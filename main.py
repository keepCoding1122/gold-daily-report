"""黄金数据日报 — 主入口

定时执行：采集数据 → 计算指标 → 生成日报 → 推送飞书
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from collectors.fred_client import FredClient
from collectors.akshare_client import AkshareClient
from collectors.web_scrapers import WebScraper
from indicators.fiscal_pressure import FiscalPressureIndex
from indicators.technical import TechnicalIndicators, SentimentIndicators
from report.template import build_report_data
from report.ai_summary import generate_summary
from report.formatter import build_feishu_message
from pusher.feishu_bot import FeishuBot


def main():
    print(f"{'='*50}")
    print(f"  黄金数据日报 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 0. 验证配置
    missing = Config.validate()
    if missing:
        print(f"[WARN] 以下配置未填写：{', '.join(missing)}")
        print("   请复制 .env.example 为 .env 并填入真实值\n")

    # 1. 采集 FRED 宏观数据
    print("[1/5] 采集 FRED 宏观数据...")
    fred_client = FredClient()
    fred_data = fred_client.fetch_all()
    print(f"   共获取 {len(fred_data)} 个 series\n")

    # 2. 采集中国数据
    print("[2/5] 采集中国市场数据...")
    akshare_client = AkshareClient()
    china_data = akshare_client.collect_all()
    print()

    # 3. 采集网页数据（金价、GLD、GVZ、CFTC）
    print("[3/5] 采集网页数据...")
    scraper = WebScraper()
    web_data = scraper.collect_all()

    # 从 Yahoo Finance 获取的金价数据构建 DataFrame，并入 fred_data
    gold_history = web_data.get("gold_price_history", {})
    gold_prices_list = gold_history.get("prices", [])
    if gold_prices_list:
        df_gold = pd.DataFrame(gold_prices_list)
        df_gold["date"] = pd.to_datetime(df_gold["date"])
        df_gold = df_gold.sort_values("date").reset_index(drop=True)
        fred_data["gold_price"] = df_gold
        print(f"\n   [融合] 金价历史数据: {len(df_gold)} 行, "
              f"最新 ${df_gold['gold_price'].iloc[-1]}")
    else:
        print("\n   [融合] 无金价历史数据（技术面计算将跳过）")

    print()

    # 4. 计算自算指标
    print("[4/5] 计算自算指标...")

    # 技术面（基于金价数据）
    technical = {}
    if "gold_price" in fred_data:
        df_gp = fred_data["gold_price"]
        if df_gp is not None and not df_gp.empty and "gold_price" in df_gp.columns:
            prices = df_gp["gold_price"]
            if len(prices) >= 5:
                technical = TechnicalIndicators.compute_all(prices)
                pr = technical.get("percentile", {})
                ma = technical.get("moving_averages", {})
                print(f"   ✓ 技术面: 均线/动量/分位数/波动率 计算完成")
                if pr.get("percentile") is not None:
                    print(f"     金价 {pr['window_days']}日历史分位: {pr['percentile']}%")
                if ma.get("trend_signal"):
                    print(f"     趋势信号: {ma['trend_signal']}")
            else:
                print("   ⚠ 金价数据不足 5 天，跳过技术面计算")
    else:
        print("   ⚠ 无金价数据，跳过技术面计算")

    # 财政压力指数
    fiscal = {}
    try:
        debt_gdp = None
        interest_revenue = None
        deficit_gdp = None

        if "federal_debt" in fred_data and "gdp_real" in fred_data:
            debt_df = fred_data["federal_debt"]
            gdp_df = fred_data["gdp_real"]
            if not debt_df.empty and not gdp_df.empty:
                debt_col = "federal_debt" if "federal_debt" in debt_df.columns else next((c for c in debt_df.columns if c != "date"), None)
                gdp_col = "gdp_real" if "gdp_real" in gdp_df.columns else next((c for c in gdp_df.columns if c != "date"), None)
                if debt_col and gdp_col:
                    debt = float(debt_df[debt_col].iloc[-1])
                    gdp = float(gdp_df[gdp_col].iloc[-1])
                    debt_gdp = round(debt / gdp / 10, 1)

        if "fiscal_deficit" in fred_data:
            deficit_df = fred_data["fiscal_deficit"]
            if not deficit_df.empty:
                deficit_col = "fiscal_deficit" if "fiscal_deficit" in deficit_df.columns else next((c for c in deficit_df.columns if c != "date"), None)
                if deficit_col and debt_gdp:
                    deficit = float(deficit_df[deficit_col].iloc[-1])
                    deficit_gdp = round(abs(deficit) / (debt_gdp / 100 * 100) / 10, 1)

        fiscal = FiscalPressureIndex().calculate(
            debt_gdp=debt_gdp,
            interest_revenue=interest_revenue,
            deficit_gdp=deficit_gdp,
        )
        if fiscal.get("score") is not None:
            print(f"   ✓ 财政压力指数: {fiscal['score']}/100 ({fiscal['regime']})")
        else:
            print("   ⚠ 财政压力指数: 数据不足")
    except Exception as e:
        print(f"   ⚠ 财政压力指数计算失败: {e}")

    # 情绪指标
    sentiment = {}
    try:
        cftc_data = web_data.get("cftc", {})
        if cftc_data and "net_long" in cftc_data:
            mock_history = [120000, 150000, 180000, 220000, 250000, 270000,
                            290000, 260000, 240000, 300000, 310000, 285000]
            sentiment["cftc_percentile"] = SentimentIndicators.cftc_percentile(
                cftc_data["net_long"], mock_history
            )
            print(f"   ✓ CFTC 拥挤度: {sentiment['cftc_percentile']['percentile']}%分位")

        gld_data = web_data.get("gld_holdings", {})
        if gld_data and "holdings_tons" in gld_data:
            mock_gld_history = [870, 872, 874, 873, 875, 876, 877]
            sentiment["gld_trend"] = SentimentIndicators.gld_flow_trend(mock_gld_history)
            print(f"   ✓ GLD 持仓趋势判断")

        has_t10yie = "t10yie" in fred_data
        has_gdp = "gdp_real" in fred_data
        if has_t10yie and has_gdp:
            try:
                t10_df = fred_data["t10yie"]
                t10_col = "t10yie" if "t10yie" in t10_df.columns else next((c for c in t10_df.columns if c != "date"), None)
                gdp_df = fred_data["gdp_real"]
                gdp_col = "gdp_real" if "gdp_real" in gdp_df.columns else next((c for c in gdp_df.columns if c != "date"), None)
                if t10_col and gdp_col:
                    inflation = float(t10_df[t10_col].iloc[-1])
                    gdp_vals = gdp_df[gdp_col].values
                    gdp_growth = round((gdp_vals[-1] - gdp_vals[-4]) / gdp_vals[-4] * 100, 1) if len(gdp_vals) >= 4 else 2.5
                    sentiment["regime_matrix"] = SentimentIndicators.regime_matrix(gdp_growth, inflation)
                    print(f"   ✓ 增长×通胀矩阵: {sentiment['regime_matrix']['regime']}")
            except Exception as e:
                print(f"   ⚠ 通胀矩阵: {e}")
    except Exception as e:
        print(f"   ⚠ 情绪指标计算失败: {e}")

    print()

    # 5. 生成日报 & 推送
    print("[5/5] 生成日报并推送...")
    try:
        report_data = build_report_data(
            fred_data=fred_data,
            china_data=china_data,
            web_data=web_data,
            technical=technical,
            fiscal=fiscal,
            sentiment=sentiment,
        )

        # AI 总结（百炼大模型）
        print("   [AI] 生成市场总结...")
        ai_summary = generate_summary(report_data)
        if ai_summary:
            report_data["ai_summary"] = ai_summary
            print(f"   ✓ AI 总结: {ai_summary[:50]}...")
        else:
            print("   ⚠ AI 总结跳过（无 API Key 或调用失败）")

        feishu_msg = build_feishu_message(report_data)
        print(f"   日报共 {len(report_data.get('signals', []))} 条信号")
        print()

        bot = FeishuBot()
        result = bot.send(feishu_msg)

        if result.get("code") == 0:
            print(f"\n{'='*50}")
            print(f"  ✅ 日报推送完成！")
            print(f"{'='*50}")
        else:
            print(f"\n{'='*50}")
            print(f"  [WARN] 日报已生成但推送未成功")
            print(f"  请检查 .env 中 FEISHU_WEBHOOK_URL 是否正确")
            print(f"{'='*50}")

    except Exception as e:
        print(f"[ERROR] 日报生成/推送失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

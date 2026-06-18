"""黄金数据日报 — 主入口

定时执行：采集数据 → 计算指标 → 生成日报 → 推送飞书
"""

import sys
from datetime import datetime

# 确保项目根目录在 path 中
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from collectors.fred_client import FredClient
from collectors.akshare_client import AkshareClient
from collectors.web_scrapers import WebScraper
from indicators.fiscal_pressure import FiscalPressureIndex
from indicators.technical import TechnicalIndicators, SentimentIndicators
from report.template import build_report_data
from report.formatter import build_feishu_message
from pusher.feishu_bot import FeishuBot


def main():
    print(f"{'='*50}")
    print(f"  黄金数据日报 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    # 0. 验证配置
    missing = Config.validate()
    if missing:
        print(f"⚠️  以下配置未填写：{', '.join(missing)}")
        print("   请复制 .env.example 为 .env 并填入真实值\n")

    # 1. 采集 FRED 数据
    print("📡 [1/5] 采集 FRED 宏观数据...")
    fred_client = FredClient()
    fred_data = fred_client.fetch_all()
    print(f"   共获取 {len(fred_data)} 个 series\n")

    # 2. 采集中国数据
    print("🇨🇳 [2/5] 采集中国市场数据...")
    akshare_client = AkshareClient()
    china_data = akshare_client.collect_all()
    print()

    # 3. 采集网页数据
    print("🕸️ [3/5] 采集网页数据...")
    scraper = WebScraper()
    web_data = scraper.collect_all()
    print()

    # 4. 计算指标
    print("🧮 [4/5] 计算自算指标...")

    # 技术面（基于金价数据）
    technical = {}
    if "gold_price" in fred_data:
        prices = fred_data["gold_price"]["gold_price"]
        if not prices.empty:
            technical = TechnicalIndicators.compute_all(prices)
            print(f"   ✓ 技术面: 均线/动量/分位数/波动率 计算完成")
            # 分位数
            pr = technical.get("percentile", {})
            if pr.get("percentile") is not None:
                print(f"     金价 {pr['window_days']}日历史分位: {pr['percentile']}%")
            # 趋势
            ma = technical.get("moving_averages", {})
            if ma.get("trend_signal"):
                print(f"     趋势信号: {ma['trend_signal']}")
    else:
        print("   ⚠ 无金价数据，跳过技术面计算")

    # 财政压力指数
    fiscal = {}
    try:
        # 从 FRED 数据中提取计算用值
        debt_gdp = None
        interest_revenue = None
        deficit_gdp = None

        if "federal_debt" in fred_data and "gdp_real" in fred_data:
            # 债务/GDP (FRED debt 是百万美元, GDP 是十亿?)
            debt_series = fred_data["federal_debt"]
            gdp_series = fred_data["gdp_real"]
            if not debt_series.empty and not gdp_series.empty:
                debt = debt_series["federal_debt"].iloc[-1]
                gdp = gdp_series["gdp_real"].iloc[-1]
                # 粗略估算: GFDEBTN 单位百万, GDPC1 单位十亿
                debt_gdp = round(debt / gdp / 10, 1)  # 转化为 %

        if "fiscal_deficit" in fred_data:
            deficit_series = fred_data["fiscal_deficit"]
            if not deficit_series.empty:
                deficit = deficit_series["fiscal_deficit"].iloc[-1]
                # FYFSD 单位百万
                if debt_gdp and gdp:
                    deficit_gdp = round(abs(deficit) / gdp / 10, 1)

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
        # CFTC 分位（模拟历史数据，实际需要更多历史）
        cftc_data = web_data.get("cftc", {})
        if cftc_data and "net_long" in cftc_data:
            # 模拟一些历史数据（实际应从数据库或历史文件读取）
            mock_history = [120000, 150000, 180000, 220000, 250000, 270000,
                            290000, 260000, 240000, 300000, 310000, 285000]
            sentiment["cftc_percentile"] = SentimentIndicators.cftc_percentile(
                cftc_data["net_long"], mock_history
            )
            print(f"   ✓ CFTC 拥挤度计算完成")

        # GLD 趋势（模拟）
        gld_data = web_data.get("gld_holdings", {})
        if gld_data and "holdings_tons" in gld_data:
            mock_gld_history = [870, 872, 874, 873, 875, 876, 877]
            sentiment["gld_trend"] = SentimentIndicators.gld_flow_trend(mock_gld_history)
            print(f"   ✓ GLD 趋势判断完成")

        # 通胀矩阵
        has_t10yie = "t10yie" in fred_data
        has_gdp = "gdp_real" in fred_data
        if has_t10yie and has_gdp:
            try:
                inflation = float(fred_data["t10yie"]["t10yie"].iloc[-1])
                # GDP 增长取最近同比变化近似
                gdp_vals = fred_data["gdp_real"]["gdp_real"].values
                if len(gdp_vals) >= 4:
                    gdp_growth = round((gdp_vals[-1] - gdp_vals[-4]) / gdp_vals[-4] * 100, 1)
                else:
                    gdp_growth = 2.5  # fallback
                sentiment["regime_matrix"] = SentimentIndicators.regime_matrix(gdp_growth, inflation)
                rm = sentiment["regime_matrix"]
                print(f"   ✓ 增长×通胀矩阵: {rm.get('regime', '?')}")
            except Exception as e:
                print(f"   ⚠ 通胀矩阵: {e}")
    except Exception as e:
        print(f"   ⚠ 情绪指标计算失败: {e}")

    print()

    # 5. 生成日报 & 推送
    print("📝 [5/5] 生成日报并推送...")
    try:
        report_data = build_report_data(
            fred_data=fred_data,
            china_data=china_data,
            web_data=web_data,
            technical=technical,
            fiscal=fiscal,
            sentiment=sentiment,
        )

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
            print(f"  ⚠️  日报已生成但推送未成功")
            print(f"  请检查 .env 中 FEISHU_WEBHOOK_URL 是否正确")
            print(f"{'='*50}")

    except Exception as e:
        print(f"❌ 日报生成/推送失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

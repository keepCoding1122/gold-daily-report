"""日报模板 — 将采集数据组装为结构化日报"""

from datetime import datetime

import pandas as pd
from config import Config


def build_report_data(fred_data: dict, china_data: dict, web_data: dict,
                      technical: dict, fiscal: dict, sentiment: dict) -> dict:
    """
    将各采集层数据合并为日报数据对象

    Returns:
        dict: 包含所有日报板块数据的字典
    """
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()],
    }

    # 一、金价速览
    report["gold"] = _build_gold_section(fred_data)

    # 二、宏观层
    report["macro"] = _build_macro_section(fred_data)

    # 三、财政压力指数
    report["fiscal"] = fiscal

    # 四、市场情绪
    report["sentiment"] = _build_sentiment_section(sentiment, web_data)

    # 五、技术面
    report["technical"] = technical

    # 六、中国市场
    report["china"] = _build_china_section(china_data)

    # 七、资产对比
    report["assets"] = _build_assets_comparison(fred_data)

    # 八、关键信号
    report["signals"] = _build_signals(report)

    return report


def _get_latest(df: pd.DataFrame, series_key: str) -> float:
    """从 FRED 数据中提取最新值"""
    if series_key not in df or df[series_key].empty:
        return None
    return float(df[series_key].iloc[-1])


def _get_change(df: pd.DataFrame, series_key: str, period: int = 1) -> float:
    """计算变动值"""
    if series_key not in df or len(df[series_key]) < period + 1:
        return None
    arr = df[series_key].values
    current = float(arr[-1])
    prev = float(arr[-1 - period])
    return round(current - prev, 2)


def _get_pct_change(df: pd.DataFrame, series_key: str, period: int = 1) -> float:
    """计算百分比变化"""
    if series_key not in df or len(df[series_key]) < period + 1:
        return None
    arr = df[series_key].values
    current = float(arr[-1])
    prev = float(arr[-1 - period])
    if prev == 0:
        return None
    return round((current - prev) / prev * 100, 2)


def _build_gold_section(fred_data: dict) -> dict:
    """金价速览板块"""
    gold_series = fred_data.get("gold_price", pd.DataFrame())
    section = {}

    if gold_series is not None and not gold_series.empty:
        # 最新值
        section["price"] = round(gold_series["gold_price"].iloc[-1], 2)
        # 多周期变化
        for label, days in [("1日", 1), ("1周", 5), ("1月", 21), ("年初至今", None)]:
            if days:
                chg = _get_pct_change(gold_series, "gold_price", days)
                if chg is not None:
                    section[label] = {
                        "change_pct": chg,
                        "direction": "up" if chg > 0 else "down",
                    }
        # YTD 年初至今
        if len(gold_series) > 1:
            first_this_year = gold_series[gold_series["date"] >= f"{datetime.now().year}-01-01"]
            if not first_this_year.empty:
                first_price = first_this_year["gold_price"].iloc[0]
                last_price = gold_series["gold_price"].iloc[-1]
                ytd_chg = round((last_price - first_price) / first_price * 100, 2)
                section["年初至今"] = {
                    "change_pct": ytd_chg,
                    "direction": "up" if ytd_chg > 0 else "down",
                }

    return section


def _build_macro_section(fred_data: dict) -> dict:
    """宏观层板块"""
    section = {}
    # 先合并所有 FRED 数据
    dfs = []
    for name, df in fred_data.items():
        if df is not None and not df.empty:
            d = df.copy()
            dfs.append(d)

    if not dfs:
        return section

    # 实际利率 = DGS10 - T10YIE
    if "dgs10" in fred_data and "t10yie" in fred_data:
        try:
            dgs = fred_data["dgs10"]
            tie = fred_data["t10yie"]
            merged = pd.merge(dgs, tie, on="date", how="inner")
            if not merged.empty:
                real_rate = merged["dgs10"].iloc[-1] - merged["t10yie"].iloc[-1]
                section["real_rate"] = round(real_rate, 2)
        except Exception:
            pass

    # 直接从 FRED series 取最新值
    single_series = [
        ("fed_funds_rate", "联邦基金利率"),
        ("dgs10", "10Y国债收益率"),
        ("dgs2", "2Y国债收益率"),
        ("t5yie", "5Y通胀预期"),
        ("t10yie", "10Y通胀预期"),
        ("dollar_index", "美元指数(贸易加权)"),
        ("unemployment", "失业率"),
        ("ism_manufacturing", "ISM制造业PMI"),
        ("core_pce", "核心PCE"),
    ]

    for key, label in single_series:
        if key in fred_data:
            df = fred_data[key]
            if df is not None and not df.empty:
                value = df.iloc[-1][key]
                section[key] = {
                    "label": label,
                    "value": round(float(value), 2),
                }

    # 期限利差
    if "dgs10" in fred_data and "dgs2" in fred_data:
        try:
            d10 = fred_data["dgs10"]["dgs10"].iloc[-1]
            d2 = fred_data["dgs2"]["dgs2"].iloc[-1]
            section["spread"] = round(float(d10) - float(d2), 2)
        except Exception:
            pass

    return section


def _build_sentiment_section(sentiment: dict, web_data: dict) -> dict:
    """市场情绪板块"""
    section = {}

    if "cftc_percentile" in sentiment:
        section["cftc"] = sentiment["cftc_percentile"]

    if "gld_trend" in sentiment:
        section["gld"] = sentiment["gld_trend"]

    if "gvz" in web_data:
        gvz_data = web_data["gvz"]
        if isinstance(gvz_data, dict):
            section["gvz"] = gvz_data.get("gvz")

    if "regime_matrix" in sentiment:
        section["regime_matrix"] = sentiment["regime_matrix"]

    return section


def _build_china_section(china_data: dict) -> dict:
    """中国市场板块"""
    section = {}

    if "shanghai_gold" in china_data:
        section["shanghai_gold"] = china_data["shanghai_gold"]

    if "usd_cny" in china_data:
        section["usd_cny"] = china_data["usd_cny"]

    if "china_cpi" in china_data:
        section["china_cpi"] = china_data["china_cpi"]

    if "china_pmi" in china_data:
        section["china_pmi"] = china_data["china_pmi"]

    if "china_m2" in china_data:
        section["china_m2"] = china_data["china_m2"]

    if "china_foreign_reserve" in china_data:
        section["china_foreign_reserve"] = china_data["china_foreign_reserve"]

    return section


def _build_assets_comparison(fred_data: dict) -> list:
    """资产表现对比"""
    comparisons = []

    # 黄金 YTD
    if "gold_price" in fred_data:
        df = fred_data["gold_price"]
        if df is not None and not df.empty and len(df) > 1:
            first = df.iloc[0]["gold_price"]
            last = df.iloc[-1]["gold_price"]
            gold_ytd = round((last - first) / first * 100, 2)
            comparisons.append(("黄金", gold_ytd))

    # 标普 500 YTD
    if "sp500" in fred_data:
        df = fred_data["sp500"]
        if df is not None and not df.empty and len(df) > 1:
            first = df.iloc[0]["sp500"]
            last = df.iloc[-1]["sp500"]
            sp_ytd = round((last - first) / first * 100, 2)
            comparisons.append(("标普500", sp_ytd))

    return comparisons


def _build_signals(report: dict) -> list:
    """生成今日关键信号"""
    signals = []

    # 实际利率信号
    macro = report.get("macro", {})
    real_rate = macro.get("real_rate")
    if real_rate is not None:
        if real_rate > 2:
            signals.append(("🔴", f"实际利率 {real_rate}% 高位压制金价"))
        elif real_rate > 1:
            signals.append(("🟡", f"实际利率 {real_rate}% 仍构成约束"))
        else:
            signals.append(("🟢", f"实际利率 {real_rate}% 低位利好金价"))

    # CFTC 拥挤度
    sentiment = report.get("sentiment", {})
    cftc = sentiment.get("cftc", {})
    if isinstance(cftc, dict) and cftc.get("percentile") is not None:
        pct = cftc["percentile"]
        if pct >= 90:
            signals.append(("🔴", f"CFTC 净多头拥挤度 {pct}% — 警惕短期回调"))
        elif pct >= 75:
            signals.append(("🟡", f"CFTC 净多头拥挤度 {pct}% — 偏高"))

    # GLD 持仓趋势
    gld = sentiment.get("gld", {})
    if isinstance(gld, dict):
        trend = gld.get("trend", "")
        if "净流入" in trend:
            signals.append(("🟢", f"GLD 持仓：{trend}"))

    # 通胀矩阵
    matrix = sentiment.get("regime_matrix", {})
    if isinstance(matrix, dict):
        regime = matrix.get("regime", "")
        outlook = matrix.get("gold_outlook", "")
        if regime:
            signals.append(("📊", f"增长×通胀定位：{regime} — {outlook}"))

    # 金价技术面
    tech = report.get("technical", {})
    if tech:
        ma = tech.get("moving_averages", {})
        trend_signal = ma.get("trend_signal", "")
        if trend_signal:
            signals.append(("📈", f"技术面信号：{trend_signal}"))

    return signals

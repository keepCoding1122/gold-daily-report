"""交易建议 — 基于多因子信号生成买卖参考"""

from typing import Optional


def build_trade_advice(report: dict) -> list:
    """
    根据报告中的各项因子生成交易信号

    评分机制：
      +1 = 看多信号  -1 = 看空信号   0 = 中性
    总分 > 2 → 偏多，< -2 → 偏空，其余 → 震荡
    """
    score = 0
    reasons = []

    # 1. 技术面趋势信号
    tech = report.get("technical", {})
    ma = tech.get("moving_averages", {})
    trend = ma.get("trend_signal", "")
    if "偏多" in trend:
        score += 1
        reasons.append("技术面偏多")
    elif "偏空" in trend:
        score -= 1
        reasons.append("技术面偏空")

    # 2. 历史分位（极端位置反指）
    pr = tech.get("percentile", {})
    pct = pr.get("percentile")
    if pct is not None:
        if pct > 90:
            score -= 1
            reasons.append(f"金价处于{pct}%高位分位，有回调风险")
        elif pct < 15:
            score += 1
            reasons.append(f"金价处于{pct}%低位分位，估值偏便宜")

    # 3. CFTC 拥挤度
    sentiment = report.get("sentiment", {})
    cftc = sentiment.get("cftc", {})
    if isinstance(cftc, dict):
        cp = cftc.get("percentile")
        if cp is not None:
            if cp > 90:
                score -= 1
                reasons.append(f"CFTC净多头{cp}%分位，过于拥挤")
            elif cp < 20:
                score += 1
                reasons.append(f"CFTC净多头仅{cp}%分位，冷清")

    # 4. 实际利率环境
    macro = report.get("macro", {})
    real_rate = macro.get("real_rate")
    if real_rate is not None:
        if real_rate < 1.0:
            score += 1
            reasons.append(f"实际利率{real_rate}%处于低位，有利黄金")
        elif real_rate > 2.5:
            score -= 1
            reasons.append(f"实际利率{real_rate}%过高，压制金价")

    # 5. 通胀×增长矩阵
    matrix = sentiment.get("regime_matrix", {})
    if isinstance(matrix, dict):
        regime = matrix.get("regime", "")
        if "滞胀" in regime:
            score += 1
            reasons.append("类滞胀环境，黄金历史表现最好")
        elif "金发" in regime:
            score -= 1
            reasons.append("金发女孩环境，机会成本高")

    # 6. GLD 资金流向
    gld = sentiment.get("gld", {})
    if isinstance(gld, dict):
        trend_text = gld.get("trend", "")
        if "净流入" in trend_text:
            score += 1
            reasons.append("GLD持续净流入，资金面支撑")
        elif "净流出" in trend_text:
            score -= 1
            reasons.append("GLD持续净流出，资金面偏空")

    # 7. 金价多周期动量
    momentum = tech.get("momentum", {})
    if momentum:
        # 短中长期动量一致性
        month = momentum.get("1月")
        year = momentum.get("1年")
        if month and year:
            if month > 3 and year > 10:
                score -= 1
                reasons.append(f"短期动量过猛({month:+.0f}%)，警惕回调")
            elif month < -3 and year < 5:
                score += 1
                reasons.append(f"短期超跌({month:+.0f}%)，可能反弹")

    # 生成建议
    if score >= 2:
        verdict = "偏多 ↑"
        opinion = "整体信号偏多，适合逢低布局或持有"
    elif score <= -2:
        verdict = "偏空 ↓"
        opinion = "整体信号偏空，建议控制仓位、等待更好入场点"
    else:
        verdict = "震荡 →"
        opinion = "多空因素交织，建议观望或轻仓操作"

    # 精简原因（取最重要的 3 条）
    top_reasons = reasons[:3]

    return [verdict, opinion, top_reasons]

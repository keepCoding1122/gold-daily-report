"""飞书消息格式器 — 将日报数据转为飞书 Post 消息 JSON"""


def build_feishu_message(report: dict) -> dict:
    """将 report dict 转为飞书 Post 消息 payload"""
    content = []
    date_str = report.get("date", "")
    weekday = report.get("weekday", "")

    # ── AI 总结（最醒目的位置） ──
    ai_summary = report.get("ai_summary", "")
    if ai_summary:
        content.append([{"tag": "text", "text": f"💡 {ai_summary}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 金价速览 ──
    gold = report.get("gold", {})
    if gold.get("price"):
        price_line = f"🟡 伦敦金  ${gold['price']}"
        periods = []
        for period in ["1日", "1周", "1月", "年初至今"]:
            if period in gold:
                chg = gold[period].get("change_pct", 0)
                arrow = "↑" if chg > 0 else "↓"
                periods.append(f"{period} {chg:+.2f}%{arrow}")
        content.append([{"tag": "text", "text": price_line, "bold": True}])
        if periods:
            content.append([{"tag": "text", "text": f"  {'  |  '.join(periods)}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 宏观数据 ──
    macro = report.get("macro", {})
    if macro:
        content.append([{"tag": "text", "text": "▎宏观面", "bold": True}])

        # 利率组
        rate_items = []
        if "real_rate" in macro:
            rate_items.append(f"实际利率 {macro['real_rate']}%")
        for key, short in [("fed_funds_rate", "联邦基金"), ("dgs10", "10Y"), ("dgs2", "2Y")]:
            if key in macro:
                rate_items.append(f"{short} {macro[key]['value']}%")
        if "spread" in macro:
            rate_items.append(f"利差 {macro['spread']}%")
        if rate_items:
            content.append([{"tag": "text", "text": f"  利率｜{'  '.join(rate_items)}"}])

        # 通胀组
        infl_items = []
        for key, short in [("t5yie", "5Y预期"), ("t10yie", "10Y预期"), ("core_pce", "核心PCE")]:
            if key in macro:
                infl_items.append(f"{short} {macro[key]['value']}%")
        if infl_items:
            content.append([{"tag": "text", "text": f"  通胀｜{'  '.join(infl_items)}"}])

        # 其他
        other_items = []
        if "dollar_index" in macro:
            other_items.append(f"美元 {macro['dollar_index']['value']}")
        if "unemployment" in macro:
            other_items.append(f"失业率 {macro['unemployment']['value']}%")
        if "ism_manufacturing" in macro:
            other_items.append(f"ISM {macro['ism_manufacturing']['value']}")
        if other_items:
            content.append([{"tag": "text", "text": f"  其他｜{'  '.join(other_items)}"}])

        content.append([{"tag": "text", "text": ""}])

    # ── 财政压力 ──
    fiscal = report.get("fiscal", {})
    if fiscal.get("score") is not None:
        content.append([{"tag": "text", "text": "▎财政压力", "bold": True}])
        components = fiscal.get("components", {})
        comp_parts = [f"{c['label']} {c['value']:.1f}%" for c in components.values()]
        if comp_parts:
            content.append([{"tag": "text", "text": f"  {' / '.join(comp_parts)}"}])
        content.append([{"tag": "text", "text": f"  评分 {fiscal['score']}/100 → {fiscal.get('regime', 'N/A')}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 市场情绪 ──
    sentiment = report.get("sentiment", {})
    sentiment_items = []
    gld = sentiment.get("gld", {})
    if gld:
        sentiment_items.append(f"GLD {gld.get('trend', '')}")
    cftc = sentiment.get("cftc", {})
    if cftc and cftc.get("percentile"):
        sentiment_items.append(f"CFTC {cftc['percentile']}%分位 {cftc.get('signal', '')}")
    gvz = sentiment.get("gvz")
    if gvz:
        sentiment_items.append(f"GVZ {gvz}")
    matrix = sentiment.get("regime_matrix", {})
    if isinstance(matrix, dict) and matrix.get("regime"):
        sentiment_items.append(f"{matrix['regime']}→{matrix.get('gold_outlook', '')}")

    if sentiment_items:
        content.append([{"tag": "text", "text": "▎市场情绪", "bold": True}])
        for item in sentiment_items:
            content.append([{"tag": "text", "text": f"  · {item}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 技术面 ──
    tech = report.get("technical", {})
    if tech:
        content.append([{"tag": "text", "text": "▎技术面", "bold": True}])
        ma = tech.get("moving_averages", {})
        ma_parts = []
        for label in ["5日", "20日", "60日", "200日"]:
            if label in ma:
                ma_parts.append(f"{label} ${ma[label]['ma']}({ma[label]['deviation_pct']:+.1f}%)")
        if ma_parts:
            content.append([{"tag": "text", "text": f"  均线｜{'  '.join(ma_parts)}"}])
        trend_sig = ma.get("trend_signal", "")
        if trend_sig:
            content.append([{"tag": "text", "text": f"  信号｜{trend_sig}"}])
        pr = tech.get("percentile", {})
        if pr.get("percentile") is not None:
            content.append([{"tag": "text", "text": f"  分位｜{pr.get('window_days', '?')}日历史 {pr['percentile']}%"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 中国市场 ──
    china = report.get("china", {})
    if china:
        china_items = []
        sg = china.get("shanghai_gold", {})
        if sg:
            china_items.append(f"沪金 ¥{sg.get('price', '?')}/克")
        cny = china.get("usd_cny")
        if cny:
            china_items.append(f"USD/CNY {cny}")
        cpi = china.get("china_cpi", {})
        if cpi:
            china_items.append(f"CPI {cpi.get('value', '?')}%")
        pmi = china.get("china_pmi", {})
        if pmi:
            china_items.append(f"PMI {pmi.get('official', '?')}")
        m2 = china.get("china_m2", {})
        if m2:
            china_items.append(f"M2 +{m2.get('value', '?')}%")
        fr = china.get("china_foreign_reserve", {})
        if fr:
            china_items.append(f"外储 ${fr.get('value', '?')}万亿")

        if china_items:
            content.append([{"tag": "text", "text": "▎中国市场", "bold": True}])
            content.append([{"tag": "text", "text": f"  {'  |  '.join(china_items)}"}])
            content.append([{"tag": "text", "text": ""}])

    # ── 资产对比 ──
    assets = report.get("assets", [])
    if assets:
        parts = []
        for name, ytd in assets:
            arrow = "↑" if ytd > 0 else "↓"
            parts.append(f"{name} {ytd:+.1f}%{arrow}")
        content.append([{"tag": "text", "text": "▎YTD对比", "bold": True}])
        content.append([{"tag": "text", "text": f"  {'  vs  '.join(parts)}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 关键信号 ──
    signals = report.get("signals", [])
    if signals:
        content.append([{"tag": "text", "text": "─── 今日信号 ───", "bold": True}])
        for icon, msg in signals:
            content.append([{"tag": "text", "text": f"{icon} {msg}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 页脚 ──
    content.append([{"tag": "text", "text": f"⏱ {report.get('generated_at', '')}  ·  FRED / Yahoo / AKShare"}])

    # 组装飞书 payload
    return {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"📊 黄金日报 · {date_str} {weekday}",
                    "content": content,
                }
            }
        }
    }

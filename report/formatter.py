"""飞书消息格式器 — 将日报数据转为飞书 Post 消息 JSON"""


def build_feishu_message(report: dict) -> dict:
    """将 report dict 转为飞书 Post 消息 payload"""
    content = []
    date_str = report.get("date", "")
    weekday = report.get("weekday", "")

    # ── 标题行 ──
    content.append([{"tag": "text", "text": f"📊 黄金看板 · 数据日报"}])
    content.append([{"tag": "text", "text": f"{date_str} ({weekday})", "un_escape": True}])
    content.append([{"tag": "text", "text": ""}])

    # ── 当前报价 ──
    gold = report.get("gold", {})
    if gold.get("price"):
        price = gold["price"]
        # 找 1 日变化
        chg_1d = gold.get("1日", {}).get("change_pct", 0)
        arrow = "🟢" if chg_1d > 0 else ("🔴" if chg_1d < 0 else "⚪")
        content.append([
            {"tag": "text", "text": f"{arrow} 伦敦金  ${price}  ({chg_1d:+.2f}%)", "bold": True}
        ])

        # 多周期变化（一行内紧凑排布）
        period_parts = []
        for p in ["1周", "1月", "年初至今"]:
            if p in gold:
                cp = gold[p].get("change_pct", 0)
                icon = "▲" if cp > 0 else "▼"
                period_parts.append(f"{p} {cp:+.2f}%{icon}")
        if period_parts:
            content.append([{"tag": "text", "text": "  " + "  ".join(period_parts)}])
    content.append([{"tag": "text", "text": ""}])

    # ── 交易建议（新增，最显眼位置） ──
    advice = report.get("trade_advice", [])
    if advice and len(advice) >= 2:
        verdict, opinion, reasons = advice[0], advice[1], advice[2] if len(advice) > 2 else []
        emoji_map = {"偏多": "🟢", "偏空": "🔴", "震荡": "🟡"}
        emoji = "🟡"
        for k, v in emoji_map.items():
            if k in verdict:
                emoji = v
                break
        content.append([
            {"tag": "text", "text": f"{emoji} 参考建议：{verdict}  {opinion}", "bold": True}
        ])
        for r in reasons:
            content.append([{"tag": "text", "text": f"  · {r}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 宏观数据 ──
    macro = report.get("macro", {})
    if macro:
        content.append([
            {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
        ])
        content.append([{"tag": "text", "text": "📌 宏观", "bold": True}])

        # 利率行
        parts = []
        if "real_rate" in macro:
            parts.append(f"实际利率 {macro['real_rate']}%")
        for k, short in [("fed_funds_rate", "基金利率"), ("dgs10", "10Y"), ("dgs2", "2Y")]:
            if k in macro:
                parts.append(f"{short} {macro[k]['value']}%")
        if "spread" in macro:
            parts.append(f"利差 {macro['spread']}%")
        if parts:
            content.append([{"tag": "text", "text": "  利率  " + "  ".join(parts)}])

        # 通胀行
        parts = []
        for k, short in [("t5yie", "5Y预期"), ("t10yie", "10Y预期"), ("core_pce", "核心PCE")]:
            if k in macro:
                parts.append(f"{short} {macro[k]['value']}%")
        if parts:
            content.append([{"tag": "text", "text": "  通胀  " + "  ".join(parts)}])

        # 其他行
        parts = []
        if "dollar_index" in macro:
            parts.append(f"美元 {macro['dollar_index']['value']}")
        if "unemployment" in macro:
            parts.append(f"失业率 {macro['unemployment']['value']}%")
        if "ism_manufacturing" in macro:
            parts.append(f"PMI {macro['ism_manufacturing']['value']}")
        if parts:
            content.append([{"tag": "text", "text": "  其他  " + "  ".join(parts)}])

        content.append([{"tag": "text", "text": ""}])

    # ── 财政压力 ──
    fiscal = report.get("fiscal", {})
    if fiscal.get("score") is not None:
        content.append([
            {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
        ])
        content.append([{"tag": "text", "text": "💰 财政压力", "bold": True}])
        comps = fiscal.get("components", {})
        for c in comps.values():
            content.append([{"tag": "text", "text": f"  {c['label']} {c['value']:.1f}%"}])
        # 风险等级用颜色表示
        regime = fiscal.get("regime", "")
        regime_emoji = {"健康": "🟢", "关注": "🟡", "金融抑制": "🟠", "危机风险": "🔴"}
        re = regime_emoji.get(regime, "⚪")
        content.append([
            {"tag": "text", "text": f"  评分 {fiscal['score']}/100  ({re} {regime})", "bold": True}
        ])
        content.append([{"tag": "text", "text": ""}])

    # ── 情绪与技术 ──
    sentiment = report.get("sentiment", {})
    tech = report.get("technical", {})
    if sentiment or tech:
        content.append([
            {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
        ])
        content.append([{"tag": "text", "text": "📈 情绪 & 技术", "bold": True}])

        # 情绪项
        gld = sentiment.get("gld", {})
        if gld:
            content.append([{"tag": "text", "text": f"  GLD {gld.get('trend', '')}"}])
        cftc = sentiment.get("cftc", {})
        if isinstance(cftc, dict) and cftc.get("percentile"):
            content.append([{"tag": "text", "text": f"  CFTC 净多头 {cftc['percentile']}%分位 {cftc.get('signal', '')}"}])
        gvz = sentiment.get("gvz")
        if gvz:
            content.append([{"tag": "text", "text": f"  GVZ 波动率 {gvz}"}])

        # 均线
        ma = tech.get("moving_averages", {})
        ma_parts = []
        for label in ["5日", "20日", "60日", "200日"]:
            if label in ma:
                d = ma[label]['deviation_pct']
                icon = "▲" if d > 0 else "▼"
                ma_parts.append(f"{label}${ma[label]['ma']}{icon}{abs(d):.1f}%")
        if ma_parts:
            content.append([{"tag": "text", "text": "  均线  " + "  ".join(ma_parts)}])

        # 信号
        trend_sig = ma.get("trend_signal", "")
        if trend_sig:
            content.append([{"tag": "text", "text": f"  信号  {trend_sig}"}])

        # 分位
        pr = tech.get("percentile", {})
        if pr.get("percentile") is not None:
            content.append([{"tag": "text", "text": f"  分位  {pr['window_days']}日历史 {pr['percentile']}%"}]),
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
            china_items.append(f"CNY {cny}")
        for key, label in [("china_cpi", "CPI"), ("china_pmi", "PMI"),
                           ("china_m2", "M2"), ("china_foreign_reserve", "外储")]:
            item = china.get(key, {})
            if item:
                v = item.get("value") or item.get("official")
                if v:
                    china_items.append(f"{label} {v}")
        if china_items:
            content.append([
                {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
            ])
            content.append([{"tag": "text", "text": "🌐 中国", "bold": True}])
            content.append([{"tag": "text", "text": "  " + "  |  ".join(china_items)}])
            content.append([{"tag": "text", "text": ""}])

    # ── YTD 对比 ──
    assets = report.get("assets", [])
    if assets:
        parts = []
        for name, ytd in assets:
            icon = "▲" if ytd > 0 else "▼"
            parts.append(f"{name} {ytd:+.1f}%{icon}")
        content.append([
            {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
        ])
        content.append([{"tag": "text", "text": "📊 YTD", "bold": True}])
        content.append([{"tag": "text", "text": "  " + "  vs  ".join(parts)}])
        content.append([{"tag": "text", "text": ""}])

    # ── 关键信号 ──
    signals = report.get("signals", [])
    if signals:
        content.append([
            {"tag": "text", "text": "━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━ ━", "un_escape": True}
        ])
        content.append([{"tag": "text", "text": "💡 关键信号", "bold": True}])
        for icon, msg in signals:
            content.append([{"tag": "text", "text": f"  {icon} {msg}"}])
        content.append([{"tag": "text", "text": ""}])

    # ── 页脚 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━", "un_escape": True}
    ])
    content.append([
        {"tag": "text", "text": f"⏱ {report.get('generated_at', '')}  FRED/Yahoo"}
    ])

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

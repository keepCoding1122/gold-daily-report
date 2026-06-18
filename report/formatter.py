"""飞书消息格式器 — 将日报数据转为飞书 Post 消息 JSON"""

from datetime import datetime


def build_feishu_message(report: dict) -> dict:
    """
    将 report dict 转为飞书 Post 消息 payload

    Returns:
        dict: 可直接 POST 给飞书 webhook 的 JSON payload
    """
    content = []
    date_str = report.get("date", "")
    weekday = report.get("weekday", "")

    # ── 标题行 ──
    content.append([
        {"tag": "text", "text": f"📊 黄金看板 · 数据日报"},
    ])
    content.append([
        {"tag": "text", "text": f"{date_str} ({weekday})", "un_escape": True},
    ])
    content.append([{"tag": "text", "text": ""}])  # 空行

    # ── 一、金价速览 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": "🟡 一、金价速览", "bold": True},
    ])
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])

    gold = report.get("gold", {})
    if gold.get("price"):
        content.append([
            {"tag": "text", "text": f"伦敦金：${gold['price']}/盎司"},
        ])

    # 多周期变化
    for period in ["1日", "1周", "1月", "年初至今"]:
        if period in gold:
            chg = gold[period].get("change_pct", 0)
            arrow = "▲" if chg > 0 else "▼"
            content.append([
                {"tag": "text", "text": f"  {period}：{chg:+.2f}%  {arrow}"},
            ])

    content.append([{"tag": "text", "text": ""}])

    # ── 二、宏观层 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": "🏛️ 二、宏观层", "bold": True},
    ])
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])

    macro = report.get("macro", {})
    macro_mappings = {
        "real_rate": "实际利率",
        "fed_funds_rate": "联邦基金利率",
        "dgs10": "10Y国债收益率",
        "dgs2": "2Y国债收益率",
        "spread": "期限利差(10Y-2Y)",
        "t5yie": "5Y通胀预期",
        "t10yie": "10Y通胀预期",
        "dollar_index": "美元指数(贸易加权)",
        "unemployment": "失业率",
        "ism_manufacturing": "ISM制造业PMI",
        "core_pce": "核心PCE",
    }

    for key, label in macro_mappings.items():
        if key in macro:
            val = macro[key]
            if isinstance(val, dict):
                v = val.get("value", "")
            else:
                v = val
            suffix = "%" if key not in ["dollar_index", "ism_manufacturing", "spread", "core_pce"] else ""
            if key == "core_pce":
                suffix = "%"
            content.append([
                {"tag": "text", "text": f"📌 {label}：{v}{suffix}"},
            ])

    content.append([{"tag": "text", "text": ""}])

    # ── 三、财政压力指数 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": "💰 三、财政压力指数", "bold": True},
    ])
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])

    fiscal = report.get("fiscal", {})
    if fiscal.get("score") is not None:
        components = fiscal.get("components", {})
        for key, comp in components.items():
            content.append([
                {"tag": "text", "text": f"  {comp['label']}：{comp['value']:.1f}%"},
            ])
        content.append([
            {"tag": "text", "text": f"  ─────────────────"},
        ])
        content.append([
            {"tag": "text", "text": f"  财政压力评分：{fiscal['score']}/100", "bold": True},
        ])
        content.append([
            {"tag": "text", "text": f"  区间：{fiscal.get('regime', 'N/A')}", "bold": True},
        ])
    else:
        content.append([{"tag": "text", "text": "  数据不足（需 FRED 联邦债务/赤字数据）"}])

    content.append([{"tag": "text", "text": ""}])

    # ── 四、市场情绪 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": "📈 四、市场情绪", "bold": True},
    ])
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])

    sentiment = report.get("sentiment", {})

    # GLD
    gld = sentiment.get("gld", {})
    if gld:
        trend = gld.get("trend", "")
        content.append([
            {"tag": "text", "text": f"📌 GLD ETF 持仓趋势：{trend}"},
        ])

    # CFTC
    cftc = sentiment.get("cftc", {})
    if cftc:
        pct = cftc.get("percentile")
        signal = cftc.get("signal", "")
        if pct:
            content.append([
                {"tag": "text", "text": f"📌 CFTC 净多头拥挤度：{pct}%分位 {signal}"},
            ])

    # GVZ
    gvz = sentiment.get("gvz")
    if gvz:
        content.append([
            {"tag": "text", "text": f"📌 GVZ 波动率指数：{gvz}"},
        ])

    # 通胀矩阵
    matrix = sentiment.get("regime_matrix", {})
    if matrix and isinstance(matrix, dict):
        regime = matrix.get("regime", "")
        outlook = matrix.get("gold_outlook", "")
        if regime:
            content.append([
                {"tag": "text", "text": f"📌 增长×通胀定位：{regime}"},
            ])
            content.append([
                {"tag": "text", "text": f"   → {outlook}"},
            ])

    content.append([{"tag": "text", "text": ""}])

    # ── 五、技术面 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": "📊 五、技术面", "bold": True},
    ])
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])

    tech = report.get("technical", {})
    if tech:
        ma = tech.get("moving_averages", {})
        for label in ["5日", "20日", "60日", "200日"]:
            if label in ma:
                content.append([
                    {"tag": "text", "text": f"  {label}均线：${ma[label]['ma']}  (偏离{ma[label]['deviation_pct']:+.2f}%)"},
                ])
        trend_sig = ma.get("trend_signal", "")
        if trend_sig:
            content.append([
                {"tag": "text", "text": f"  信号：{trend_sig}"},
            ])

        # 百分位
        pr = tech.get("percentile", {})
        if pr.get("percentile") is not None:
            content.append([
                {"tag": "text", "text": f"  当前在{pr.get('window_days', '?')}日历史中处于 {pr['percentile']}% 分位"},
            ])

    content.append([{"tag": "text", "text": ""}])

    # ── 六、中国市场 ──
    china = report.get("china", {})
    if china:
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])
        content.append([
            {"tag": "text", "text": "🌐 六、中国市场", "bold": True},
        ])
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])

        sg = china.get("shanghai_gold", {})
        if sg:
            content.append([
                {"tag": "text", "text": f"📌 上海金(Au99.99)：¥{sg.get('price', '?')}/克"},
            ])

        cny = china.get("usd_cny")
        if cny:
            content.append([
                {"tag": "text", "text": f"📌 USD/CNY：{cny}"},
            ])

        cpi = china.get("china_cpi", {})
        if cpi:
            content.append([
                {"tag": "text", "text": f"📌 中国CPI：{cpi.get('value', '?')}%"},
            ])

        pmi = china.get("china_pmi", {})
        if pmi:
            content.append([
                {"tag": "text", "text": f"📌 中国PMI：{pmi.get('official', '?')} (制造业)"},
            ])

        m2 = china.get("china_m2", {})
        if m2:
            content.append([
                {"tag": "text", "text": f"📌 中国M2：+{m2.get('value', '?')}% YoY"},
            ])

        fr = china.get("china_foreign_reserve", {})
        if fr:
            content.append([
                {"tag": "text", "text": f"📌 外汇储备：${fr.get('value', '?')}万亿"},
            ])

        content.append([{"tag": "text", "text": ""}])

    # ── 七、资产对比 ──
    assets = report.get("assets", [])
    if assets:
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])
        content.append([
            {"tag": "text", "text": "🏆 七、资产表现对比 (YTD)", "bold": True},
        ])
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])

        for name, ytd in assets:
            arrow = "▲" if ytd > 0 else "▼"
            content.append([
                {"tag": "text", "text": f"  {name}：{ytd:+.1f}%  {arrow}"},
            ])

        content.append([{"tag": "text", "text": ""}])

    # ── 八、关键信号 ──
    signals = report.get("signals", [])
    if signals:
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])
        content.append([
            {"tag": "text", "text": "💡 八、今日关键信号", "bold": True},
        ])
        content.append([
            {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
        ])

        for icon, msg in signals:
            content.append([
                {"tag": "text", "text": f"  {icon} {msg}"},
            ])

        content.append([{"tag": "text", "text": ""}])

    # ── 页脚 ──
    content.append([
        {"tag": "text", "text": "━━━━━━━━━━━━━━━━━━━━━", "un_escape": True},
    ])
    content.append([
        {"tag": "text", "text": f"数据源：FRED / AKShare / CFTC / CBOE"},
    ])
    content.append([
        {"tag": "text", "text": f"生成时间：{report.get('generated_at', '')} CST"},
    ])

    # 组装飞书 payload
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"📊 黄金看板日报 · {date_str}",
                    "content": content,
                }
            }
        }
    }

    return payload

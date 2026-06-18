"""AI 总结 — 调用阿里百炼生成日报摘要"""

import json
import requests
from config import Config


def generate_summary(report_data: dict) -> str:
    """
    将日报结构化数据发给百炼大模型，返回一段精炼的市场总结。
    无 API Key 或调用失败时返回空字符串（不阻塞主流程）。
    """
    if not Config.DASHSCOPE_API_KEY:
        return ""

    prompt = _build_prompt(report_data)

    try:
        resp = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": Config.DASHSCOPE_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "你是一位专业的黄金市场分析师，擅长将复杂宏观数据提炼为简洁的市场洞察。"
                        "用 3-5 句话总结今日黄金市场核心逻辑，语言精炼、有观点、有方向感。"
                        "不要使用 markdown 格式，直接输出纯文本。"
                    )},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"   ⚠ AI 总结生成失败: {e}")
        return ""


def _build_prompt(report_data: dict) -> str:
    """将日报数据组装为 prompt 上下文"""
    parts = []

    parts.append(f"日期：{report_data.get('date', '')} {report_data.get('weekday', '')}")

    # 金价
    gold = report_data.get("gold", {})
    if gold.get("price"):
        parts.append(f"伦敦金现价：${gold['price']}/盎司")
        for period in ["1日", "1周", "1月", "年初至今"]:
            if period in gold:
                parts.append(f"  {period}变动：{gold[period]['change_pct']:+.2f}%")

    # 宏观
    macro = report_data.get("macro", {})
    if macro:
        parts.append("\n宏观数据：")
        if "real_rate" in macro:
            parts.append(f"  实际利率：{macro['real_rate']}%")
        for key in ["fed_funds_rate", "dgs10", "dgs2", "t5yie", "t10yie",
                    "dollar_index", "unemployment", "core_pce"]:
            if key in macro:
                item = macro[key]
                parts.append(f"  {item['label']}：{item['value']}")
        if "spread" in macro:
            parts.append(f"  期限利差(10Y-2Y)：{macro['spread']}%")

    # 财政
    fiscal = report_data.get("fiscal", {})
    if fiscal.get("score") is not None:
        parts.append(f"\n财政压力指数：{fiscal['score']}/100 ({fiscal.get('regime', '')})")

    # 情绪
    sentiment = report_data.get("sentiment", {})
    if sentiment.get("regime_matrix"):
        m = sentiment["regime_matrix"]
        parts.append(f"\n增长×通胀定位：{m.get('regime', '')} → {m.get('gold_outlook', '')}")

    # 技术面
    tech = report_data.get("technical", {})
    if tech:
        ma = tech.get("moving_averages", {})
        if ma.get("trend_signal"):
            parts.append(f"\n技术面信号：{ma['trend_signal']}")

    # 信号
    signals = report_data.get("signals", [])
    if signals:
        parts.append("\n今日信号：")
        for icon, msg in signals:
            parts.append(f"  {icon} {msg}")

    return "\n".join(parts)

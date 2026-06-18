"""技术面指标 — 均线、动量、分位数、百分位"""

from typing import Optional

import numpy as np
import pandas as pd


class TechnicalIndicators:
    """基于金价序列计算各种技术指标"""

    @staticmethod
    def moving_averages(prices: pd.Series) -> dict:
        """计算各周期均线及当前偏离度"""
        periods = {"5日": 5, "20日": 20, "60日": 60, "200日": 200}
        current_price = prices.iloc[-1]
        result = {}

        for label, period in periods.items():
            if len(prices) >= period:
                ma = prices.tail(period).mean()
                deviation = (current_price - ma) / ma * 100
                result[label] = {
                    "ma": round(ma, 2),
                    "deviation_pct": round(deviation, 2),
                }

        # 判断趋势信号
        if "20日" in result:
            deviation_20 = result["20日"]["deviation_pct"]
            if deviation_20 > 3:
                result["trend_signal"] = "短期偏多"
            elif deviation_20 < -3:
                result["trend_signal"] = "短期偏空"
            else:
                result["trend_signal"] = "中性"

        return result

    @staticmethod
    def percentile_rank(prices: pd.Series, window: int = 2520) -> dict:
        """
        当前价格在 N 个交易日内的百分位
        默认 2520 ≈ 10年
        """
        if len(prices) < 2:
            return {"percentile": None, "range": (None, None)}

        recent = prices.tail(min(window, len(prices)))
        current = prices.iloc[-1]
        low = recent.min()
        high = recent.max()

        if high == low:
            pct = 50.0
        else:
            pct = (current - low) / (high - low) * 100

        return {
            "percentile": round(pct, 1),
            "current": round(current, 2),
            "low": round(low, 2),
            "high": round(high, 2),
            "window_days": len(recent),
        }

    @staticmethod
    def momentum(prices: pd.Series) -> dict:
        """计算多周期动量"""
        result = {}
        periods = {"1周": 5, "2周": 10, "1月": 21, "3月": 63, "1年": 252}

        current = prices.iloc[-1]
        for label, period in periods.items():
            if len(prices) > period:
                prev = prices.iloc[-1 - period]
                change = (current - prev) / prev * 100
                result[label] = round(change, 2)

        return result

    @staticmethod
    def volatility(prices: pd.Series, window: int = 21) -> dict:
        """价格波动率（年化）"""
        if len(prices) < window:
            return {}

        returns = prices.pct_change().dropna()
        recent_returns = returns.tail(window)
        daily_vol = recent_returns.std()
        annualized_vol = daily_vol * np.sqrt(252)

        return {
            "daily_vol_pct": round(daily_vol * 100, 2),
            "annualized_vol_pct": round(annualized_vol * 100, 2),
            "window": window,
        }

    @staticmethod
    def compute_all(prices: pd.Series) -> dict:
        """计算所有技术指标"""
        return {
            "moving_averages": TechnicalIndicators.moving_averages(prices),
            "percentile": TechnicalIndicators.percentile_rank(prices),
            "momentum": TechnicalIndicators.momentum(prices),
            "volatility": TechnicalIndicators.volatility(prices),
        }


class SentimentIndicators:
    """情绪指标分析"""

    @staticmethod
    def cftc_percentile(cftc_net_long: float, history: list[float]) -> dict:
        """
        CFTC 净多头在历史中的分位（拥挤度）
        """
        if not history:
            return {"percentile": None, "signal": "数据不足"}

        all_vals = sorted(history + [cftc_net_long])
        rank = all_vals.index(cftc_net_long)
        pct = rank / (len(all_vals) - 1) * 100

        if pct >= 90:
            signal = "🔴 极度拥挤"
        elif pct >= 75:
            signal = "🟡 偏拥挤"
        elif pct <= 10:
            signal = "🟢 极度冷清"
        elif pct <= 25:
            signal = "🟢 偏冷清"
        else:
            signal = "⚪ 中性"

        return {
            "percentile": round(pct, 1),
            "signal": signal,
            "current": cftc_net_long,
        }

    @staticmethod
    def gld_flow_trend(holdings_history: list[float]) -> dict:
        """GLD 持仓趋势判断"""
        if len(holdings_history) < 5:
            return {"trend": "数据不足"}

        recent = holdings_history[-5:]
        changes = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
        positive_days = sum(1 for c in changes if c > 0)

        if positive_days >= 4:
            return {"trend": "🟢 连续净流入", "consecutive_inflow": positive_days}
        elif positive_days <= 1:
            return {"trend": "🔴 连续净流出", "consecutive_outflow": 5 - positive_days}
        else:
            return {"trend": "⚪ 波动", "inflow_days": positive_days}

    @staticmethod
    def regime_matrix(gdp_growth: Optional[float], inflation: Optional[float]) -> dict:
        """
        增长 × 通胀 2×2 矩阵定位

        增长 > 2% 为强，通胀 > 3% 为高（近似值）
        """
        if gdp_growth is None or inflation is None:
            return {"regime": "数据不足"}

        strong_growth = gdp_growth > 2
        high_inflation = inflation > 3

        if strong_growth and high_inflation:
            regime = "繁荣"
            gold_outlook = "中性偏弱 — 风险资产受追捧"
        elif not strong_growth and high_inflation:
            regime = "类滞胀"
            gold_outlook = "🟢 最有利于黄金的宏观组合"
        elif strong_growth and not high_inflation:
            regime = "金发女孩"
            gold_outlook = "偏弱 — 机会成本高"
        else:
            regime = "衰退/通缩"
            gold_outlook = "中性 — 避险需求 vs 流动性紧缩"

        return {
            "regime": regime,
            "gold_outlook": gold_outlook,
            "gdp_growth": gdp_growth,
            "inflation": inflation,
        }

"""财政压力指数 — 复合加权评分"""

from typing import Optional


class FiscalPressureIndex:
    """
    财政压力指数 = 债务/GDP + 利息支出/财政收入 + 赤字/GDP 复合加权

    评分映射：
      0-39   健康
      40-59  关注
      60-79  金融抑制
      80-100 危机风险
    """

    # 评分权重
    WEIGHTS = {
        "debt_gdp": 0.40,           # 债务/GDP
        "interest_revenue": 0.35,    # 利息支出/财政收入
        "deficit_gdp": 0.25,         # 赤字/GDP
    }

    # 各指标子评分函数 (0-100)
    @staticmethod
    def _score_debt_gdp(ratio: float) -> float:
        """债务/GDP 评分"""
        if ratio <= 40:
            return 0
        elif ratio <= 60:
            return (ratio - 40) / 20 * 25
        elif ratio <= 90:
            return 25 + (ratio - 60) / 30 * 25
        elif ratio <= 120:
            return 50 + (ratio - 90) / 30 * 25
        else:
            return min(100, 75 + (ratio - 120) / 30 * 25)

    @staticmethod
    def _score_interest_revenue(ratio: float) -> float:
        """利息支出/财政收入 评分（单位：%）"""
        if ratio <= 5:
            return ratio / 5 * 20
        elif ratio <= 10:
            return 20 + (ratio - 5) / 5 * 30
        elif ratio <= 20:
            return 50 + (ratio - 10) / 10 * 35
        else:
            return min(100, 85 + (ratio - 20) / 10 * 15)

    @staticmethod
    def _score_deficit_gdp(ratio: float) -> float:
        """赤字/GDP 评分（单位：%，负值为盈余）"""
        if ratio <= 0:
            return 0
        elif ratio <= 3:
            return ratio / 3 * 30
        elif ratio <= 6:
            return 30 + (ratio - 3) / 3 * 35
        elif ratio <= 10:
            return 65 + (ratio - 6) / 4 * 25
        else:
            return min(100, 90 + (ratio - 10) / 5 * 10)

    @staticmethod
    def get_regime(score: float) -> str:
        if score < 40:
            return "健康"
        elif score < 60:
            return "关注"
        elif score < 80:
            return "金融抑制"
        else:
            return "危机风险"

    def calculate(
        self,
        debt_gdp: Optional[float] = None,
        interest_revenue: Optional[float] = None,
        deficit_gdp: Optional[float] = None,
    ) -> dict:
        """
        计算财政压力指数

        Args:
            debt_gdp: 联邦债务/GDP，如 1.225（即 122.5%）
            interest_revenue: 利息支出/财政收入，如 18.5（即18.5%）
            deficit_gdp: 赤字/GDP，如 5.7（即5.7%）
        """
        components = {}

        if debt_gdp is not None:
            components["debt_gdp"] = {
                "value": debt_gdp,
                "label": "债务/GDP",
                "score": self._score_debt_gdp(debt_gdp),
            }

        if interest_revenue is not None:
            components["interest_revenue"] = {
                "value": interest_revenue,
                "label": "利息/财政收入",
                "score": self._score_interest_revenue(interest_revenue),
            }

        if deficit_gdp is not None:
            components["deficit_gdp"] = {
                "value": deficit_gdp,
                "label": "赤字/GDP",
                "score": self._score_deficit_gdp(deficit_gdp),
            }

        # 加权总分
        total_score = 0.0
        total_weight = 0.0
        details = []

        for key, weight in self.WEIGHTS.items():
            if key in components:
                total_score += components[key]["score"] * weight
                total_weight += weight
                details.append(
                    f"{components[key]['label']}：{components[key]['value']:.1f}% → "
                    f"{components[key]['score']:.0f}分(权重{weight*100:.0f}%)"
                )

        if total_weight == 0:
            return {"score": None, "regime": "数据不足", "details": []}

        final_score = round(total_score / total_weight, 1)

        return {
            "score": final_score,
            "regime": self.get_regime(final_score),
            "components": components,
            "details": details,
        }


# 快捷函数
def calc_fiscal_pressure(
    debt_gdp: Optional[float] = None,
    interest_revenue: Optional[float] = None,
    deficit_gdp: Optional[float] = None,
) -> dict:
    return FiscalPressureIndex().calculate(debt_gdp, interest_revenue, deficit_gdp)

"""图表生成 — 用 matplotlib 绘制金价走势、均线、技术面"""

from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


class ChartGenerator:
    """生成日报配图"""

    OUTPUT_DIR = Path(__file__).parent.parent / "charts"

    def __init__(self):
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        # 中文字体
        plt.rcParams["font.sans-serif"] = ["PingFang SC", "Microsoft YaHei", "SimHei", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False
        # 配色
        self.GOLD = "#d4a853"
        self.GOLD_DARK = "#b9852c"
        self.GREEN = "#16a34a"
        self.RED = "#dc2626"
        self.BG = "#faf6ef"
        self.TEXT = "#1f1a12"

    def price_chart(self, df: pd.DataFrame, col: str = "gold_price") -> str:
        """金价走势图（含均线）"""
        if df is None or df.empty or len(df) < 10:
            return ""

        fig, ax = plt.subplots(figsize=(8, 3.2))
        fig.patch.set_facecolor(self.BG)
        ax.set_facecolor(self.BG)

        dates = df["date"]
        prices = df[col]

        # 主价格线
        ax.plot(dates, prices, color=self.GOLD_DARK, linewidth=1.8, label="金价", zorder=3)

        # 均线
        for period, color, ls in [(20, self.GREEN, "--"), (60, self.RED, "--")]:
            if len(prices) >= period:
                ma = prices.rolling(period).mean()
                ax.plot(dates, ma, color=color, linewidth=0.8, linestyle=ls,
                        alpha=0.7, label=f"{period}日均线")

        # 最近一天高亮
        ax.scatter(dates.iloc[-1:], prices.iloc[-1:], color=self.GOLD, s=40,
                   zorder=5, edgecolors=self.GOLD_DARK, linewidth=1.2)

        # 格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
        fig.autofmt_xdate(rotation=0, ha="center")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))

        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.grid(True, alpha=0.2, color="#cccccc", linewidth=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#dddddd")
        ax.spines["bottom"].set_color("#dddddd")
        ax.tick_params(colors=self.TEXT, labelsize=9)

        legend = ax.legend(loc="upper left", framealpha=0.8, fontsize=8,
                           facecolor="white", edgecolor="#dddddd")
        for text in legend.get_texts():
            text.set_color(self.TEXT)

        plt.tight_layout(pad=0.8)
        path = self.OUTPUT_DIR / f"price_{datetime.now().strftime('%Y%m%d')}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=self.BG)
        plt.close(fig)
        return str(path)

    def momentum_chart(self, df: pd.DataFrame, col: str = "gold_price") -> str:
        """动量/偏离度柱状图"""
        if df is None or df.empty or len(df) < 5:
            return ""

        prices = df[col]
        current = prices.iloc[-1]

        periods = [5, 10, 21, 63, 126]
        labels = ["5日", "10日", "21日", "63日", "126日"]
        deviations = []

        for p in periods:
            if len(prices) > p:
                ma = prices.tail(p).mean()
                dev = (current - ma) / ma * 100
                deviations.append(dev)
            else:
                deviations.append(0)

        fig, ax = plt.subplots(figsize=(6, 2.2))
        fig.patch.set_facecolor(self.BG)
        ax.set_facecolor(self.BG)

        colors = [self.RED if d < 0 else self.GREEN for d in deviations]
        bars = ax.barh(labels, deviations, color=colors, height=0.55, zorder=3)

        # 标注数值
        for bar, dev in zip(bars, deviations):
            label_x = dev + (0.3 if dev >= 0 else -0.3)
            ha = "left" if dev >= 0 else "right"
            ax.text(label_x, bar.get_y() + bar.get_height() / 2,
                    f"{dev:+.1f}%", ha=ha, va="center",
                    fontsize=10, fontweight="bold", color=self.TEXT)

        ax.axvline(0, color="#333333", linewidth=0.6)
        ax.set_xlabel("偏离 %", fontsize=9, color=self.TEXT)
        ax.tick_params(colors=self.TEXT, labelsize=9)
        ax.grid(True, axis="x", alpha=0.15, color="#cccccc")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#dddddd")
        ax.spines["bottom"].set_color("#dddddd")

        plt.tight_layout(pad=0.6)
        path = self.OUTPUT_DIR / f"momentum_{datetime.now().strftime('%Y%m%d')}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=self.BG)
        plt.close(fig)
        return str(path)

    def generate_all(self, df: pd.DataFrame, col: str = "gold_price") -> list[str]:
        """生成所有图表，返回文件路径列表"""
        paths = []
        for fn in [self.price_chart, self.momentum_chart]:
            p = fn(df, col)
            if p:
                paths.append(p)
                print(f"   ✓ 图表生成: {Path(p).name}")
        return paths


def generate_charts(df: pd.DataFrame, col: str = "gold_price") -> list[str]:
    return ChartGenerator().generate_all(df, col)

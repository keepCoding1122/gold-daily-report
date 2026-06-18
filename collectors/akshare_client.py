"""AKShare 数据采集 — 中国市场黄金及相关宏观数据"""

from datetime import datetime
from typing import Optional

import pandas as pd


class AkshareClient:
    """AKShare 封装（akshare 需单独安装，未安装时返回模拟数据）"""

    def __init__(self):
        self._ak = None

    @property
    def available(self) -> bool:
        try:
            import akshare as ak
            self._ak = ak
            return True
        except ImportError:
            return False

    def get_shanghai_gold(self) -> Optional[dict]:
        """上海黄金交易所 Au99.99 最新价格"""
        if not self.available:
            return None
        try:
            df = self._ak.spot_gold()
            if df is None or df.empty:
                return None
            # 取最新行
            row = df.iloc[-1]
            return {
                "price": float(row.get("最新价", 0)),
                "change": float(row.get("涨跌幅", 0)),
                "high": float(row.get("最高价", 0)),
                "low": float(row.get("最低价", 0)),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        except Exception:
            return None

    def get_usd_cny(self) -> Optional[float]:
        """美元兑人民币中间价"""
        if not self.available:
            return None
        try:
            df = self._ak.currency_boc_sina("美元")
            if df is not None and not df.empty:
                row = df.iloc[-1]
                return float(row.get("现汇买入价", 7.24)) / 100
        except Exception:
            pass
        return None

    def get_china_cpi(self) -> Optional[dict]:
        """中国 CPI 最新"""
        if not self.available:
            return None
        try:
            df = self._ak.macro_china_cpi_monthly()
            if df is not None and not df.empty:
                last = df.iloc[-1]
                return {"value": float(last.iloc[-1]), "date": str(last.iloc[0])}
        except Exception:
            pass
        return None

    def get_china_pmi(self) -> Optional[dict]:
        """中国 PMI 最新"""
        if not self.available:
            return None
        try:
            df = self._ak.macro_china_pmi()
            if df is not None and not df.empty:
                last = df.iloc[-1]
                return {
                    "official": float(last.get("制造业采购经理人指数", 0)),
                    "date": str(last.iloc[0]),
                }
        except Exception:
            pass
        return None

    def get_china_m2(self) -> Optional[dict]:
        """中国 M2 货币供应"""
        if not self.available:
            return None
        try:
            df = self._ak.macro_china_m2()
            if df is not None and not df.empty:
                last = df.iloc[-1]
                return {
                    "value": float(last.get("货币和准货币(M2)供应量_同比增长", 0)),
                    "date": str(last.iloc[0]),
                }
        except Exception:
            pass
        return None

    def get_china_foreign_reserve(self) -> Optional[dict]:
        """中国外汇储备"""
        if not self.available:
            return None
        try:
            df = self._ak.macro_china_fx_reserves_yearly()
            if df is not None and not df.empty:
                last = df.iloc[-1]
                return {
                    "value": float(last.iloc[-1]) / 1e8,  # 转万亿
                    "date": str(last.iloc[0]),
                }
        except Exception:
            pass
        return None

    def collect_all(self) -> dict:
        """收集所有中国数据"""
        result = {"aksource": "akshare" if self.available else "unavailable"}
        if not self.available:
            return result

        print("  [AKShare] 获取上海金价...")
        gold = self.get_shanghai_gold()
        if gold:
            result["shanghai_gold"] = gold
            print(f"    ✓ 上海金: ¥{gold['price']}/克")

        print("  [AKShare] 获取 USD/CNY...")
        cny = self.get_usd_cny()
        if cny:
            result["usd_cny"] = cny
            print(f"    ✓ USD/CNY: {cny:.4f}")

        print("  [AKShare] 获取中国 CPI...")
        cpi = self.get_china_cpi()
        if cpi:
            result["china_cpi"] = cpi

        print("  [AKShare] 获取中国 PMI...")
        pmi = self.get_china_pmi()
        if pmi:
            result["china_pmi"] = pmi

        print("  [AKShare] 获取中国 M2...")
        m2 = self.get_china_m2()
        if m2:
            result["china_m2"] = m2

        print("  [AKShare] 获取中国外汇储备...")
        fr = self.get_china_foreign_reserve()
        if fr:
            result["china_foreign_reserve"] = fr

        return result

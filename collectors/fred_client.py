"""FRED API 客户端 — 从圣路易斯联储获取宏观数据"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests

from config import Config


class FredClient:
    """FRED API 封装，自动缓存最近一次结果避免重复请求"""

    BASE_URL = Config.FRED_BASE_URL
    API_KEY = Config.FRED_API_KEY
    START_DATE = Config.FRED_START_DATE

    # 缓存目录（避免每次运行都重复请求同个 series）
    CACHE_DIR = Path(__file__).parent.parent / ".cache"
    CACHE_TTL_HOURS = 6  # 6 小时内不重复请求

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "GoldDailyReport/1.0"})
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, series_id: str) -> Path:
        return self.CACHE_DIR / f"fred_{series_id}.json"

    def _is_cache_valid(self, series_id: str) -> bool:
        cache_path = self._cache_path(series_id)
        if not cache_path.exists():
            return False
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        return (datetime.now() - mtime) < timedelta(hours=self.CACHE_TTL_HOURS)

    def fetch_series(self, series_id: str, observation_start: Optional[str] = None) -> pd.DataFrame:
        """获取单个 FRED series 的全部观测值，返回 DataFrame"""

        # 检查缓存
        if self._is_cache_valid(series_id):
            cache_path = self._cache_path(series_id)
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._parse_observations(data, series_id)

        # 请求 API
        params = {
            "series_id": series_id,
            "api_key": self.API_KEY,
            "file_type": "json",
            "observation_start": observation_start or self.START_DATE,
            "sort_order": "desc",  # 最新的在前面
            "limit": 2000,
        }

        url = f"{self.BASE_URL}/series/observations"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # 检查 API 错误
        if "error_code" in data:
            raise RuntimeError(f"FRED API error [{data.get('error_code')}]: {data.get('error_message')}")

        # 写缓存
        with open(self._cache_path(series_id), "w", encoding="utf-8") as f:
            json.dump(data, f)

        return self._parse_observations(data, series_id)

    def _parse_observations(self, data: dict, series_id: str) -> pd.DataFrame:
        """解析 FRED API 返回的 observations 为 DataFrame"""
        observations = data.get("observations", [])
        if not observations:
            return pd.DataFrame()

        rows = []
        for obs in observations:
            val = obs.get("value")
            if val and val != ".":
                rows.append({
                    "date": obs["date"],
                    series_id: float(val),
                })

        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)
        return df

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """获取所有配置的 FRED series"""
        results = {}
        total = len(Config.FRED_SERIES)

        for i, (name, series_id) in enumerate(Config.FRED_SERIES.items(), 1):
            print(f"  [{i}/{total}] 获取 {name} ({series_id})...")
            try:
                df = self.fetch_series(series_id)
                if not df.empty:
                    results[name] = df
                    # 打印最新值
                    last = df.iloc[-1]
                    print(f"    ✓ 最新 ({last['date'].date()}): {last[series_id]}")
                else:
                    print(f"    ⚠ 无数据")
            except Exception as e:
                print(f"    ✗ 失败: {e}")

            # 避免请求频率过高
            if i < total:
                time.sleep(0.3)

        return results

    def get_latest_value(self, series_id: str) -> tuple[Optional[str], Optional[float]]:
        """快捷方法：获取最新日期和值"""
        try:
            df = self.fetch_series(series_id)
            if df.empty:
                return None, None
            last = df.iloc[-1]
            return str(last["date"].date()), float(last[series_id])
        except Exception:
            return None, None

    def get_multi_series(self, names: list[str]) -> pd.DataFrame:
        """从预配置的 series 中批量获取，合并为一个宽表"""
        all_data = {}
        for name in names:
            series_id = Config.FRED_SERIES.get(name)
            if not series_id:
                continue
            df = self.fetch_series(series_id)
            if not df.empty:
                all_data[name] = df

        # 按 date 合并
        result = None
        for name, df in all_data.items():
            col = name
            df = df[["date", Config.FRED_SERIES[name]]].rename(
                columns={Config.FRED_SERIES[name]: col}
            )
            if result is None:
                result = df
            else:
                result = pd.merge(result, df, on="date", how="outer")

        if result is not None:
            result = result.sort_values("date").reset_index(drop=True)
        return result


# 快捷函数
def get_fred_data() -> dict[str, pd.DataFrame]:
    client = FredClient()
    return client.fetch_all()

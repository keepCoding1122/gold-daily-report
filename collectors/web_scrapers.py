"""网页数据采集 — CFTC / GVZ / GLD 持仓等"""

from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup


class WebScraper:
    """爬虫采集公开网页数据"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/124.0.0.0 Safari/537.36"
        })

    def get_gld_holdings(self) -> Optional[dict]:
        """从 SPDR 官网获取 GLD 持仓量（吨）"""
        try:
            # SPDR 官方数据页面
            url = "https://www.spdrgoldshares.com/"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")

            # 尝试多种选择器（网站结构可能变化）
            selectors = [
                ".holdings-table .current-holding",
                ".total-holdings",
                "#holdings .value",
                "[data-field='holdings']",
            ]

            for selector in selectors:
                el = soup.select_one(selector)
                if el:
                    text = el.get_text(strip=True).replace(",", "").replace("t", "").replace(" ", "")
                    try:
                        tons = float(text)
                        return {
                            "holdings_tons": tons,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "SPDR.com",
                        }
                    except ValueError:
                        continue

            # fallback: 找包含 "tonnes" 的文字
            for tag in soup.find_all(["div", "span", "p"]):
                text = tag.get_text(strip=True).lower()
                if "tonnes" in text:
                    words = text.replace(",", "").split()
                    for i, w in enumerate(words):
                        try:
                            if float(w) > 100:
                                return {
                                    "holdings_tons": float(w),
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "source": "SPDR.com(parsed)",
                                }
                        except ValueError:
                            continue
            return None

        except Exception as e:
            print(f"    ⚠ GLD 爬虫失败: {e}")
            return None

    def get_gvz(self) -> Optional[dict]:
        """从 CBOE 获取 GVZ 黄金波动率指数（近似值）"""
        try:
            # CBOE GVZ 历史数据
            url = "https://www.cboe.com/us/indices/dashboard/gvz/"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text()

            # 找 "GVZ" 附近的数字
            import re
            # 匹配模式: "GVZ" 后跟数字
            patterns = [
                r"GVZ[:\s]*(\d+\.?\d*)",
                r"gvz[:\s]*(\d+\.?\d*)",
                r"Gold VIX[:\s]*(\d+\.?\d*)",
            ]
            for pat in patterns:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    return {
                        "gvz": float(match.group(1)),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": "CBOE.com",
                    }

            # fallback: Yahoo Finance
            return self._get_gvz_from_yahoo()

        except Exception as e:
            print(f"    ⚠ GVZ 爬虫失败: {e}")
            return self._get_gvz_from_yahoo()

    def _get_gvz_from_yahoo(self) -> Optional[dict]:
        """从 Yahoo Finance 获取 GVZ"""
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/GVZ"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = self.session.get(url, headers=headers, timeout=10)
            data = resp.json()

            meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
            price = meta.get("regularMarketPrice")
            if price:
                return {
                    "gvz": float(price),
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": "Yahoo Finance",
                }
        except Exception:
            pass
        return None

    def get_cftc(self) -> Optional[dict]:
        """获取 CFTC 黄金期货持仓（从公开 CSV 源）"""
        try:
            # 使用 CFTC 官方提供的最近一期 COT 报告
            url = "https://www.cftc.gov/dea/futures/deacmxsf.htm"
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()

            text = resp.text
            import re

            # 找 "GOLD" 所在行，后面跟着数字
            lines = text.split("\n")
            in_gold = False
            for line in lines:
                if "GOLD" in line.upper() and "COMEX" in line.upper():
                    in_gold = True
                if in_gold and re.search(r"\d{4,}", line):
                    # 提取数字: 总持仓, 多头, 空头, 净多头等
                    nums = re.findall(r"[\d,]+", line)
                    nums = [n.replace(",", "") for n in nums]
                    if len(nums) >= 3:
                        longs = int(nums[0]) if len(nums) > 0 else 0
                        shorts = int(nums[1]) if len(nums) > 1 else 0
                        net = longs - shorts
                        return {
                            "net_long": net,
                            "long": longs,
                            "short": shorts,
                            "date": datetime.now().strftime("%Y-%m-%d"),
                            "source": "CFTC.gov",
                        }
            return None

        except Exception as e:
            print(f"    ⚠ CFTC 爬虫失败: {e}")
            return None

    def collect_all(self) -> dict:
        """采集所有网页数据"""
        result = {}

        print("  [爬虫] 获取 GLD 持仓...")
        gld = self.get_gld_holdings()
        if gld:
            result["gld_holdings"] = gld
            print(f"    ✓ GLD: {gld.get('holdings_tons', '?')} 吨")
        else:
            print("    ⚠ GLD 数据未获取到（模拟）")

        print("  [爬虫] 获取 GVZ 波动率...")
        gvz = self.get_gvz()
        if gvz:
            result["gvz"] = gvz
            print(f"    ✓ GVZ: {gvz.get('gvz', '?')}")
        else:
            print("    ⚠ GVZ 未获取到")

        print("  [爬虫] 获取 CFTC 持仓...")
        cftc = self.get_cftc()
        if cftc:
            result["cftc"] = cftc
            print(f"    ✓ CFTC 净多头: {cftc.get('net_long', '?')}")
        else:
            print("    ⚠ CFTC 未获取到")

        return result

"""配置管理 — 从 .env 和环境变量读取"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（项目根目录）
# 已存在的环境变量不会被覆盖
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
elif not os.environ.get("FRED_API_KEY") or not os.environ.get("FEISHU_WEBHOOK_URL"):
    # 环境变量也未设置时，尝试 .env.example 让用户知道
    example_path = Path(__file__).parent / ".env.example"
    if example_path.exists():
        print("[INFO] .env not found. Copy .env.example to .env and fill in your API keys for local runs.")
        print("[INFO] In GitHub Actions, set secrets in repo settings instead.")
        load_dotenv(example_path)


class Config:
    # FRED
    FRED_API_KEY = os.getenv("FRED_API_KEY", "")
    FRED_START_DATE = os.getenv("FRED_START_DATE", "2015-01-01")
    FRED_BASE_URL = "https://api.stlouisfed.org/fred"

    # 飞书
    FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
    FEISHU_SECRET = os.getenv("FEISHU_SECRET", "")

    # FRED series 定义（key = 指标名, value = FRED series_id）
    FRED_SERIES = {
        # 黄金
        "gold_price": "GOLDAMGBD228NLBM",          # 伦敦金定盘价 (USD/oz)
        # 利率
        "fed_funds_rate": "FEDFUNDS",              # 联邦基金利率
        "dgs10": "DGS10",                          # 10Y 国债收益率
        "dgs2": "DGS2",                            # 2Y 国债收益率
        "dfii10": "DFII10",                        # 10Y TIPS 实际利率
        # 通胀
        "t5yie": "T5YIE",                          # 5Y 盈亏平衡通胀率
        "t10yie": "T10YIE",                        # 10Y 盈亏平衡通胀率
        "cpi": "CPIAUCSL",                         # CPI 同比
        "core_cpi": "CPILFESL",                    # 核心 CPI
        "core_pce": "PCEPILFE",                    # 核心 PCE
        # 美元
        "dollar_index": "DTWEXBGS",                # 贸易加权美元指数
        "dollar_advanced": "DTWEXAFEGS",           # 对发达经济体美元
        # 就业
        "unemployment": "UNRATE",                  # 失业率
        "nonfarm_payroll": "PAYEMS",               # 非农就业
        "avg_hourly": "AHETPI",                    # 平均时薪
        # 经济
        "ism_manufacturing": "NAPM",               # ISM 制造业 PMI
        "ism_non_manufacturing": "NAPMSN",         # ISM 非制造业 PMI
        "consumer_confidence": "UMCSENT",          # 消费者信心
        "gdp_real": "GDPC1",                       # 实际 GDP
        # 财政
        "federal_debt": "GFDEBTN",                 # 联邦债务总额
        "fiscal_deficit": "FYFSD",                 # 财政赤字
        # 货币
        "m2": "M2SL",                              # M2 货币供应
        # 市场
        "sp500": "SP500",                          # 标普 500
    }

    # 指标分类（用于日报分区）
    SERIES_CATEGORIES = {
        "gold_price": "黄金",
        "fed_funds_rate": "利率",
        "dgs10": "利率",
        "dgs2": "利率",
        "dfii10": "利率",
        "t5yie": "通胀",
        "t10yie": "通胀",
        "cpi": "通胀",
        "core_cpi": "通胀",
        "core_pce": "通胀",
        "dollar_index": "汇率",
        "dollar_advanced": "汇率",
        "unemployment": "就业",
        "nonfarm_payroll": "就业",
        "avg_hourly": "就业",
        "ism_manufacturing": "经济",
        "ism_non_manufacturing": "经济",
        "consumer_confidence": "经济",
        "gdp_real": "经济",
        "federal_debt": "财政",
        "fiscal_deficit": "财政",
        "m2": "货币",
        "sp500": "市场",
    }

    @classmethod
    def validate(cls):
        """启动时验证关键配置"""
        missing = []
        if not cls.FRED_API_KEY or cls.FRED_API_KEY == "your_fred_api_key_here":
            missing.append("FRED_API_KEY")
        if not cls.FEISHU_WEBHOOK_URL or "your_token" in cls.FEISHU_WEBHOOK_URL:
            missing.append("FEISHU_WEBHOOK_URL")
        return missing

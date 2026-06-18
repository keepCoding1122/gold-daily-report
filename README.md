# 黄金数据日报系统

每日采集全球黄金及相关宏观数据，生成结构化日报推送至飞书群。

## 数据源（全部免费）

| 来源 | 覆盖指标 | 获取方式 |
|------|---------|---------|
| **FRED API** | 金价、利率、通胀、美元指数、PMI、就业、GDP、债务 | 注册免费 Key |
| **AKShare** | 上海金价、中国CPI/PMI/M2/外汇储备 | pip install （可选） |
| **网页爬虫** | CFTC 净多头、GVZ 波动率、GLD 持仓 | 自动抓取公开数据 |
| **自算指标** | 财政压力指数、均线/动量/分位数、通胀×增长矩阵 | 原创算法 |

## 日报内容（8 个板块）

```
金价速览 → 宏观层 → 财政压力指数 → 市场情绪
→ 技术面 → 中国市场 → 资产对比 → 今日信号
```

## 部署方式

### 方式一：GitHub Actions（推荐）

免费、云端运行、无需本地电脑开机。

#### 1. 配置 Secrets

在 GitHub 仓库 **Settings → Secrets and variables → Actions** 添加：

| Secret | 说明 |
|--------|------|
| `FRED_API_KEY` | [FRED 免费 API Key](https://fred.stlouisfed.org/docs/api/api_key.html) |
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 Webhook 地址 |
| `FEISHU_SECRET` | （可选）飞书签名密钥 |

#### 2. 推送即运行

提交后自动生效，每天 UTC 1:00 / 9:00（北京时间 9:00 / 17:00）执行。

也可在 Actions 页面手动触发：**Actions → 黄金数据日报 → Run workflow**。

### 方式二：本地运行

```bash
git clone https://github.com/keepCoding1122/gold-daily-report.git
cd gold-daily-report

pip install -r requirements.txt

# 复制配置模板并填写
copy .env.example .env
# 编辑 .env，填入 FRED_API_KEY 和 FEISHU_WEBHOOK_URL

# 手动运行
python main.py

# Windows 定时任务（可选）
setup.bat
```

## 项目结构

```
gold-daily-report/
├── main.py                         # 入口
├── config.py                       # 配置
├── collectors/
│   ├── fred_client.py              # FRED API
│   ├── akshare_client.py           # AKShare 中国数据
│   └── web_scrapers.py             # 爬虫
├── indicators/
│   ├── fiscal_pressure.py          # 财政压力指数
│   └── technical.py                # 技术面 & 情绪
├── report/
│   ├── template.py                 # 日报组装
│   └── formatter.py                # 飞书格式
├── pusher/
│   └── feishu_bot.py               # 飞书推送
└── .github/workflows/
    └── daily-report.yml            # GitHub Actions
```

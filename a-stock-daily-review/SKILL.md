---
name: A股每日复盘
description_en: "Generate daily A-share market review report at 4pm. Includes: market overview (rise/fall ratio, limit up/down ratio, fear/greed index, 30-day volume), surge stocks analysis, heat ranking TOP50 from 3 platforms. Data sources: Wencai + Xueqiu + EastMoney."
description: "每天下午4点运行，生成A股每日复盘报告。包含：大盘整体情况（涨跌比、涨跌停比、恐慌/贪心指标、30日成交量变化）、涨停个股分析、人气股排名TOP50（雪球+东财+问财三大平台聚合）。数据来源：乐股+问财+雪球+东方财富。适用场景：用户询问A股复盘、每日总结、市场分析、今日A股走势、涨停分析、热门股票。关键词：A股复盘、每日复盘、大盘分析、涨停分析、市场总结。"
---

# A股每日复盘技能

## 概述

每天下午4点（股市收盘后）自动运行，生成A股每日复盘报告。

## 功能特性

### 1. 大盘整体情况
- 涨跌比（上涨/下跌家数）
- 涨跌停比（涨停/跌停家数）
- 恐慌指数 = 跌停/(涨停+跌停) × 100%
- 贪心指数 = 涨停/(涨停+跌停) × 100%
- 最近30日成交量变化图
- 大盘拥挤度

### 2. 涨停个股分析
- 当日所有涨停个股
- 涨幅数据
- 涨停原因分类统计（业绩预增、并购重组、政策利好、概念炒作、资金推动等）

### 3. 人气股排名TOP50（多平台综合排名）
- **问财**人气排名（问财即同花顺数据）
- **雪球**热榜
- **东方财富**人气排名
- 综合热度分数计算

## 数据来源

| 数据 | 来源 |
|------|------|
| 大盘数据（涨跌统计、分布、拥挤度） | 乐股 (legulegu.com) |
| 恐惧贪婪指数 | FundDB (via akshare) / 乐股回退 |
| 涨停数据 | 问财 (iwencai.com) |
| 成交量历史 | 问财 |
| 人气排名 | 问财 + 雪球 + 东方财富（三大平台并发获取） |

## 环境要求

- Python 3.8+
- Node.js（用于生成问财Hexin-V签名）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

```bash
# 运行复盘（Markdown格式）
python main.py

# 输出JSON格式
python main.py --format json

# 输出PDF格式
python main.py --format pdf

# 输出HTML格式
python main.py --format html

# 指定输出文件
python main.py --output /path/to/report.md

# 指定日期
python main.py --date 2026-04-05

# 启用调试日志
python main.py --debug
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--format` | 输出格式 (md/json/pdf/html) | md |
| `--output` | 输出文件路径 | output/review_YYYY-MM-DD.{format} |
| `--date` | 复盘日期 (YYYY-MM-DD) | 当天 |
| `--debug` | 启用调试日志 | False |

## 项目结构

```
a-stock-daily-review/
├── SKILL.md                  # 技能文档
├── main.py                   # 主程序入口
├── config.py                 # 配置加载器
├── config.json               # 配置文件
├── logger.py                 # 日志配置
├── requirements.txt          # 依赖清单
├── models/                   # 数据模型
│   ├── market.py             # 大盘数据模型 (MarketData, VolumeData)
│   ├── stock.py              # 股票数据模型 (SurgeStock, HeatRank, CompositeHeatRank)
│   └── review.py             # 复盘报告模型 (DailyReview)
├── fetcher/                  # 数据采集器
│   ├── base.py               # 采集器基类
│   ├── wencai.py             # 问财采集器
│   ├── xueqiu.py             # 雪球采集器
│   ├── eastmoney.py          # 东方财富采集器
│   ├── legu.py               # 乐股采集器
│   ├── funddb.py             # FundDB恐惧贪婪指数
│   └── akshare_fetcher.py    # AKShare新闻情绪（可选）
├── analyzer/                 # 分析器
│   ├── heat_ranker.py        # 热度排名分析器
│   └── reason_analyzer.py    # 涨停原因分析器
├── reporter/                 # 报告生成器
│   ├── template_renderer.py  # 模板渲染器
│   └── generators/
│       ├── markdown_generator.py  # Markdown生成器
│       ├── json_generator.py      # JSON生成器
│       ├── pdf_generator.py       # PDF生成器 (ReportLab)
│       └── html_generator.py      # HTML生成器 (Chart.js)
├── utils/                    # 工具函数
│   ├── retry.py              # 重试装饰器
│   ├── helpers.py            # 辅助函数
│   └── validators.py         # 验证器
├── lib/
│   └── hexin_v.js            # 问财签名生成器
└── output/                   # 输出目录
```

## 输出格式

### Markdown报告示例

```markdown
# A股每日复盘报告

**日期**: 2026-04-05

## 📊 大盘概况

| 指标 | 数值 |
|------|------|
| 上涨家数 | 2356 |
| 下跌家数 | 2489 |
| 涨跌比 | 0.95 |
| 涨停家数 | 42 |
| 跌停家数 | 8 |
| 恐慌指数 | 16.0% |
| 贪心指数 | 84.0% |

## 🎭 市场情绪
- **恐慌指数**: 16.0%
- **贪心指数**: 84.0%
- **情绪判断**: 🟢 市场贪婪情绪较强

## 📈 最近30日成交量
...

## 🚀 涨停分析 (42只)
...

## 🔥 人气排名TOP50（三大平台综合排名）
...
```

## 定时执行

通过 crontab 设置每日16:00自动运行：

```bash
# 编辑定时任务
crontab -e

# 添加以下行（根据实际路径修改）
0 16 * * 1-5 cd /path/to/skills/a-stock-daily-review && python3 main.py >> review.log 2>&1
```

## 注意事项

1. 问财接口需要Node.js生成Hexin-V签名，可能有反爬限制
2. 建议在交易日收盘后运行（16:00之后）
3. 三大平台人气排名并发获取，失败不影响其他平台
4. 股市有风险，本报告仅供参考，不构成投资建议

## License

MIT
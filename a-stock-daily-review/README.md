# A股每日复盘工具

每天下午4点（股市收盘后）自动运行，生成A股每日复盘报告。

## 功能特性

### 1. 大盘整体情况
- 涨跌比（上涨/下跌家数）
- 涨跌停比（涨停/跌停家数）
- 恐慌指数 = 跌停/(涨停+跌停) × 100%
- 贪心指数 = 涨停/(涨停+跌停) × 100%
- 最近30日成交量变化图
- 主力资金净流入
### 2. 新增指标（参照 Go 项目 RKstk）
- **停牌家数** - 当日停牌股票数量
- **非一字涨停** - 真实涨停（排除一字板）
- **非一字跌停** - 真实跌停（排除一字板）
- **真实涨跌停比** - 非一字涨停/非一字跌停
- **大盘拥挤度** - 反映市场情绪极端程度
- **市场活跃度** - (涨停+跌停)/总家数

### 2. 涨停个股分析
- 当日所有涨停个股
- 涨幅数据
- 涨停原因分类统计（业绩预增、并购重组、政策利好、概念炒作、资金推动等）

### 3. 人气股排名TOP50（多平台综合排名）
- **问财**人气排名
- **雪球**热榜
- **东方财富**人气排名
- **同花顺**人气排名
- 综合热度分数计算

## 数据来源

| 数据 | 来源 |
|------|------|
| 大盘数据 | 问财（自然语言查询） |
| 涨停数据 | 问财 |
| 成交量历史 | 问财 |
| 人气排名 | 问财 + 雪球 + 东方财富 + 同花顺 |

## 环境要求

- Python 3.8+
- Node.js（用于生成问财签名）

## 安装

```bash
# 安装Python依赖
pip install -r requirements.txt
```

## 使用方法

```bash
# 运行复盘（Markdown格式）
python main.py

# 输出JSON格式
python main.py --format json

# 输出PDF格式（包含图表和仪表盘）
python main.py --format pdf

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
| `--format` | 输出格式 (md/json/pdf) | md |
| `--output` | 输出文件路径 | output/review_YYYY-MM-DD.md |
| `--date` | 复盘日期 (YYYY-MM-DD) | 当天 |
| `--debug` | 启用调试日志 | False |

## 项目结构

```
a-stock-daily-review/
├── SKILL.md                  # 技能文档
├── README.md                 # 项目说明
├── main.py                   # 主程序入口
├── config.py                 # 配置加载器
├── config.json               # 配置文件
├── logger.py                 # 日志配置
├── requirements.txt          # 依赖清单
├── .gitignore                # Git忽略文件
├── models/                   # 数据模型
│   ├── __init__.py
│   ├── market.py             # 大盘数据模型
│   ├── stock.py              # 股票数据模型
│   └── review.py             # 复盘报告模型
├── fetcher/                  # 数据采集器
│   ├── __init__.py
│   ├── base.py               # 采集器基类
│   ├── wencai.py             # 问财采集器
│   ├── xueqiu.py             # 雪球采集器
│   ├── eastmoney.py          # 东方财富采集器
│   └── thsi.py               # 同花顺采集器
├── analyzer/                 # 分析器
│   ├── __init__.py
│   ├── heat_ranker.py        # 热度排名分析器
│   └── reason_analyzer.py    # 涨停原因分析器
├── reporter/                 # 报告生成器
│   ├── __init__.py
│   ├── template_renderer.py  # 模板渲染器
│   └── generators/
│       ├── __init__.py
│       ├── markdown_generator.py  # Markdown生成器
│       └── json_generator.py      # JSON生成器
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── retry.py              # 重试装饰器
│   ├── helpers.py            # 辅助函数
│   └── validators.py         # 验证器
├── lib/
│   └── hexin_v.js            # 问财签名生成器
├── tests/                    # 测试
│   ├── __init__.py
│   ├── run_tests.py          # 测试运行脚本
│   ├── test_03_core_modules.py       # 核心模块测试
│   └── test_04_report_generators.py  # 报告生成器测试
└── output/                   # 输出目录
    └── review_YYYYMMDD.md
```

## 运行测试

```bash
# 运行所有单元测试
python tests/run_tests.py

# 运行单个测试文件
python tests/test_03_core_modules.py
python tests/test_04_report_generators.py
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

1. 问财接口可能有反爬限制，建议适当增加延时
2. 建议在交易日收盘后运行（16:00之后）
3. 股市有风险，本报告仅供参考，不构成投资建议

## License

MIT
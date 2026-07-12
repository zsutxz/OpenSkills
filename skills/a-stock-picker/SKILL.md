---
name: a-stock-picker
description: |
  A 股稳健趋势选股与历史复盘工具。每个交易日用"均线多头 + 温和放量 + MACD 多头"
  策略从全市场筛选并推荐 3 只股票，并对历史推荐做 T+1/T+5/T+10 收益复盘。
  当用户说"今天推 3 只股""帮我选股""A 股推荐""看看选股结果""复盘历史推荐"
  "上次推荐表现怎样""回顾选股"等时自动激活。数据源为新浪/腾讯免费行情，零第三方依赖。
  ⚠️ 仅供信息参考，不构成投资建议。
license: MIT
allowed-tools: [Bash, Read, Write]
version: 0.1.0
metadata:
  category: finance
  tags: [stock, a-share, screener, backtest, quant]
---

# A 股选股与复盘

> ⚠️ 风险声明：本工具基于公开行情的量化筛选结果，**仅供信息参考，不构成任何投资建议**。
> 股市有风险，买卖决策与盈亏由使用者自行承担。

## 它做什么

- **选股（recommend.py）**：交易日从全市场快照过滤（剔除 ST/退市/亏损/停牌/次新），对候选逐个取前复权日 K，按"MA 多头排列 + 温和放量(量比 1.1~2.5) + MACD 零轴上方多头"三条件筛选，综合打分（趋势 50% + 量价 30% + 动能 20%）取 Top 3，打印中文推荐并落盘 JSONL。
- **复盘（review.py）**：读历史推荐，以推荐价为基准算 T+1/T+5/T+10 收益率，汇总胜率/平均收益/最佳最差，输出 Markdown 报告。

## 何时激活

| 用户说 | 动作 |
|--------|------|
| 今天推 3 只股 / 帮我选股 / A 股推荐 | 运行选股，展示当日 Top 3 + 风险声明 |
| 复盘 / 上次推荐表现怎样 / 回顾选股 | 运行复盘，展示收益报告 |

## 怎么用

脚本位于本 skill 目录的 `scripts/` 下（数据/报告路径由脚本按自身位置解析，与运行目录无关）。两种触发方式：

### 1. 手动（会话内）

在本 skill 目录下直接跑：

```
python scripts/recommend.py     # 当日选股：打印 Top3 + 风险声明，落盘 docs/a-stock-picker/data/recommendations.jsonl
python scripts/review.py        # 历史复盘：输出 docs/a-stock-picker/reports/review-YYYYMMDD.md
```

非交易日运行 `recommend.py` 会提示"今日非交易日"且不落盘。

### 2. 定时（无人值守）

工作日收盘后自动选股，配置见 `README.md`（Windows 任务计划程序 / Linux crontab）。交易日判定由 `trading_calendar.is_trading_day()` 负责，非交易日自动跳过。

## 输出与持久化

- `docs/a-stock-picker/data/recommendations.jsonl`：推荐历史，每行一条，追加写入，同日重跑去重覆盖。
- `docs/a-stock-picker/reports/review-YYYYMMDD.md`：复盘报告，顶部含风险声明。

## 数据与依赖

- 数据源：新浪（全市场列表 + 快照）+ 腾讯（前复权日 K），免费公开。
- 零第三方依赖，仅 Python 3.11 标准库。
- 交易日历：`trading_calendar.HOLIDAYS` 仅含 2026 节假日，**每年底需补下一年表**（详见 README「交易日历维护」），否则跨年静默误判交易日。

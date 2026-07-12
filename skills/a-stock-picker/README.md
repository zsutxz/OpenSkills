# a-stock-picker · A 股选股与复盘

> ⚠️ 风险声明：本工具基于公开行情的量化筛选结果，**仅供信息参考，不构成任何投资建议**。股市有风险，盈亏自负。

每个交易日用稳健趋势策略（均线多头 + 温和放量 + MACD 多头）推荐 3 只 A 股，并对历史推荐做 T+1/T+5/T+10 复盘。纯 Python 标准库，数据源为新浪/腾讯免费行情。

## 快速开始

```bash
# 当日选股（仅交易日生效，输出 Top3 + 落盘）
python scripts/recommend.py

# 历史复盘（读 docs/a-stock-picker/data/recommendations.jsonl，输出 docs/a-stock-picker/reports/review-YYYYMMDD.md）
python scripts/review.py
```

## 目录结构

```
scripts/
  common.py            风险声明常量 / JSONL 读写 / 收益率 / 格式化
  market_data.py       新浪列表 + 腾讯 K线（多源，纯标准库）
  trading_calendar.py  A 股交易日判定（周末 + 节假日表）
  indicators.py        MA / EMA / MACD / 量比 纯函数
  strategy.py          过滤 + 打分 + Top3
  recommend.py         选股主流程 CLI
  review.py            复盘主流程 CLI
tests/                 单元测试（python tests/test_*.py）
```

运行时产物不在本 skill 目录，统一写到仓库根 `docs/a-stock-picker/`（已在 `.gitignore`，不进仓库）：

```
docs/a-stock-picker/data/recommendations.jsonl   推荐历史（追加 + 同日去重；review.py 复盘输入）
docs/a-stock-picker/data/recommendations.md      推荐历史人类可读镜像（与 jsonl 同源，每次整体重写）
docs/a-stock-picker/reports/review-YYYYMMDD.md    复盘报告
```

## 定时任务配置（工作日 09:10 自动选股）

### Windows · 任务计划程序

1. 打开"任务计划程序" → 创建基本任务。
2. 触发器：每日 09:10（开盘前，用最近一个交易日收盘数据选当日标的）。
3. 操作：启动程序
   - 程序：`python`（或完整路径，如 `C:\Python311\python.exe`）
   - 参数：`scripts\recommend.py`
   - 起始位置：本 skill 目录的完整路径
4. 非交易日脚本自身会跳过（提示"今日非交易日"且不落盘）。

### Linux / macOS · crontab

```cron
# 工作日(周一至五) 09:10 开盘前跑选股（用最近交易日收盘数据）
10 9 * * 1-5  cd /path/to/a-stock-picker && /usr/bin/python3 scripts/recommend.py >> /tmp/a-stock-picker.log 2>&1
```

### 会话内（临时）

会话内可用 `/loop` 或定时任务临时调度 `recommend.py`（会话内定时任务约 7 天自动过期、且仅在 REPL 空闲时触发，具体行为以 Claude Code 当前版本为准）；**长期稳定用建议上面的 OS 级方案**。

## 交易日历维护（跨年必读）

`trading_calendar.HOLIDAYS` 仅内置 **2026 年**节假日表（依据国务院放假安排）。**每年底必须补下一年表**，否则跨年后春节/国庆等休市日会被误判为交易日——脚本会照常拉数据，多半得到 0 入选，**不报错（静默退化）**。更新方式：在 `scripts/trading_calendar.py` 的 `HOLIDAYS_2026` 旁新增 `HOLIDAYS_2027` 等并并入 `HOLIDAYS` 集合。

## 策略与复盘口径

- **选股条件**：剔除 ST/退市/亏损(PE≤0)/停牌/次新；MA 多头(close>MA5>MA10>MA20) + 温和放量(量比 1.1~2.5) + MACD 多头(DIF>DEA 且 DIF>0)。打分 = 趋势 50% + 量价 30% + 动能 20%。
- **复盘口径**：以推荐价为 entry，取推荐日后第 1/5/10 个交易日收盘算收益率；胜率 = 正收益占比；最佳/最差按 T+5。

## 测试

```bash
python tests/test_indicators.py
python tests/test_strategy.py
python tests/test_recommend.py
python tests/test_review.py
python tests/test_contract.py
python tests/test_market_data.py
python tests/test_trading_calendar.py
python tests/test_skill_docs.py
```

## 许可

MIT

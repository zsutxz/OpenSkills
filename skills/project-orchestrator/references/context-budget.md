# 上下文预算 参考

本文件是 `project-orchestrator` skill 上下文预算自动管理的展开，被 SKILL.md「上下文预算」章节与「通用骨架/步骤 0」引用。skill 激活后、在需要测代理指标或调阈值时再读本文件。

## 1. 硬约束与适用边界

主 agent 有两个做不到，决定了本机制是"退化形态"而非"全自动"：

- **读不到自己的上下文用量百分比**——没有这个 API，任何"用了 X% 上下文"的精确判断都无从谈起。
- **不能自己执行 `/compact` 或 `/clear`**——都是用户级斜杠命令，必须有人按（或接受 harness 在逼近上限时的自动压缩）。

因此本机制只能做到：**自动测代理指标 → 自动 tmp+mv 落盘 state.json → 提示用户按 /compact 或 /clear → 用户说"继续"后从断点续跑**。不是"自动清缓存续跑"。

**适用边界**：本机制是"防上下文爆炸 + 保可续跑"的保险丝，不是精确的上下文用量计量。代理指标与真实上下文占用只是正相关，不是因果。校准见 §3。

## 2. 代理指标计算

**主信号 = 切片进度比**（确定可数，与上下文累积强相关）：

| 当前层 | 公式 | 示例 |
|--------|------|------|
| 规划层 | planning 三阶段里 status=completed 的 / 3 | 需求+架构完成、slicing 未完 → 2/3 ≈ 0.67 |
| 执行层 | slices[] 里 status=completed 的 / slices.length | 6 切片完成 3 个 → 3/6 = 0.50 |
| 收尾层 | 免检（短阶段，通常一次 push 即完） | — |

**辅助信号 = events.log 行数**（防"进度没到但事件已爆"，如某切片反复重试、规划层粒度粗）：

```bash
wc -l < "$PROJ_ROOT/.project-orchestrator/events.log"
```

**计数方式**：主路径是 **agent 直接读 state.json 自行计数**（模型读 JSON 文本数 completed 切片即可，零外部依赖，纯净 Git Bash 亦可用）——这是默认方式。若环境装了 jq，可用下述片段做确定性核验（纯净 Git Bash 通常无 jq，跳过即可，不影响主路径）：

```bash
# 执行层进度比（awk 比 bc 在 Git Bash 更通用）
done=$(jq '[.slices[]|select(.status=="completed")]|length' "$PROJ_ROOT/.project-orchestrator/state.json")
total=$(jq '.slices|length' "$PROJ_ROOT/.project-orchestrator/state.json")
echo "$done $total" | awk '{printf "%.2f\n", $1/$2}'

# 规划层进度比
pdone=$(jq '[.planning|to_entries[]|select(.value.status=="completed")]|length' "$PROJ_ROOT/.project-orchestrator/state.json")
echo "$pdone 3" | awk '{printf "%.2f\n", $1/$2}'
```

> 触发判定：进度比 ≥ 软/硬阈值 **或** events.log 行数 ≥ 软/硬行数阈值，即按已触发的档位处理（两信号 OR，不是 AND）。

## 3. 阈值校准建议

缺省值（config.context_budget，可覆盖）：进度比 软 0.50 / 硬 0.75，events.log 行数 软 120 / 硬 200。

为何这么设：

- **0.50 软档**：留一半缓冲再 /compact，对应"做到一半清一下"的直觉。0.75 硬档：剩 25% 时上下文已偏紧，宜 /clear 彻底重置。
- **行数 120/200**：典型切片每步记 1-3 条 event，6 切片全程约 80-150 行；超 120 提示有重试或异常累积，超 200 偏重。

按项目特点调：

- **规划层粒度粗**：planning 只有 0/33%/66%/100% 四档，软档 0.5 实际要到 66%（2/3）才触发，偏晚。对策：规划层以辅助信号行数为主；或临时把 `soft_threshold` 调到 0.33，让架构出完（1/3）就先 /compact 一次。
- **单切片巨大**（slices.length=1，进度 0→100% 直跳）：中途上下文已爆但进度比仍 0%。对策：(a) 辅助信号行数兜底（这正是它存在的理由）；(b) slicing 阶段补经验约束"单切片建议改动 ≤ N 文件 / ≤ M 行"，从源头防巨切片；(c) 可选进阶——执行层用切片内 tdd 三子步（test/dev/review）的完成数 / 3 作为补充信号，把单切片再细分。
- **小项目**（3 切片以内）：可把 `enabled` 关掉，退回纯手动，避免频繁打扰。

## 4. /compact 与 /clear 两档选择

| | `/compact`（软档） | `/clear`（硬档） |
|---|---|---|
| 做什么 | 压缩当前对话为摘要，保留摘要续跑 | 彻底清空对话，全新会话 |
| 续跑依赖 | 摘要 + state.json | 只靠 state.json（会话零记忆） |
| 清得干不干净 | 留压缩摘要（有损耗风险） | 最干净，上下文归零 |
| 契合度 | 通用 | **更契合本 skill**（state.json 是唯一真相源） |

**恢复路径差异**：

- /compact 后：同一会话说"继续"，模型从压缩摘要 + state.json 续跑。
- /clear 后：**新会话**说"继续上次项目"，走「恢复流程」读 state.json 精确恢复到切片内 TDD 某一步。

**同会话去重（软档专属，头号坑）**：/compact 压缩对话但**不改 state.json**，步骤 0 再测进度比仍是同一个值，会再次弹软档，陷"提示→/compact→再提示"死循环。对策：同一会话内已对当前进度比提示过软档且用户已处理（/compact 或选"不管"），不重复打扰，直接走步骤 a。硬档走 /clear 是新会话，天然重置，无此问题。

## 5. 自主模式降级细节

autonomous=true 时无人值守，没人按 /compact 或 /clear。按档降级（不再像旧版那样跳过检查点）：

| 档位 | 本轮 cron 动作 | events.log | 之后 |
|------|---------------|-----------|------|
| 未达软档 | 正常推进下一里程碑 | 常规 | 等下次 cron |
| 达软档 | **不开**新切片/新阶段，只落盘 state.json | level=soft, note="本轮跳过新单元" | 结束本轮，等下次 cron |
| 达硬档 | 落盘 + 本轮停止 | level=hard, note="需人工 /clear" | 下次能汇报时告知需人工 /clear |

**诚实声明**：无人值守下上下文压力是固有风险。本机制只能"不再加重（达软档就不开新单元）+ 告警（落盘 + 下次汇报）"，做不到自动清缓存续跑。若项目大到单会话跑不完，自主模式本质上需要人回来 /clear——这是 durable=false（会话内值守）设计的题中之义。

cron prompt 配合：见 `templates/autonomous-cron.md`，prompt 里已要求"先跑上下文预算检查"。

## 6. 与 events.log 的集成

现有 events.log 每行一个 JSON `{ts, stage, slice, event}`（见 SKILL.md「时间戳与确定性」）。新增两种机器可 grep 的 event 值，行内追加字段向后兼容（旧解析只读 ts/stage/slice/event 不受影响）。

**`上下文预算触发`**（强制，触发即记，落盘 state.json 之后、提示用户之前）：

```json
{"ts":"2026-07-12T10:23:01+08:00","stage":"execution","slice":"slice-4","event":"上下文预算触发","level":"soft","progress":0.5,"progress_basis":"切片 3/6","event_lines":128,"action":"persisted+prompted-/compact","autonomous":false}
```

自主模式硬档示例：

```json
{"ts":"2026-07-12T11:08:00+08:00","stage":"execution","slice":"slice-5","event":"上下文预算触发","level":"hard","progress":0.75,"progress_basis":"切片 4/6","event_lines":212,"action":"persisted+stopped+awaiting-manual-/clear","autonomous":true,"note":"需人工 /clear"}
```

字段：`level`(soft/hard)、`progress`(0-1)、`progress_basis`(可读依据)、`event_lines`、`action`(本轮做了什么)、`autonomous`(bool)、可选 `note`。

**`预算例行检查`**（可选，常规测量落一条，便于事后校准阈值；体积敏感可在 config 关闭）：

```json
{"ts":"...","stage":"execution","slice":"slice-4","event":"预算例行检查","progress":0.33,"progress_basis":"切片 2/6","event_lines":88,"level":"ok","autonomous":false}
```

**恢复时识别"上次因预算而停"**：新会话「恢复流程」读 state.json 后：

```bash
grep '"event":"上下文预算触发"' "$PROJ_ROOT/.project-orchestrator/events.log" | tail -1
```

若末条 `level=hard` 且时间戳最近，向用户补一句"上次因上下文预算硬档触发而 /clear，现已从断点恢复"。

## 7. config 缺省与关闭

config.context_budget 各键缺省值（与 `references/state-schema.md` 的 schema 一致）：

| 键 | 类型 | 默认 | 用途 |
|---|---|---|---|
| `enabled` | bool | true | 总开关；false 则完全跳过步骤 0 的预算检查，退回旧行为 |
| `soft_threshold` | number [0,1] | 0.5 | 进度比 ≥ 此值触发软档（提示 /compact） |
| `hard_threshold` | number [0,1] | 0.75 | 进度比 ≥ 此值触发硬档（提示 /clear 并停） |
| `event_lines_soft` | int | 120 | events.log 行数软档（辅助信号，与进度比 OR 触发） |
| `event_lines_hard` | int | 200 | events.log 行数硬档 |

**缺省合并**（老 v2 项目 state.json 没有这个键时不报错）：

```
DEFAULT_CB = {enabled:true, soft_threshold:0.5, hard_threshold:0.75, event_lines_soft:120, event_lines_hard:200}
cb = DEFAULT_CB 与 config.context_budget 浅合并（没写用默认、写了哪项覆盖哪项、缺一半不崩）
```

**整体关闭**：`config.context_budget.enabled=false` 即跳过预算检查，步骤 0 退化为"未达软档→直接走步骤 a"（即不打扰）。适合小项目或不想被这套机制打断时。

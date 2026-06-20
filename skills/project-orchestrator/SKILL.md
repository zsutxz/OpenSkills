---
name: project-orchestrator
description: |
  端到端项目交付编排器。当用户说"从零做一个项目""启动一个项目并完整交付"
  "端到端完成这个项目""帮我把这个想法做成可发布的产品""接着上次的项目继续/
  恢复项目进度""项目现在到哪一步了""自动跑完，不用管它"，或要求按
  "需求分析 → 架构设计 → 代码开发 → 测试 → 审查 → 发布"流水线推进一个项目时，
  自动激活。会驱动子代理依次完成各阶段，过程中持久化进度（.project-orchestrator/），
  支持中断续跑、无人值守推进，仅在需求定稿/架构定稿/发布推送/部署等关键节点暂停。
  不用于单点任务（修 bug、加按钮、重构函数、改文档）——那是直接干活，不是发起完整流水线。
license: MIT
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, WebSearch, Task, CronCreate, CronDelete, CronList, TaskCreate, TaskUpdate, TaskList, TaskGet]
version: 0.1.0
metadata:
  category: orchestration
  tags: [project, pipeline, autonomous, delivery, subagent]
---

# 项目交付编排器

把一个项目从想法一路自主推进到可发布。六个阶段、子代理分工、进度全程落盘、可中断续跑。

## 使用时机

用户说类似下面这些话时激活：

- "从零做一个 XXX 项目，端到端做完"
- "启动一个项目并交付到 GitHub"
- "帮我把这个想法做成可发布的产品"
- "接着上次的项目继续 / 恢复项目进度"
- "项目现在到哪一步了"
- "自动跑完，不用管它"

**不激活的反例**：单点任务（"修个 bug""加个按钮""重构这个函数"）不触发本 skill——那是直接干活，不是发起一个完整交付流水线。

## 核心原则

1. **持续推进**：阶段内与阶段之间不要停下来等用户，除非撞上第 7 节的"确认点"。
2. **状态全落盘**：每进入/完成一个阶段、每个里程碑，都更新 `state.json` 并追加 `events.log`。这是"重启后继续"的命脉。
3. **时间戳一律用 bash `date`**，不让模型估算日期（见第 12 节）。
4. **全部产出用中文**（代码注释、文档、报告、提交信息）。
5. **子代理优先复用**：每阶段先尝试对应专家子代理，缺失再兜底（见第 6 节调度表）。绝不假设某个 `ecc:*` 一定存在。
6. **失败有界**：每个阶段 `retry_count` 上限 3，超限就暂停求助，不死磕、不空转烧预算。

## 意图路由

| 用户说 | 动作 |
|--------|------|
| 从零做 / 启动 / 端到端完成一个项目 | → 第 5 节「新建流程」 |
| 继续 / 接着 / 恢复上次项目 | → 第 9 节「恢复流程」 |
| 项目什么状态 / 到哪一步了 | `cat state.json` → 汇报当前阶段与产物 |
| 自动跑完 / 无人值守 | → 第 11 节「自主模式（cron）」 |
| 只做某个阶段（如"只做架构"） | 单阶段执行后回到 idle，不强制跑完全流程 |

## 工作目录与持久化

**所有状态写在目标项目根目录，绝不写进 OpenSkills 插件目录本身。** 否则会污染插件仓库。

状态目录：`<项目根>/.project-orchestrator/`

```
.project-orchestrator/
├── state.json          # 控制状态（阶段/状态/时间戳/计数/产物指针）
├── events.log          # 追加式事件日志，每行一个 JSON
└── artifacts/          # 各阶段产物（人机共读的 Markdown）
    ├── requirements.md
    ├── architecture.md
    ├── dev-log.md
    ├── test-report.md
    ├── review-report.md
    └── release-notes.md
```

**定位项目根**（恢复与新建都先做这步）：

1. 当前工作目录下存在 `.project-orchestrator/state.json` → 即该项目，直接用。
2. 否则问用户：新建项目放哪个路径？要恢复哪个已有项目（给路径）？不要脑补路径。

## 新建流程

1. **确认项目要素**（缺哪项问哪项，不臆测）：
   - 项目名称、一句话目标
   - 技术栈倾向（用户没想法则由架构阶段提议）
   - 目标仓库地址（可暂无，发布阶段再定）
   - 项目根路径（默认当前目录，或用户指定）
2. **建状态目录**（bash 一次完成）：
   ```bash
   PROJ_ROOT="<项目根绝对路径>"
   mkdir -p "$PROJ_ROOT/.project-orchestrator/artifacts"
   ```
3. **写入初始 `state.json`**（时间戳用 `date` 生成，schema 见第 8 节）：`status=running`、`current_phase=requirements`、六个阶段均 `pending`。
4. **`TaskCreate` 六个阶段任务**（requirements / architecture / development / testing / review / release），与 `state.json` 的 phases 对齐。
5. 追加首条 `events.log`，进入第 6 节「阶段流水线」。

## 阶段流水线（核心）

对**每一个**阶段，按下面通用骨架执行：

```
a. 读 state.json，把当前阶段标 in_progress（写 started_at 时间戳）
b. 按调度表调度子代理（优先专家 → 兜底），把任务、输入产物、输出产物路径交代清楚
c. 把阶段产物写入 artifacts/<对应>.md
d. 校验"完成判据"；不通过 → 走该阶段"失败处理"
e. 标 completed（写 completed_at 时间戳），追加 events.log
f. 若当前阶段是"确认点" → 暂停汇报等用户确认；否则不停顿，进入下一阶段
```

### 阶段调度表

| # | 阶段 | 优先子代理 | 兜底（project-role-worker 角色） | 产物 | 完成判据 |
|---|------|-----------|----------------------------------|------|----------|
| 1 | 需求分析 | `ecc:plan-prd` / `ecc:prp-prd` / `ecc:planner` | 产品经理 | `requirements.md` | 含目标/用户故事/范围/非范围/验收标准；**用户确认（确认点①）** |
| 2 | 架构设计 | `ecc:architect` / `open-skills:codebase-analyst` | 架构师 | `architecture.md` | 含技术栈/目录结构/模块职责/数据流/风险；**用户确认（确认点②）** |
| 3 | 代码开发 | 按改动规模派单（见下）；build 失败调 `ecc:build-error-resolver` 或对应语言 `ecc:<lang>-build-resolver`（如 `ecc:react-build-resolver`、`ecc:rust-build-resolver`） | 开发 | 源码 + `dev-log.md` | 关键功能可运行、build 通过 |
| 4 | 测试 | `ecc:tdd-guide` / 各语言 `ecc:*-test` | 测试 | `test-report.md` | 核心路径全绿，覆盖率达标 |
| 5 | 审查 | `ecc:code-reviewer` + `ecc:security-reviewer`（两条 Task **并行**） | 审查 | `review-report.md` | 无 🔴 高危项（或已修复） |
| 6 | 发布 | `ecc:pr` / `ecc:prp-pr` | 发布（主 agent 也可跑 git） | `release-notes.md` + commit/push | 远端可见新提交；**push 前必停（确认点③）** |

**调度规则（写死，避免歧义）**：

- 用 **Task 工具**调度子代理，`subagent_type` 填调度表"优先子代理"列。
- **先探测再调度，不靠"试调用-失败"兜底**：开工前用 Bash 跑一次 `claude plugin list`（或检查 `~/.claude/plugins/`），判断 ecc 是否安装。
  - 装了 ecc → 优先用调度表"优先子代理"列的专家（能力更强）。
  - 没装 ecc → **直接用本插件自带的 `subagent_type=project-role-worker`**（一定存在），在 prompt 里说明扮演哪个角色、任务、输入输出产物路径。
- `project-role-worker` 是本插件自带、确定可用的兜底，永远是安全默认。**绝不假设某个 `ecc:*` 一定存在**，也不要把 ecc 缺失当错误抛给用户。
- 兜底角色定义见 `agents/project-role-worker.md`。

**开发阶段（阶段 3）派单规则**：主 agent 不独自扛大项目，按改动规模分工——

- 单文件 / 小改动（几十行内）：主 agent 直接写。
- 多文件 / 新建模块 / 大功能：派给 `project-role-worker` 开发角色（或 `ecc:build-error-resolver` 处理 build 故障），主 agent 只做协调与 state 更新，避免上下文爆炸。

**各阶段失败处理**：

- **阶段 3 开发**：build 失败 → 调对应语言 `ecc:*-build-resolver`（缺失则 project-role-worker 开发角色）；`phases.development.retry_count++`；上限 3 次仍红 → 暂停，把失败信息汇报用户求助。
- **阶段 4 测试**：测试红 → 回阶段 3 修代码 → 重跑测试；`phases.testing.retry_count++`；上限 3 次暂停。
- **阶段 5 审查**：发现 🔴 高危 → 回阶段 3 修复 → **只对上轮 🔴 项做回归验证，不重开全量审查**；`phases.review.retry_count++`；上限 3 次暂停，把高危项清单交用户定夺。
- **阶段 6 发布**：push 失败 → 多半是凭证/网络/远端不存在，提示用户手动处理，不自动重试。

## 确认点（仅这 4 处停顿等用户）

| # | 节点 | 停下来做什么 |
|---|------|-------------|
| ① | 需求定稿 | 展示 `requirements.md` 要点，等用户拍板范围 |
| ② | 架构定稿 | 展示 `architecture.md` 要点，等用户拍板技术方案 |
| ③ | 发布 push 前 | 展示将推送的提交，等用户确认推送 |
| ④ | 部署前（可选） | 仅当用户要求部署/发包时才出现 |

**这四处之外，一律自主推进，不要每阶段都来问"要不要继续"。** 用户确认后，把结论记进 `state.json.decisions`（带时间戳），便于恢复时回忆"上次拍板了什么"。

## state.json

控制状态文件，**只存最小控制信息**；真正的需求/架构正文放 `artifacts/*.md`，这里只放指针。schema：

```json
{
  "schema_version": "1",
  "project": {
    "name": "项目名",
    "goal": "一句话目标",
    "repo_url": null,
    "tech_stack": [],
    "root_path": "项目根绝对路径"
  },
  "status": "running | completed | abandoned | paused",
  "current_phase": "requirements | architecture | development | testing | review | release",
  "created_at": "ISO 时间戳（bash date -Iseconds）",
  "updated_at": "ISO 时间戳",
  "completed_at": null,
  "phases": {
    "requirements": {
      "status": "pending | in_progress | completed | failed",
      "started_at": null,
      "completed_at": null,
      "retry_count": 0,
      "max_retries": 3,
      "artifact": "artifacts/requirements.md",
      "notes": ""
    }
    /* architecture / development / testing / review / release 同构 */
  },
  "decisions": [
    { "ts": "ISO", "point": "requirements | architecture | release", "summary": "用户拍板的结论" }
  ],
  "config": {
    "autonomous": false,
    "cron_job_id": null,
    "deploy_enabled": false
  }
}
```

设计要点：

- 顶层 `status` 只有 4 个值，恢复时一眼判断项目状态。
- `phases.<name>.retry_count` 是防死循环的关键。
- `artifact` 用相对项目根的路径，便于整目录迁移。
- `decisions` 记录每个确认点结论，恢复时让用户回忆上次决策。
- `config.autonomous` + `cron_job_id` 支撑无人值守模式的可取消。

**写入要原子**：用临时文件 + `mv`，避免半写损坏：

```bash
cat > "$PROJ_ROOT/.project-orchestrator/state.json.tmp" <<'JSON'
{ ... 完整内容 ... }
JSON
mv "$PROJ_ROOT/.project-orchestrator/state.json.tmp" "$PROJ_ROOT/.project-orchestrator/state.json"
```

## 恢复流程

用户说"继续 / 接着 / 恢复上次项目"时：

1. **定位项目根**（见第 4 节）。
2. `cat "$PROJ_ROOT/.project-orchestrator/state.json"`。文件不存在 → 当作新项目，走第 5 节。
3. 读取后向用户**复述**，不要默默继续：
   - 项目目标、技术栈
   - 当前 `status` 与 `current_phase`
   - 已完成阶段的产物清单（读 `phases` 里 `completed` 的 `artifact`）
   - 下一步打算做什么
4. 问用户：**继续当前阶段 / 重做当前阶段 / 放弃**，默认"继续"。
5. 把 `TaskList` 与 `state.json` 对齐：补齐缺失的 `TaskCreate`、勾掉已完成的。
6. 从 `current_phase` 续跑，走第 6 节骨架。

> 关键：恢复后绝不从需求阶段重头来——那是失忆。靠 `state.json` 接着断点走。

## 停止条件

满足**任一**即结束本 skill：

- 阶段 6 发布完成 → `status=completed`，停止。
- 用户说"停 / 放弃" → `status=abandoned`，停止。
- 某阶段 `retry_count` 超上限且用户选择不继续 → `status=paused`，停止。
- 无人值守模式下用户取消 cron（`CronDelete`）→ 停止自动推进。

## 自主模式（cron 无人值守）

用户说"自动跑完 / 无人值守 / 不用管它"时：

1. `state.json.config.autonomous = true`。
2. `CronCreate` 注册周期任务：

```
CronCreate:
  cron: "*/15 * * * *"          # 每 15 分钟唤醒一次
  recurring: true
  durable: false                # session-only，关会话即停，避免后台跑飞
  prompt: "继续推进 project-orchestrator：读 .project-orchestrator/state.json，
          执行当前阶段的下一里程碑，更新状态。遇到确认点（需求/架构定稿、push、部署）
          就暂停并向用户汇报，不要自动越过。"
```

3. **告知用户**：cron 任务仅在 REPL 空闲时触发；recurring 任务 **7 天后自动过期**。
4. 把返回的 job id 存进 `state.json.config.cron_job_id`。
5. 项目完成（`status=completed`）或用户喊停时，`CronDelete` 清掉，`config.autonomous=false`。

## 时间戳与确定性

**所有时间戳用 bash `date` 生成，禁止模型脑补"今天 / 刚才 / 几天前"。**

```bash
date -Iseconds                  # ISO 时间，用于 state.json / 报告内
date +%Y-%m-%d_%H%M%S           # 文件名用
```

**追加事件日志**（每个阶段开始/完成、每个确认点、每次重试都记一条）：

```bash
printf '{"ts":"%s","phase":"%s","event":"%s"}\n' \
  "$(date -Iseconds)" "development" "build 通过，进入测试" \
  >> "$PROJ_ROOT/.project-orchestrator/events.log"
```

## 注意事项

- **状态只写目标项目根**，绝不写进 OpenSkills 插件目录。
- **ecc 缺失不是错误**，静默走兜底即可，不要报错卡住。
- 写 `state.json` 一律用临时文件 + `mv`，防半写损坏。
- 部署 / 发包是**可选项**，不强求；"发布"默认 = `git commit` + `git push` 到 GitHub，契合本仓库"发布即推送"的理念。
- 阶段产物（`requirements.md` 等）是下游阶段的输入——架构阶段要读 `requirements.md`，开发要读 `architecture.md`，环环相扣，不要凭空发挥。
- 与 `claude-updater` skill 风格保持一致：意图路由表、分步执行流程、bash 时间戳、模板化产物。
- `TaskCreate/TaskUpdate/TaskList`（可选 todo 跟踪）与 `CronCreate/CronDelete/CronList`（无人值守）是扩展工具：本仓库目标环境可用，但**它们不是进度真相**——`state.json` 才是 source of truth。若当前环境缺这些工具，编排器照常靠 `state.json` 跟踪与手动续跑运行，cron 模式自动跳过。

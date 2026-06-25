---
name: project-orchestrator
description: |
  端到端项目交付编排器。当用户说"从零做一个项目""启动一个项目并完整交付"
  "端到端完成这个项目""帮我把这个想法做成可发布的产品""接着上次的项目继续/
  恢复项目进度""项目现在到哪一步了""自动跑完，不用管它"，或要求把一个项目
  从需求一路推进到发布时，自动激活。按「规划层（需求/架构/切片拆解）→ 执行层
  （逐切片 TDD 红绿小循环）→ 收尾层（统一发布）」三层模型推进，会驱动子代理
  分工完成，过程中持久化进度（.project-orchestrator/），支持中断续跑、无人值守
  推进，仅在需求定稿/架构定稿/切片清单定稿/发布推送/部署等关键节点暂停。
  不用于单点任务（修 bug、加按钮、重构函数、改文档）——那是直接干活，不是发起完整流水线。
license: MIT
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, WebSearch, Task, CronCreate, CronDelete, CronList, TaskCreate, TaskUpdate, TaskList, TaskGet]
version: 0.2.0
metadata:
  category: orchestration
  tags: [project, pipeline, autonomous, delivery, subagent, slicing, tdd]
---

# 项目交付编排器

把一个项目从想法一路自主推进到可发布。三层模型：规划层拆需求/架构/切片，执行层逐切片走 TDD 红绿小循环，收尾层统一发布。子代理分工、进度全程落盘、可中断续跑。

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

1. **持续推进**：阶段内、切片之间不要停下来等用户，除非撞上第 7 节的"确认点"。
2. **状态全落盘**：每进入/完成一个阶段或切片、每个里程碑，都更新 `state.json` 并追加 `events.log`。这是"重启后继续"的命脉。
3. **时间戳一律用 bash `date`**，不让模型估算日期（见第 12 节）。
4. **全部产出用中文**（代码注释、文档、报告、提交信息）。
5. **子代理优先复用**：每阶段/每切片先尝试对应专家子代理，缺失再兜底（见第 6 节调度表）。绝不假设某个 `ecc:*` 一定存在。
6. **失败有界**：每个阶段、每个切片 `retry_count` 上限 3，超限就暂停求助，不死磕、不空转烧预算。
7. **切片是执行单位，TDD 测试先行**：大项目先在规划层拆成可独立交付的切片；执行层每个切片内严格走「先写测试(红)→开发到绿→小审查」红绿循环，不把开发和测试拆成两个割裂阶段。

## 意图路由

| 用户说 | 动作 |
|--------|------|
| 从零做 / 启动 / 端到端完成一个项目 | → 第 5 节「新建流程」 |
| 继续 / 接着 / 恢复上次项目 | → 第 9 节「恢复流程」 |
| 项目什么状态 / 到哪一步了 | `cat state.json` → 汇报当前 stage/切片与产物 |
| 自动跑完 / 无人值守 | → 第 11 节「自主模式（cron）」 |
| 只做规划层某阶段（如"只做架构"）/ 只跑某个切片 | 单阶段/单切片执行后回到 idle，不强制跑完全流程 |

## 工作目录与持久化

**所有状态写在目标项目根目录，绝不写进 OpenSkills 插件目录本身。** 否则会污染插件仓库。

状态目录：`<项目根>/.project-orchestrator/`

```
.project-orchestrator/
├── state.json          # 控制状态（stage/切片/时间戳/计数/产物指针）
├── events.log          # 追加式事件日志，每行一个 JSON
└── artifacts/          # 各阶段产物（人机共读的 Markdown）
    ├── requirements.md
    ├── architecture.md
    ├── slices.md         # 切片拆解清单（规划层产物，执行层输入）
    ├── dev-log.md        # 跨切片开发记录，按切片分段追加
    ├── review-report.md  # 跨切片审查记录，按切片分段追加
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
3. **写入初始 `state.json`**（时间戳用 `date` 生成，schema 见第 8 节）：`status=running`、`current_stage=planning`、`current_slice_index=null`、`planning` 三阶段均 `pending`、`slices=[]`、`release` 为 `pending`。
4. **`TaskCreate` 规划层三个任务**（requirements / architecture / slicing），与 `state.json.planning` 对齐。切片任务待 slicing 完成后按 `slices[]` 补建，发布任务最后建——始终让 TaskList 与 state.json 对齐。
5. 追加首条 `events.log`，进入第 6 节「阶段流水线」。

## 阶段流水线（核心）

模型分三层：**规划层**（一次性：需求→架构→切片拆解）→ **执行层**（逐切片 TDD 小循环）→ **收尾层**（一次性：统一发布）。规划层与收尾层各阶段、执行层每个切片，都套下面的通用骨架。

### 通用骨架

```
0. [Token 检查点] 进入新阶段/新切片前，先向用户展示一行状态：
      ⚙️ 即将进入「<阶段/切片名>」（规划层 X/3 或 切片 Y/N）。上下文是否还充裕？
      [继续] / [先 /compact 再继续] / [保存进度，稍后重启]
   - 用户选"继续" → 直接走步骤 a。
   - 用户选"/compact" → 提示执行 /compact，等用户确认压缩完成后再走步骤 a。
   - 用户选"重启" → 提示：进度已保存至 state.json，重启后说"继续上次项目"即可恢复。然后停止。
   - 无人值守模式（config.autonomous=true）→ 跳过本检查点，不打断自动推进。
a. 读 state.json，把当前阶段/切片标 in_progress（写 started_at 时间戳）
b. 按调度表调度子代理（优先专家 → 兜底），把任务、输入产物、输出产物路径交代清楚
c. 把产物写入 artifacts/<对应>.md（切片开发/审查记录追加进 dev-log.md / review-report.md）
d. 校验"完成判据"；不通过 → 走该阶段/切片"失败处理"
e. 标 completed（写 completed_at 时间戳），追加 events.log
f. 若是"确认点" → 暂停汇报等用户确认；否则不停顿，推进下一步
```

### 6.1 规划层（一次性）

依次跑需求分析 → 架构设计 → 切片拆解，每阶段套通用骨架。切片拆解完成后 `current_stage` 从 `planning` 切到 `execution`，`current_slice_index=0`。

**规划层调度表**：

| # | 阶段 | 优先子代理 | 兜底（project-role-worker 角色） | 产物 | 完成判据 |
|---|------|-----------|----------------------------------|------|----------|
| 1 | 需求分析 | `ecc:plan-prd` / `ecc:prp-prd` / `ecc:planner` | 产品经理 | `requirements.md` | 含目标/用户故事/范围/非范围/验收标准；**用户确认（确认点①）** |
| 2 | 架构设计 | `ecc:architect` | 架构师 | `architecture.md` | 含技术栈/目录结构/模块职责/数据流/风险；**用户确认（确认点②）** |
| 3 | 切片拆解 | `ecc:planner` / `ecc:plan` / `ecc:prp-plan` | 架构师 | `slices.md` | 把项目拆成 N 个可独立交付的切片，**每切片有 title/goal/可验证 acceptance**；**用户确认（确认点③）** |

> slicing 阶段的产物同时填进 `state.json.slices[]`：每个切片落 `id`/`title`/`goal`/`acceptance`/`status=pending`。**acceptance 必须具体可测**，否则执行层 TDD 测试先行无从下笔——这是 slicing 阶段的硬性完成判据。

### 6.2 执行层（逐切片 TDD 小循环）

对 `slices[]` 里**每个**切片，按下面小循环推进；切片之间不停顿（无确认点），自主跑到最后一个切片：

```
a. 读 state.json，slices[i].status=in_progress（写 started_at），current_slice_index=i
b. 测试先行（红）：调度测试角色，输入=slices.md 该切片 goal+acceptance 与 architecture.md；
   产出该切片测试用例，确认它们当前跑红（功能尚未实现）。slices[i].tdd.test=completed
c. 开发到绿：调度开发角色（按改动规模派单，见下），实现到该切片测试全绿；
   build 失败调对应语言 ecc:*-build-resolver（缺失则 project-role-worker 开发角色）。
   slices[i].tdd.dev=completed
d. 切片小审查：ecc:code-reviewer + ecc:security-reviewer 两条 Task **并行**，**仅审查本切片 diff**；
   发现 🔴 高危 → 回步骤 b/c 重跑该切片测试（不重开全量审查），retry_count++，上限 3 暂停求助。
   slices[i].tdd.review=completed
e. git commit（不 push）：commit message 引用 slice id，把 sha 记进 slices[i].commit_sha
f. slices[i].status=completed（写 completed_at），追加 events.log，current_slice_index++
```

**执行层调度表**：

| 切片内步骤 | 优先子代理 | 兜底（project-role-worker 角色） |
|-----------|-----------|----------------------------------|
| 测试先行（红） | `ecc:tdd-guide` / 各语言 `ecc:*-test` | 测试 |
| 开发实现（绿） | 按改动规模派单（见下） | 开发 |
| 切片小审查 | `ecc:code-reviewer` + `ecc:security-reviewer`（并行，仅本切片 diff） | 审查 |

**开发派单规则**（步骤 c 内部）：主 agent 不独自扛大改动，按规模分工——

- 单文件 / 小改动（几十行内）：主 agent 直接写。
- 多文件 / 新建模块 / 大功能：派给 `project-role-worker` 开发角色，主 agent 只做协调与 state 更新，避免上下文爆炸。

### 6.3 收尾层（一次性）

所有切片 `completed` 后，`current_stage` 切到 `release`：

```
a. release.status=in_progress（写 started_at）
b. 汇总 release-notes.md（聚合各切片交付内容，引用 commit_sha）
c. [确认点④] 展示将推送的提交清单，等用户确认推送
d. git push（一次推完所有切片提交）
e. release.status=completed，顶层 status=completed，停止
```

**收尾调度**：发布优先 `ecc:pr` / `ecc:prp-pr`，兜底 project-role-worker 发布角色（主 agent 也可直接跑 git）。

### 调度规则（三层通用，写死避免歧义）

- 用 **Task 工具**调度子代理，`subagent_type` 填调度表"优先子代理"列。
- **先探测再调度，不靠"试调用-失败"兜底**：开工前用 Bash 跑一次 `claude plugin list`（或检查 `~/.claude/plugins/`），判断 ecc 是否安装。
  - 装了 ecc → 优先用调度表"优先子代理"列的专家（能力更强）。
  - 没装 ecc → **直接用本插件自带的 `subagent_type=project-role-worker`**（一定存在），在 prompt 里说明扮演哪个角色、任务、输入输出产物路径。
- `project-role-worker` 是本插件自带、确定可用的兜底，永远是安全默认。**绝不假设某个 `ecc:*` 一定存在**，也不要把 ecc 缺失当错误抛给用户。
- 兜底角色定义见 `agents/project-role-worker.md`。

## 确认点（仅这 5 处停顿等用户）

| # | 节点 | 停下来做什么 |
|---|------|-------------|
| ① | 需求定稿 | 展示 `requirements.md` 要点，等用户拍板范围 |
| ② | 架构定稿 | 展示 `architecture.md` 要点，等用户拍板技术方案 |
| ③ | 切片清单定稿 | 展示 `slices.md`（切片范围/顺序/每切片 acceptance），等用户拍板再进入执行层 |
| ④ | 发布 push 前 | 展示将推送的提交清单，等用户确认推送 |
| ⑤ | 部署前（可选） | 仅当用户要求部署/发包时才出现 |

**这五处之外，一律自主推进，不要每阶段/每切片都来问"要不要继续"。** 用户确认后，把结论记进 `state.json.decisions`（带时间戳，`point` 用 requirements/architecture/slicing/release），便于恢复时回忆"上次拍板了什么"。

## state.json

控制状态文件，**只存最小控制信息**；真正的需求/架构/切片正文放 `artifacts/*.md`，这里只放指针与进度。schema：

```json
{
  "schema_version": "2",
  "project": {
    "name": "项目名",
    "goal": "一句话目标",
    "repo_url": null,
    "tech_stack": [],
    "root_path": "项目根绝对路径"
  },
  "status": "running | completed | abandoned | paused",
  "current_stage": "planning | execution | release",
  "current_slice_index": null,
  "created_at": "ISO 时间戳（bash date -Iseconds）",
  "updated_at": "ISO 时间戳",
  "completed_at": null,
  "planning": {
    "requirements": {
      "status": "pending | in_progress | completed | failed",
      "started_at": null,
      "completed_at": null,
      "retry_count": 0,
      "max_retries": 3,
      "artifact": "artifacts/requirements.md",
      "notes": ""
    },
    "architecture": { /* 同构, artifact: "artifacts/architecture.md" */ },
    "slicing":      { /* 同构, artifact: "artifacts/slices.md" */ }
  },
  "slices": [
    {
      "id": "slice-1",
      "title": "切片标题",
      "goal": "这个切片交付什么",
      "acceptance": ["可验证的验收条件1", "..."],
      "status": "pending | in_progress | completed | failed",
      "tdd": {
        "test":   { "status": "pending | completed", "started_at": null, "completed_at": null },
        "dev":    { "status": "pending | completed", "started_at": null, "completed_at": null },
        "review": { "status": "pending | completed", "started_at": null, "completed_at": null }
      },
      "commit_sha": null,
      "retry_count": 0,
      "max_retries": 3,
      "notes": ""
    }
  ],
  "release": {
    "status": "pending | in_progress | completed | failed",
    "started_at": null,
    "completed_at": null,
    "artifact": "artifacts/release-notes.md",
    "pushed": false,
    "notes": ""
  },
  "decisions": [
    { "ts": "ISO", "point": "requirements | architecture | slicing | release", "summary": "用户拍板的结论" }
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
- `current_stage` + `current_slice_index` 取代旧版 `current_phase`，恢复时一眼定位在哪层、哪个切片。
- `slices[]` 是动态数组，slicing 阶段产出后才填；每个切片内嵌 `tdd.test/dev/review` 三步状态，小循环进度可追踪、可断点续跑。
- `commit_sha` 让每个切片可独立回滚。
- `phases.<name>.retry_count` / `slices[i].retry_count` 是防死循环的关键。
- `artifact` 用相对项目根的路径，便于整目录迁移。
- `decisions` 记录每个确认点结论，恢复时让用户回忆上次决策。
- `config.autonomous` + `cron_job_id` 支撑无人值守模式的可取消。
- **读到 `schema_version: "1"` 的旧项目**：属过时格式，向用户提示「旧版 state，建议新建或人工核对」，不要静默按 v2 误读。

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
2. `cat "$PROJ_ROOT/.project-orchestrator/state.json"`。文件不存在 → 当作新项目，走第 5 节。`schema_version` 非 `"2"` → 提示旧版，按上节规则处理。
3. 读取后向用户**复述**，不要默默继续：
   - 项目目标、技术栈
   - 当前 `status` 与 `current_stage`（以及 `current_slice_index`）
   - 已完成阶段的产物清单、切片进度 X/N（读 `slices[]` 里 `completed` 的）
   - 下一步打算做什么
4. 问用户：**继续当前阶段/切片 / 重做当前阶段/切片 / 放弃**，默认"继续"。
5. 把 `TaskList` 与 `state.json` 对齐：补齐缺失的 `TaskCreate`、勾掉已完成的。
6. 按 `current_stage` 续跑，走第 6 节对应层骨架：
   - `planning` → 规划层当前未完成子阶段。
   - `execution` → `current_slice_index` 指向的切片；切片内看 `tdd.test/dev/review` 哪步未完，从该步续跑。
   - `release` → 收尾层续跑。

> 关键：恢复后绝不从需求阶段重头来——那是失忆。靠 `state.json` 接着断点走，精确到切片内 TDD 的某一步。

## 停止条件

满足**任一**即结束本 skill：

- 收尾层发布完成（所有切片 completed 且 release completed）→ `status=completed`，停止。
- 用户说"停 / 放弃" → `status=abandoned`，停止。
- 某阶段或某切片 `retry_count` 超上限且用户选择不继续 → `status=paused`，停止。
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
          按 current_stage 与 current_slice_index 执行下一里程碑（规划层下一阶段 /
          当前切片内 TDD 下一步 / 收尾发布），更新状态。遇到确认点（需求/架构/切片
          清单定稿、push、部署）就暂停并向用户汇报，不要自动越过。"
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

**追加事件日志**（每个阶段/切片开始与完成、每个确认点、每次重试都记一条）：

```bash
printf '{"ts":"%s","stage":"%s","slice":"%s","event":"%s"}\n' \
  "$(date -Iseconds)" "execution" "slice-2" "测试转绿，进入切片小审查" \
  >> "$PROJ_ROOT/.project-orchestrator/events.log"
```

## 注意事项

- **状态只写目标项目根**，绝不写进 OpenSkills 插件目录。
- **ecc 缺失不是错误**，静默走兜底即可，不要报错卡住。
- 写 `state.json` 一律用临时文件 + `mv`，防半写损坏。
- **切片是执行层单位，TDD 测试先行**：规划层 slicing 必须给出每切片可验证的 acceptance，执行层才能先写测试再实现；acceptance 模糊会让 TDD 无从下笔。
- 部署 / 发包是**可选项**，不强求；"发布"默认 = 各切片 commit + 收尾层一次 `git push` 到 GitHub，契合本仓库"发布即推送"的理念。
- 上下游环环相扣：架构阶段读 `requirements.md`，slicing 读 `architecture.md`，执行层切片读 `slices.md` + `architecture.md`，不要凭空发挥。
- `TaskCreate/TaskUpdate/TaskList`（可选 todo 跟踪）与 `CronCreate/CronDelete/CronList`（无人值守）是扩展工具：本仓库目标环境可用，但**它们不是进度真相**——`state.json` 才是 source of truth。若当前环境缺这些工具，编排器照常靠 `state.json` 跟踪与手动续跑运行，cron 模式自动跳过。

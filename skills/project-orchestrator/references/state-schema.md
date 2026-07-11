# state.json schema 参考

本文件是 `project-orchestrator` skill 的 `state.json` 控制状态格式定义，被 SKILL.md「工作目录与持久化」「新建流程」「恢复流程」引用。skill 激活后，在需要读写 `state.json` 时再读本文件。

控制状态文件**只存最小控制信息**；真正的需求/架构/切片正文放 `artifacts/*.md`，这里只放指针与进度。

## schema

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
        "review": {
          "status": "pending | in_progress | completed | failed",
          "started_at": null,
          "completed_at": null,
          "verdict": "pass | pass-with-deferred | fail",  /* 完成前为 null */
          "findings": {"critical": 0, "high": 0, "medium": 0, "low": 0},
          "deferred": ["缓修的低级别问题一句话…"],
          "artifact": "artifacts/review-report.md#slice-N"
        }
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
    "deploy_enabled": false,
    "context_budget": {                    /* 上下文预算自动管理,见 SKILL.md「上下文预算」 */
      "enabled": true,                     /* 总开关,false 则跳过预算检查 */
      "soft_threshold": 0.5,               /* 进度比软档,触发提示 /compact */
      "hard_threshold": 0.75,              /* 进度比硬档,触发提示 /clear 并停 */
      "event_lines_soft": 120,             /* events.log 行数软档(辅助信号) */
      "event_lines_hard": 200              /* events.log 行数硬档 */
    }
  }
}
```

## 设计要点

- 顶层 `status` 只有 4 个值，恢复时一眼判断项目状态。
- `current_stage` + `current_slice_index` 取代旧版 `current_phase`，恢复时一眼定位在哪层、哪个切片。
- `slices[]` 是动态数组，slicing 阶段产出后才填；每个切片内嵌 `tdd.test/dev/review` 三步状态，小循环进度可追踪、可断点续跑。
- `tdd.review` 带 `verdict`/`findings`/`deferred`/`artifact` 而非单纯布尔态：让恢复时/用户能从 state.json 一眼确认 review 真做过、审出什么（对症"空标 completed 跳过审查"）；`findings` 用四档计数——state.json 存英文键名 `{critical,high,medium,low}`（代码友好），展示层映射 critical=🔴/high=🟠/medium=🟡/low=⚪，与 SKILL.md §6.2 门禁判定及 review-report.md 同词汇。
- `commit_sha` 让每个切片可独立回滚。
- `planning.<name>.retry_count` / `slices[i].retry_count` 是防死循环的关键。
- `artifact` 用相对项目根的路径，便于整目录迁移。
- `decisions` 记录每个确认点结论，恢复时让用户回忆上次决策。
- `config.autonomous` + `cron_job_id` 支撑无人值守模式的可取消。
- `config.context_budget` 控制上下文预算自动管理（详见 SKILL.md「上下文预算」与 `references/context-budget.md`）：纯新增可选键，**老 v2 项目缺省合并不报错、不当作旧版**——
  DEFAULT_CB = {enabled:true, soft_threshold:0.5, hard_threshold:0.75, event_lines_soft:120, event_lines_hard:200}；
  读取时 DEFAULT_CB 与 config.context_budget 浅合并（没写用默认、写了哪项覆盖哪项、缺一半不崩）。本次仅新增可选键，**schema_version 保持 "2" 不 bump**。

## 原子写入

写 `state.json` 一律用临时文件 + `mv`，避免半写损坏：

```bash
cat > "$PROJ_ROOT/.project-orchestrator/state.json.tmp" <<'JSON'
{ ... 完整内容 ... }
JSON
mv "$PROJ_ROOT/.project-orchestrator/state.json.tmp" "$PROJ_ROOT/.project-orchestrator/state.json"
```

## 旧版兼容

读到 `schema_version: "1"` 的旧项目：属过时格式，向用户提示「旧版 state，建议新建或人工核对」，不要静默按 v2 误读。

# 自主模式（cron 无人值守）模板

本文件是 `project-orchestrator` skill 的自主/无人值守模式细节与 cron prompt 模板，被 SKILL.md「意图路由」引用。仅当用户说"自动跑完 / 无人值守 / 不用管它"时启用。

## 启用步骤

1. `state.json.config.autonomous = true`。
2. `CronCreate` 注册周期任务（模板见下）。
3. **告知用户**：cron 任务仅在 REPL 空闲时触发；recurring 任务 **7 天后自动过期**。
4. 把返回的 job id 存进 `state.json.config.cron_job_id`。
5. 项目完成（`status=completed`）或用户喊停时，`CronDelete` 清掉，`config.autonomous=false`。

## CronCreate 模板

```
CronCreate:
  cron: "*/15 * * * *"          # 每 15 分钟唤醒一次
  recurring: true
  durable: false                # session-only，关会话即停，避免后台跑飞
  prompt: "继续推进 project-orchestrator：读 .project-orchestrator/state.json，
          先跑上下文预算检查（见 SKILL.md「上下文预算」与步骤 0）——测切片进度比与
          events.log 行数：软档本轮不开新切片/新阶段、只落盘等下次；硬档落盘并停本轮告警。
          未触发阈值时，按 current_stage 与 current_slice_index 执行下一里程碑
          （规划层下一阶段 / 当前切片内 TDD 下一步 / 收尾发布），更新状态。遇到确认点
          （需求/架构/切片清单定稿、push、部署）就暂停并向用户汇报，不要自动越过。"
```

> `durable: false` 是刻意的：无人值守只在当前会话存活，会话关闭即停，避免后台无人看管跑飞。需要跨会话值守再说。
>
> prompt 开头的"上下文预算检查"与 SKILL.md 步骤 0 的自主模式分支对齐：无人值守下没人按 /compact 或 /clear，所以达软档就本轮不开新单元、达硬档就停本轮告警，等用户回来人工 /clear。详见 `references/context-budget.md` §5。

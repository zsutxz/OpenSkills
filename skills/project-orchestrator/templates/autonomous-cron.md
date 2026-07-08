# 自主模式（cron 无人值守）模板

本文件是 `project-orchestrator` skill 的自主/无人值守模式细节与 cron prompt 模板，被 SKILL.md「意图路由」引用。仅当用户说"自动跑完 / 无人值守 / 不用管它"时启用。

## 启用步骤

1. `state.json.config.autonomous = true`。
2. `CronCreate` 注册周期任务（模板见下）。
3. **告知用户**：cron 任务仅在 REPL 空闲时触发；recurring 任务 **7 天后自动过期**；`durable=true` 跨会话存活——关掉再重开 Claude Code，任务自动恢复并在新会话空闲时继续唤醒。
4. 把返回的 job id 存进 `state.json.config.cron_job_id`。
5. 项目完成（`status=completed`）或用户喊停时，`CronDelete` 清掉，`config.autonomous=false`。**durable 任务不随会话结束而消失，这步必须做**，否则空跑到 7 天过期。

## CronCreate 模板

```
CronCreate:
  cron: "*/15 * * * *"          # 每 15 分钟唤醒一次
  recurring: true
  durable: true                 # 持久化到磁盘，跨会话存活：会话断了下个周期由新会话读 state.json 自动接力
  prompt: "继续推进 project-orchestrator：先读 .project-orchestrator/state.json，
          若 status 为 completed/abandoned/paused 则 CronDelete 自清理并停止；
          否则按 current_stage 与 current_slice_index 执行下一里程碑（规划层下一阶段 /
          当前切片内 TDD 下一步 / 收尾发布），更新状态并落盘。遇到确认点（需求/架构/切片
          清单定稿、push、部署）就暂停并向用户汇报，不要自动越过。"
```

> **`durable=true` 是自动接力的关键**：cron 持久化到 `.claude/scheduled_tasks.json`，即使当前会话上下文已满或被关闭，用户重开 Claude Code 后任务自动恢复，在干净的新会话里读 `state.json` 接着断点跑——这就是本方案"token 满了自动续命"的实现：prompt 自带读盘逻辑，不依赖旧会话上下文。
>
> **代价与兜底**：durable 任务不会随会话结束而消失，故完成/喊停时**必须** `CronDelete`（启用步骤 5）；prompt 里的"status 终态则自清理"是第二道闸，两道闸防它空转到 7 天自动过期。
>
> **同一会话内的局限**：durable 只解决"跨会话接力"，不解决"同一会话内上下文持续增长"。若长时间不重开会话，cron 在同一上下文里反复 fire 仍会撑爆 token——届时靠 Claude Code 自动 /compact，或主动重开会话让 durable 任务在新上下文接力。

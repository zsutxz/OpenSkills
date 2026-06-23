---
description: 启动端到端项目交付流水线。接受项目想法作为参数，激活 project-orchestrator skill，按"需求分析 → 架构设计 → 代码开发 → 测试 → 审查 → 发布"六阶段推进，过程中持久化进度、支持中断续跑。
allowed-tools: [Bash, Read, Write, Edit, Glob, Grep, WebSearch, Task, CronCreate, CronDelete, CronList, TaskCreate, TaskUpdate, TaskList, TaskGet]
argument-hint: <项目想法或描述>
---

# /open-skills:goal — 启动项目交付流水线

把一个想法端到端推进到可发布状态。

## 参数处理

- **有 `$ARGUMENTS`**：直接作为项目目标，跳过询问，进入确认要素流程。
- **无 `$ARGUMENTS`**：提示用户描述项目想法，再继续。

## 执行

激活 `project-orchestrator` skill，按以下意图路由分发：

| 场景 | 路由 |
|------|------|
| 首次启动（无 `.project-orchestrator/state.json`） | 新建流程：以 `$ARGUMENTS` 为项目目标，确认名称/技术栈/路径后开跑 |
| 已有进度（存在 `state.json`） | 恢复流程：读取状态，复述进度，询问继续/重做/放弃 |
| 用户加 `--auto` 或说"自动跑完" | 进入无人值守 cron 模式（每 15 分钟唤醒一次） |

## 快捷用法示例

```
/open-skills:goal 做一个 CLI 工具，把 GitHub Issues 同步成本地 Markdown
/open-skills:goal 用 React + FastAPI 做一个个人任务管理应用
/open-skills:goal                   # 无参数，提示输入想法
```

## 注意

本命令是 `project-orchestrator` skill 的手动入口封装，行为与直接描述项目目标完全一致。进度持久化在目标项目的 `.project-orchestrator/` 目录，不影响 OpenSkills 插件目录本身。

---
name: session-resume
description: |
  通用会话恢复。当用户说"继续上一次""接着上次""恢复上次任务""上次干到哪了"
  "恢复会话""接着干""从上次断的地方继续"时自动激活；SessionStart 钩子检测到上次
  未完成任务、用户在弹出选择里选了"恢复上次任务"时也会进入本技能。读取上次退出时
  留下的指针快照（.session-resume/last-session.json），回放 transcript 重建上下文，
  复述上次进度并从断点续跑，绝不全重来。不用于全新任务——那是直接干活，不是恢复。
license: MIT
allowed-tools: [Bash, Read, Glob, Grep, Write, Edit, TaskCreate, TaskUpdate, TaskList, TaskGet]
version: 0.1.0
metadata:
  category: session
  tags: [session, resume, recovery, persistence]
---

# 会话恢复

Claude 上次退出时（SessionEnd 钩子 `session-snapshot.sh`）会把"会话指针"写到
`<项目根>/.session-resume/last-session.json`。本技能读这个快照、回放 transcript、
复述进度、从断点接着干。新会话启动时（SessionStart 钩子 `session-restore.sh`）
若检测到上次可能未完成，会先提示用户选择是否恢复——选"恢复"就进入本技能。

## 使用时机

- 用户说："继续上一次 / 接着上次 / 恢复上次任务 / 上次干到哪了 / 接着干"
- SessionStart 弹出选择，用户选了「恢复上次任务」

**不激活的反例**：全新任务（"帮我加个功能""修这个 bug"）不触发本技能——那是直接干活，不是恢复。

## 核心原则

1. **接断点，绝不重头**：靠 transcript + 快照还原"上次做到哪"，从那里接着走，不重新分析、不重新规划已经做过的部分。
2. **先复述再动手**：恢复后先把"上次目标 / 断点 / 未完成项 / git 状态"讲清楚，让用户确认方向，再继续——避免理解偏差。
3. **快照只是指针，transcript 才是真相**：`last-session.json` 只存 session_id / transcript_path / git 摘要等指针；真正的对话内容在 transcript JSONL 里，要读它才能知道上次在做什么。
4. **全部用中文**汇报与注释；时间戳一律 `bash date`，不脑补。
5. **诚实降级**：快照缺失、transcript 失效，就如实说明"能恢复多少"，不假装记得。

## 意图路由

| 用户说 / 场景 | 动作 |
|--------|------|
| 继续上次 / 接着干 / 恢复 | → 第 5 节「恢复流程」 |
| 上次干到哪了 | 读快照 + transcript，**只汇报**不自动动手，等用户决定 |
| 不想要这个恢复了 / 清掉 | 删 `.session-resume/last-session.json`（先确认） |

## 快照与 transcript

**快照**（SessionEnd 钩子写，固定结构）：

```
<项目根>/.session-resume/last-session.json
{
  "schema_version": "1",
  "session_id": "...",
  "cwd": "...",
  "project_root": "...",
  "transcript_path": "...上次会话的 JSONL 路径...",
  "saved_at": "ISO 时间戳",
  "git": { "branch": "...", "uncommitted_files": N }
}
```

**transcript**（`~/.claude/projects/<编码项目路径>/<session-uuid>.jsonl`）：每行一个 JSON 事件，含完整的用户/助手消息与工具调用。`transcript_path` 指向它。

## 恢复流程

1. **定位项目根**：
   ```bash
   git rev-parse --show-toplevel 2>/dev/null || pwd
   ```
2. **读快照**：`cat "<项目根>/.session-resume/last-session.json"`。
   - **快照不存在** → 走第 6 节「崩溃兜底」。
3. **读 transcript 最后 ~30 行**，理解上次上下文（这是恢复的核心）：
   ```bash
   # 路径可能含反斜杠/空格，务必加引号
   tail -n 30 "<transcript_path>"
   ```
   然后用 Read 工具读该文件尾部，重点提取：
   - **最后一条用户消息**：上次让 Claude 做什么。
   - **最后一条助手消息**：上次做到哪、说了什么、下一步打算。
   - **最后的 TodoWrite**（若有）：里面 `pending` / `in_progress` 的项就是未完成清单。
4. **核对 git 现状**（快照里的计数可能已过期）：
   ```bash
   git status --short
   git log --oneline -5
   ```
   判断工作区有没有新改动、上次改动是否已提交。
5. **复述**（讲清楚再问，不要默默继续）：
   - 项目根、上次目标
   - 断点位置（上次卡在哪一步）
   - 未完成项清单（来自 TodoWrite 或推断）
   - git 状态（分支、有无未提交改动）
   - **打算接着做的下一步**
6. **确认方向**：继续当前 / 重做某步 / 放弃，默认"继续"。若 `uncommitted_files > 0`，提醒用户工作区有改动、注意别覆盖。
7. **续跑**：从断点接着做。完成一个里程碑后，**询问**是否清理 `.session-resume/last-session.json`（默认保留，避免误删）。

> 关键：恢复后从断点接着走，绝不从头上来——那是失忆。靠 transcript + 快照接断点。

## 崩溃兜底（快照缺失时）

SessionEnd 钩子不保证总执行（崩溃 / 强杀 / 断电会漏）。这时 `last-session.json` 可能不存在，但 transcript 通常还在：

1. 在 `~/.claude/projects/` 下按**最近修改时间**找当前项目对应的 transcript：
   ```bash
   # 项目路径会被编码进目录名（斜杠变连字符），找最近改过的 jsonl
   ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -5
   ```
2. 把候选列给用户确认是哪个会话（不要脑补），再读其尾部走第 5 节流程。
3. 若连 transcript 都找不到 → 如实告知"没找到可恢复的会话"，请用户重新描述任务。

## 注意事项

- **快照只读不写**：本技能只**读** `.session-resume/last-session.json`；写它的是 SessionEnd 钩子。续跑时更新的应是目标项目本身的代码/文档，不是这个快照。
- **transcript 路径可能失效**（换机器 / 会话已清理）：失效就降级到"只用快照指针 + git 状态 + 用户口述"恢复，能恢复多少算多少并说明。
- **与 project-orchestrator 区分**：那个是"项目六阶段流水线"的续跑（读 `.project-orchestrator/state.json`）；本技能是"任意会话"的续跑（读 transcript）。两者可共存：先按本技能恢复上下文，若发现是 project-orchestrator 流水线，转交它继续。
- **SessionStart 已展示过就别重复弹**：若用户是被启动钩子的选择引导进来的，跳过第 5 步的"再问一次"，直接复述 + 续跑。

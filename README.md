# OpenSkills — Claude Code 个人技能合集

> 个人 Claude Code 插件，包含实用的开发者工具：命令、代理、技能、钩子。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能一览

| 组件 | 命令/名称 | 功能说明 |
|------|-----------|----------|
| 📋 命令 | `/open-skills:stats` | 分析代码库统计信息（语言分布、文件数、行数等） |
| 📋 命令 | `/open-skills:commit` | 分析暂存更改，生成 Conventional Commits 格式的提交信息 |
| 📋 命令 | `/open-skills:goal` | 把一个想法端到端推进到可发布：激活 project-orchestrator 六阶段流水线 |
| 🤖 代理 | `project-role-worker` | 项目流水线兜底执行者，分饰需求/架构/开发/测试/审查/发布六角色 |
| 🤖 代理 | `translate-it-article` | 将英文 IT 技术文章翻译成通俗中文并保存到本地 |
| 🧠 技能 | `project-orchestrator` | 端到端项目交付编排：需求→架构→开发→测试→审查→发布，自主推进且可续跑 |
| 🧠 技能 | `commit-style` | Git 提交规范知识，讨论 commit 时自动激活 |
| 🧠 技能 | `claude-updater` | 统一管理 Claude Code 生态更新，检查 CLI、插件与新功能 |
| 🧠 技能 | `session-resume` | "继续上一次"：读上次快照 + transcript，从断点续跑 |
| 🛡️ 钩子 | `guard-secrets` | 写入文件前检测敏感信息（API 密钥、密码等） |
| 🛡️ 钩子 | `session-snapshot` / `session-restore` | 退出时保存会话指针，重启时展示上次未完成任务让你选择恢复 |

## 安装方式

### 方式一：从 GitHub 安装（推荐）

在 Claude Code 中运行：

```
/plugin install zsutxz/OpenSkills
```

### 方式二：本地测试

克隆仓库并指定插件目录：

```bash
git clone https://github.com/zsutxz/OpenSkills.git
cd OpenSkills
claude --plugin-dir .
```

### 方式三：手动安装

将仓库内容复制到 Claude Code 插件目录：

```bash
# 克隆到插件缓存目录
git clone https://github.com/zsutxz/OpenSkills.git ~/.claude/plugins/cache/open-skills
```

然后在 `~/.claude/settings.json` 中启用：

```json
{
  "enabledPlugins": {
    "open-skills": true
  }
}
```

## 使用指南

### 命令

#### `/open-skills:stats [path]`

分析代码库统计信息。

```
# 分析当前目录
/open-skills:stats

# 分析指定项目
/open-skills:stats /path/to/project
```

输出包含：
- 语言分布表
- 文件类型统计
- 目录结构概览
- Git 活跃度（如果是 git 仓库）
- 大文件排行

#### `/open-skills:commit [--simple]`

分析 Git 暂存更改并生成提交信息。

```
# 生成 Conventional Commits 格式（默认）
git add .
/open-skills:commit

# 简单模式
/open-skills:commit --simple
```

#### `/open-skills:goal <项目想法>`

把一个想法端到端推进到可发布状态，是 `project-orchestrator` skill 的手动入口。

```
# 直接给出想法即开跑（六阶段：需求→架构→开发→测试→审查→发布）
/open-skills:goal 做一个 CLI 工具，把 GitHub Issues 同步成本地 Markdown

# 无参数则提示你描述想法
/open-skills:goal

# 加 --auto 进入无人值守 cron 模式（每 15 分钟唤醒一次）
/open-skills:goal --auto
```

进度持久化在目标项目的 `.project-orchestrator/` 目录；已有进度时会询问继续 / 重做 / 放弃。

### 代理

`project-role-worker` 是项目交付流水线的兜底子代理：当编排器 `project-orchestrator` 找不到对应 `ecc:*` 专家时自动顶上，按角色完成需求/架构/开发/测试/审查/发布工作。

`translate-it-article` 是英文 IT 技术文章的中译子代理：说"翻译这篇/这段""translate this""帮我翻译这篇文章"时自动调度，译成通俗中文、保留 Markdown 格式并保存为本地文件。

### 技能

- `project-orchestrator`：端到端项目交付编排器。说"从零做一个项目并发布""端到端完成""接着上次项目继续""自动跑完"时自动激活，驱动子代理走完需求→架构→开发→测试→审查→发布，过程中持久化进度、可中断续跑。
- `commit-style`：讨论 Git 提交、commit message、提交规范时自动激活，提供 Conventional Commits 规范和中文提交指南。
- `claude-updater`：需要更新 Claude Code CLI、插件或查看新功能时自动激活。
- `session-resume`：说"继续上一次""接着上次做"时自动激活，读上次会话快照与 transcript，复述进度并从断点续跑。

### 钩子

`guard-secrets` 钩子会在每次写入或编辑文件时自动检查内容是否包含敏感信息（API 密钥、私钥、密码等），发现可疑内容时会提示你确认。

`session-snapshot` 与 `session-restore` 是一对会话恢复钩子：Claude 退出时自动把会话指针写到 `<项目根>/.session-resume/last-session.json`；下次启动新会话时检测到它，会读取上次 transcript、判断有没有未完成的任务，并用选择框问你「恢复上次任务 / 只看看进度 / 开始新任务」。你也可以随时直接说"继续上一次"来恢复。快照只存指针（不解析对话内容），真正的进度判断在恢复时由 Claude 完成。

## 项目结构

```
OpenSkills/
├── .claude-plugin/
│   └── plugin.json              # 插件清单（必需）
├── commands/                    # 斜杠命令
│   ├── stats.md                 #   /open-skills:stats
│   ├── commit.md                #   /open-skills:commit
│   └── goal.md                  #   /open-skills:goal（项目交付流水线入口）
├── agents/                      # 子代理定义
│   ├── project-role-worker.md   #   项目流水线兜底执行者
│   └── translate-it-article.md  #   英文 IT 文章中译
├── skills/                      # 自动激活技能（每个子目录一个 skill）
│   ├── commit-style/
│   │   └── SKILL.md             #   Git 提交规范
│   ├── project-orchestrator/
│   │   └── SKILL.md             #   端到端项目交付编排器
│   └── ...                      #   及 claude-updater / session-resume 等
├── hooks/                       # 事件钩子
│   ├── hooks.json               #   钩子配置
│   └── scripts/
│       ├── guard-secrets.sh     #   敏感信息检测脚本
│       ├── session-snapshot.sh  #   退出时写会话指针快照
│       └── session-restore.sh   #   启动时提示恢复上次任务
├── README.md                    # 本文件
├── CLAUDE.md                    # 项目开发说明
├── LICENSE                      # MIT 许可证
└── .gitignore
```

## 插件开发学习指南

如果你想基于此项目创建自己的插件，以下是每个组件的关键文件和概念：

### 1. 插件清单 (`plugin.json`)

**必需文件**，位于 `.claude-plugin/plugin.json`。最少只需 `name` 字段：

```json
{
  "name": "my-plugin"
}
```

### 2. 命令 (`commands/*.md`)

命令是用户通过 `/` 前缀手动调用的功能。格式为 YAML frontmatter + Markdown 指令：

```markdown
---
description: 命令描述（显示在命令列表中）
allowed-tools: Bash, Read
argument-hint: [参数说明]
---

命令的详细指令，`$ARGUMENTS` 会被替换为用户输入的参数。
```

### 3. 代理 (`agents/*.md`)

代理是可以被 Claude 自动或手动调用的子代理。定义角色、能力和行为：

```markdown
---
name: my-agent
description: 代理描述和能力说明
model: sonnet
---

代理的详细角色定义和工作指令。
```

### 4. 技能 (`skills/{name}/SKILL.md`)

技能是 Claude 根据上下文自动激活的知识库。`description` 字段是触发机制：

```markdown
---
name: my-skill
description: |
  技能描述。当用户提到 XXX、YYY 时自动激活。
  描述要"主动"一些，避免过少触发。
version: 1.0.0
---

技能的知识内容和指导说明。
```

### 5. 钩子 (`hooks/hooks.json`)

钩子是事件驱动的自动化处理程序：

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/my-script.sh",
        "timeout": 30
      }]
    }]
  }
}
```

可用事件：`PreToolUse`、`PostToolUse`、`Stop`、`SessionStart`、`SessionEnd`、`UserPromptSubmit`

### 关键概念

- **`${CLAUDE_PLUGIN_ROOT}`**：插件根目录的环境变量，用于路径引用
- **`allowed-tools`**：限制组件可以使用的工具，支持 glob 模式（如 `Bash(git:*)`）
- **`$ARGUMENTS`**：命令中用户输入的参数
- **自动发现**：Claude Code 自动扫描 `commands/`、`agents/`、`skills/` 目录

## 常见问题

### Q: 命令名称为什么是 `/open-skills:stats` 而不是 `/stats`？

插件中的命令会自动加上插件名作为前缀，避免不同插件之间的命名冲突。

### Q: 如何调试钩子？

钩子脚本通过 stdin 接收 JSON 格式的工具调用参数，通过 stdout 返回 JSON 响应。可以在脚本中添加日志输出到临时文件进行调试。

### Q: 技能什么时候会被激活？

Claude 根据技能的 `description` 字段判断是否激活。描述应包含触发场景和关键词。如果技能没有被触发，尝试在描述中添加更多触发短语。

### Q: 如何卸载插件？

```
/plugin uninstall open-skills
```

## 参考链接

- [Claude Code 插件官方文档](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT](LICENSE)

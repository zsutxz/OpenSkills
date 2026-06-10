# dev-toolkit — Claude Code 示例插件

> 一个完整的 Claude Code 插件示例，展示所有组件类型：命令（Commands）、代理（Agents）、技能（Skills）、钩子（Hooks）。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 功能一览

| 组件 | 命令/名称 | 功能说明 |
|------|-----------|----------|
| 📋 命令 | `/dev-toolkit:stats` | 分析代码库统计信息（语言分布、文件数、行数等） |
| 📋 命令 | `/dev-toolkit:commit` | 分析暂存更改，生成 Conventional Commits 格式的提交信息 |
| 🤖 代理 | `codebase-analyst` | 代码库分析专家，识别架构模式和技术债务 |
| 🧠 技能 | `commit-style` | Git 提交规范知识，讨论 commit 时自动激活 |
| 🛡️ 钩子 | `guard-secrets` | 写入文件前检测敏感信息（API 密钥、密码等） |

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
git clone https://github.com/zsutxz/OpenSkills.git ~/.claude/plugins/cache/dev-toolkit
```

然后在 `~/.claude/settings.json` 中启用：

```json
{
  "enabledPlugins": {
    "dev-toolkit": true
  }
}
```

## 使用指南

### 命令

#### `/dev-toolkit:stats [path]`

分析代码库统计信息。

```
# 分析当前目录
/dev-toolkit:stats

# 分析指定项目
/dev-toolkit:stats /path/to/project
```

输出包含：
- 语言分布表
- 文件类型统计
- 目录结构概览
- Git 活跃度（如果是 git 仓库）
- 大文件排行

#### `/dev-toolkit:commit [--simple]`

分析 Git 暂存更改并生成提交信息。

```
# 生成 Conventional Commits 格式（默认）
git add .
/dev-toolkit:commit

# 简单模式
/dev-toolkit:commit --simple
```

### 代理

`codebase-analyst` 是一个自动可用的子代理，当 Claude 判断需要深入分析代码库时会自动使用。你也可以在对话中要求：

```
请分析这个项目的架构
帮我评估一下技术债务
```

### 技能

`commit-style` 技能会在你讨论 Git 提交、commit message、提交规范时自动激活，提供 Conventional Commits 规范和中文提交指南。

### 钩子

`guard-secrets` 钩子会在每次写入或编辑文件时自动检查内容是否包含敏感信息（API 密钥、私钥、密码等），发现可疑内容时会提示你确认。

## 项目结构

```
OpenSkills/
├── .claude-plugin/
│   └── plugin.json              # 插件清单（必需）
├── commands/                    # 斜杠命令
│   ├── stats.md                 #   /dev-toolkit:stats
│   └── commit.md                #   /dev-toolkit:commit
├── agents/                      # 子代理定义
│   └── codebase-analyst.md      #   代码库分析专家
├── skills/                      # 自动激活技能
│   └── commit-style/
│       └── SKILL.md             #   Git 提交规范
├── hooks/                       # 事件钩子
│   ├── hooks.json               #   钩子配置
│   └── scripts/
│       └── guard-secrets.sh     #   敏感信息检测脚本
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

### Q: 命令名称为什么是 `/dev-toolkit:stats` 而不是 `/stats`？

插件中的命令会自动加上插件名作为前缀，避免不同插件之间的命名冲突。

### Q: 如何调试钩子？

钩子脚本通过 stdin 接收 JSON 格式的工具调用参数，通过 stdout 返回 JSON 响应。可以在脚本中添加日志输出到临时文件进行调试。

### Q: 技能什么时候会被激活？

Claude 根据技能的 `description` 字段判断是否激活。描述应包含触发场景和关键词。如果技能没有被触发，尝试在描述中添加更多触发短语。

### Q: 如何卸载插件？

```
/plugin uninstall dev-toolkit
```

## 参考链接

- [Claude Code 插件官方文档](https://docs.anthropic.com/en/docs/claude-code/plugins)
- [Claude Code GitHub](https://github.com/anthropics/claude-code)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT](LICENSE)

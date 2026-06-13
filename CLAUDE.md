# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

OpenSkills 是一个 **Claude Code 插件**，同时是一份个人技能合集与教学示例。它一仓两用，这是理解结构的关键：

- **插件**：`.claude-plugin/plugin.json` 定义，名为 `open-skills`。
- **自托管 Marketplace**：`.claude-plugin/marketplace.json` 中插件的 `source` 指向 `"./"`，即 marketplace 把仓库根目录直接作为插件来源。

因此**发布 = 推送到 GitHub**：已安装用户 `/plugin` 更新、新用户 `/plugin install zsutxz/OpenSkills` 即可拿到改动，无 registry、无构建产物、无版本发布步骤。

## 四类组件及其激活机制

仓库按目录约定暴露四种组件，Claude Code 自动发现，无需注册。修改时最重要的是区分它们的**激活方式**：

| 目录 | 组件 | 激活方式 |
|------|------|----------|
| `commands/*.md` | 斜杠命令 | 用户手动 `/open-skills:<name>` 调用，`$ARGUMENTS` 接收参数 |
| `agents/*.md` | 子代理 | 模型按 `description` 自动调度，或对话中显式点名 |
| `skills/<name>/SKILL.md` | 技能 | 模型按 `description` 自动激活的知识库 |
| `hooks/hooks.json` | 钩子 | 事件驱动，`matcher` 匹配工具名后触发脚本 |

**易错点：skill 不是命令。** 放在 `skills/` 下的内容靠 `description` 自动触发，无法用 `/skill-name` 手动调用；需要手动 `/` 调用、或需要接收用户输入参数的，应放进 `commands/`。命令名自动加插件前缀（`stats.md` → `/open-skills:stats`），由插件名决定，与文件内 H1 标题无关。

## 关键约定

- **统一用中文**写文档、提示词、界面文案和代码注释。
- **Hook 脚本只用纯 bash**，不依赖 Python，保证 Windows Git Bash 兼容；经 stdin 收 JSON、stdout 回 JSON，用 `${CLAUDE_PLUGIN_ROOT}` 引用插件根。
- **`allowed-tools`** 在 frontmatter 中限定组件可用工具，支持 glob（如 `Bash(git:*)`）。
- 每个组件既要开箱即用，也要作为学习参考——README 含完整的组件开发指南，新增组件时参考其格式与 frontmatter 约定。
- `guard-secrets` 钩子在 `Write|Edit` 前扫描内容，命中密钥 / 密码 / 私钥模式时返回 `decision: ask` 拦截确认；写入含示例密钥的测试内容会触发，属预期行为。

## 常用命令

```bash
# 本地加载整个插件测试
claude --plugin-dir .

# 会话内修改组件后重载
/reload-plugins

# 分发安装（发布即靠此）
/plugin install zsutxz/OpenSkills
```

无构建 / lint / 测试套件——"测试"就是加载插件并在会话中逐个验证组件行为。

## 已知待清理项

- `commands/stats.md`、`commands/commit.md` 的 H1 标题仍写作 `/dev-toolkit:*`（插件在 commit `1a89a91` 由 `dev-toolkit` 改名 `open-skills` 时未同步标题）。不影响功能，仅文档残留。

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

OpenSkills 是一个 **Claude Code 插件**，同时是一份个人技能合集与教学示例。它一仓两用，这是理解结构的关键：

- **插件**：`.claude-plugin/plugin.json` 定义，名为 `open-skills`。
- **自托管 Marketplace**：`.claude-plugin/marketplace.json` 中插件的 `source` 指向 `"./"`，即 marketplace 把仓库根目录直接作为插件来源。

因此**发布 = 推送到 GitHub**：已安装用户 `/plugin` 更新、新用户 `/plugin install zsutxz/OpenSkills` 即可拿到改动，无 registry、无构建产物、无版本发布步骤。

## 关键约定

- **统一用中文**写文档、提示词、界面文案和代码注释。
- **Hook 脚本只用纯 bash**，不依赖 Python，保证 Windows Git Bash 兼容；经 stdin 收 JSON、stdout 回 JSON，用 `${CLAUDE_PLUGIN_ROOT}` 引用插件根。
- **`allowed-tools`** 在 frontmatter 中限定组件可用工具，支持 glob（如 `Bash(git:*)`）。
- 每个组件既要开箱即用，也要作为学习参考——README 含完整的组件开发指南，新增组件时参考其格式与 frontmatter 约定。
- `guard-secrets` 钩子在 `Write|Edit` 前扫描内容，命中密钥 / 密码 / 私钥模式时返回 `decision: ask` 拦截确认；写入含示例密钥的测试内容会触发，属预期行为。
- 无构建 / lint / 测试套件——"测试"就是本地加载插件（`claude --plugin-dir .`）并在会话中逐个验证组件行为；改完组件用 `/reload-plugins` 重载。

## 已知待清理项

- `commands/stats.md`、`commands/commit.md` 的 H1 标题仍写作 `/dev-toolkit:*`（插件在 commit `1a89a91` 由 `dev-toolkit` 改名 `open-skills` 时未同步标题）。不影响功能，仅文档残留。

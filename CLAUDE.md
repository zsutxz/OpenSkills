# dev-toolkit 项目

这是一个 Claude Code 示例插件项目，目的是展示插件的所有组件类型，同时提供实用的开发工具。

## 项目结构

- `.claude-plugin/plugin.json` — 插件清单（必需）
- `commands/` — 斜杠命令（`/dev-toolkit:stats`、`/dev-toolkit:commit`）
- `agents/` — 子代理定义（`codebase-analyst`）
- `skills/` — 自动激活的技能知识（`commit-style`）
- `hooks/` — 事件处理器（`guard-secrets` 敏感信息守卫）

## 开发约定

- 使用中文编写文档、提示词和用户界面文案
- 代码注释使用中文
- Hook 脚本使用纯 bash（不依赖 Python，确保 Windows Git Bash 兼容）
- 所有文件使用 UTF-8 编码
- 所有组件都应可直接使用，同时也可作为学习参考

## 测试方法

```bash
# 本地测试插件
claude --plugin-dir .

# 重新加载插件（在 Claude Code 会话中）
/reload-plugins
```

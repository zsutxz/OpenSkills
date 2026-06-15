---
name: claude-updater
description: 统一管理 Claude Code 生态系统的所有组件更新，包括 CLI、插件市场、新功能检测等。当用户需要更新 Claude Code 相关组件、检查更新状态、了解新功能或查看更新报告时使用此 skill。
license: MIT
allowed-tools: [Bash, Read, Write, WebSearch]
metadata:
  version: "4.1.1"
  category: system
  tags: update,cli,plugin,maintenance,changelog
---

# Claude Code 更新器

## 使用时机

用户说："升级/更新 claude"、"检查更新"、"更新插件"、"有什么新功能"、"changelog"、"更新报告"、"设置自动检查"等。

## 意图路由

| 用户说 | 动作 |
|--------|------|
| 检查更新 | 获取状态 → 检测更新 → 汇报，不执行 |
| 更新全部 / 升级 claude | CLI → 市场 → 插件 → 新功能 → 报告 |
| 更新 CLI | 仅 `claude update` |
| 更新插件 | 市场刷新 → 逐个更新插件 |
| 新功能 / changelog | WebSearch 搜索最新 changelog |
| 设置自动检查 | CronCreate 定时任务 |

## 执行流程

### 1. 获取当前状态

```bash
claude --version        # CLI 版本
claude plugin list      # 插件列表
```

### 2. 执行更新

**CLI**（`update` 与 `upgrade` 为同一命令的别名）：
```bash
claude update
```

**插件市场刷新**（拉取各市场的最新源）：
```bash
claude plugin marketplace update        # 不带参数则刷新所有市场
```

**逐个更新插件**（用 `plugin list` 输出中的 `plugin@marketplace` 全名）：
```bash
claude plugin update <plugin>@<marketplace>             # 必须用全名
claude plugin update <plugin>@<marketplace> -s project  # 指定范围：user/project/local/managed
```

> ⚠️ `update` **必须用全名 `plugin@marketplace`**。虽然 `--help` 形式上显示 `<plugin>`，但裸名（如 `agent-sdk-dev`）会报 `Plugin not found`——同名插件可能存在于多个市场，需市场名消歧。`@marketplace` 语法对 `install` 和 `update` 都适用。

- 跳过 `disabled` / `failed` 状态的插件，不自动处理
- 单个插件失败不阻塞其余，记录失败项继续
- 更新需重启 Claude Code 后才生效（CLI 与插件均如此）

### 3. 新功能与技巧搜索

用户问"新功能"、"技巧"、"changelog"时触发。

**缓存位置**：`claude-updater-reports/tips/`

**类别与有效期**：

| 类别 | TTL | 文件 | 触发词 |
|------|-----|------|--------|
| new_features | 3天 | new_features.md | 新功能、更新、最新 |
| core_tips | 7天 | core_tips.md | 技巧、窍门 |
| best_practices | 14天 | best_practices.md | 最佳实践、建议 |
| shortcuts | 30天 | shortcuts.md | 快捷键、命令、别名 |

**判断缓存是否过期（交给 bash，不靠模型算日期差）**：

```bash
# 以 new_features（TTL=3天）为例：find 有输出即已过期
find claude-updater-reports/tips/new_features.md -mtime +3 2>/dev/null
```

逻辑：
1. 缓存文件**存在**且 `find -mtime +N` **无输出** → 未过期，直接返回文件内容
2. 缓存文件不存在，或已过期 → WebSearch 搜索 → 写入 `.md` → 更新 `index.json`

**搜索关键词**（缓存过期时）：
```
# new_features
"Claude Code" changelog release notes site:docs.anthropic.com
# core_tips
"Claude Code" tips tricks workflow productivity
# best_practices
"Claude Code" best practices agent development
# shortcuts
"Claude Code" keyboard shortcuts slash commands
```

**index.json 格式**（时间戳用 `date -Iseconds` 生成，不要手写）：
```bash
date -Iseconds    # 例如 2026-06-15T09:30:00+08:00
```
```json
{
  "categories": {
    "new_features": { "last_search": "2026-06-15T09:30:00+08:00", "count": 10 }
  }
}
```

### 4. 写入报告

保存到当前工作目录 `claude-updater-reports/`：

1. 归档旧报告：`latest.md` → `history/<时间戳>.md`（时间戳用 `date +%Y-%m-%d_%H%M%S` 生成）
2. 写入新 `latest.md`
3. 更新 `index.json`（记录 `last_check`、`last_update`、各组件版本，时间戳同样用 `date` 命令生成）

**时间戳生成（统一用 bash，不让模型脑补）**：
```bash
date +%Y-%m-%d_%H%M%S   # 归档文件名
date -Iseconds          # index.json / 报告内的 ISO 时间
```

**报告模板**：
```markdown
# Claude Code 生态更新报告

*生成时间：2026-06-15 09:30*

| 组件 | 更新前 | 更新后 | 状态 |
|------|--------|--------|------|
| Claude CLI | {old} | {new} | ✅/⏭️/❌ |
| {plugin} | {old} | {new} | ✅/⏭️/❌ |

## 详细日志
（关键命令输出）

## 注意事项
- 需重启的组件
- 失败组件的手动修复命令
```

## 自动检查

用户说"设置自动检查"时用 CronCreate：

```
CronCreate: {
  cron: "3 9 * * 1",
  prompt: "运行 claude-updater skill，检查并更新 Claude Code CLI 和所有插件，生成报告。",
  recurring: true,
  durable: true
}
```

语义说明：
- `durable: true`：写入 `.claude/scheduled_tasks.json`，**跨会话存活**（重启 Claude Code 后仍生效）
- `recurring: true`：每周一 09:03 触发，**7 天后自动过期**并执行最后一次
- 仅在 REPL 空闲时触发（会话进行中或非交互运行不执行）

## 注意事项

- `claude update` 比 `npm update -g` 更可靠，优先使用
- 网络错误时提示用户检查代理/VPN，提供手动命令
- 更新后提醒用户重启 Claude Code（CLI 与插件更新均需重启生效）
- 所有时间戳一律用 `date` 命令生成；确定性逻辑（过期判断、日期比较）交给 bash，不依赖模型估算
- Windows 上市场刷新偶发 `EBUSY: resource busy or locked`（市场目录重命名被占用），会级联导致同市场插件报 `Plugin not found`；重试通常自愈，残留 `.bak` 目录则需手动删除 `~/.claude/plugins/marketplaces/<name>` 后重试
- 更新报告中的"已是最新"仅在市场源可达时可信——若 github 不通，版本判定基于本地缓存，可能过期

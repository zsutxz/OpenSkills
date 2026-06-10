---
description: 分析暂存的更改并生成规范的 Git 提交信息
allowed-tools: Bash(git:*), Read
argument-hint: "[--simple]"
---

# /dev-toolkit:commit — 生成规范提交信息

分析当前的 Git 暂存更改，生成符合 Conventional Commits 规范的提交信息。

## 步骤

1. **检查暂存区**：运行 `git diff --cached --stat` 查看暂存文件概览。
   - 如果没有暂存更改，提示用户先 `git add`，并显示 `git status --short` 供参考。

2. **获取详细差异**：运行 `git diff --cached` 获取完整的代码差异。

3. **分析更改内容**，确定：
   - **更改类型**（type）：feat / fix / refactor / docs / style / test / chore / perf
   - **影响范围**（scope）：哪些模块或文件受到影响
   - **更改摘要**（subject）：用一句话描述核心变更

4. **生成提交信息**。

## 提交信息格式

### Conventional Commits 模式（默认）

```
<type>(<scope>): <subject>

<body>
```

**type 选择规则**：
- 新增功能或用户可见的行为变更 → `feat`
- 修复 bug → `fix`
- 代码重构，不改变行为 → `refactor`
- 文档变更 → `docs`
- 代码格式调整（空格、缩进等） → `style`
- 添加或修改测试 → `test`
- 构建工具、依赖、CI 等变更 → `chore`
- 性能优化 → `perf`

**scope 选择规则**：
- 取自受影响的主要模块/目录名
- 如果涉及多个模块，选择最重要的一个
- 可选，如果没有明确范围则省略

**subject 规则**：
- 不超过 72 个字符
- 使用祈使句（"添加"而非"添加了"）
- 不以句号结尾

### 简单模式（--simple）

如果 `$ARGUMENTS` 包含 `--simple`，直接用一句话描述更改，不使用 Conventional Commits 格式。

## 交互流程

1. 生成提交信息后，展示给用户
2. 询问用户是否需要修改
3. 用户确认后，执行 `git commit -m "<message>"`
4. 如果 body 为多行，使用 heredoc：
   ```bash
   git commit -m "type(scope): subject" -m "body line 1
   body line 2"
   ```

## 注意事项

- 不要自动执行 `git commit`，必须等用户确认
- 使用中文撰写 subject 和 body
- 如果暂存区为空，给出友好的提示而非报错

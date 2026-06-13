---
name: commit-style
description: |
  Git 提交信息规范和最佳实践。当用户进行 git commit、编写提交信息、
  讨论提交规范、code review 时自动激活。涵盖 Conventional Commits 规范、
  中文提交信息格式、以及团队协作中的提交最佳实践。
  即使用户没有明确说“commit message”，只要涉及版本控制、变更描述、
  代码提交等话题，都应考虑使用此 skill。
version: 1.0.0
---

# Git 提交信息规范

## Conventional Commits 格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

## Type 类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(auth): 添加 OAuth2 登录支持` |
| `fix` | 修复缺陷 | `fix(api): 修复分页参数越界问题` |
| `docs` | 文档更新 | `docs: 更新 API 使用说明` |
| `style` | 代码格式（不影响逻辑） | `style: 统一缩进为 2 空格` |
| `refactor` | 重构（不改变行为） | `refactor(utils): 提取公共验证函数` |
| `perf` | 性能优化 | `perf(render): 虚拟列表优化大数据渲染` |
| `test` | 测试 | `test(auth): 补充登录流程单元测试` |
| `chore` | 构建 / 工具 / 依赖 | `chore: 升级 webpack 到 v5` |
| `ci` | CI/CD 配置 | `ci: 添加 GitHub Actions 自动部署` |
| `build` | 构建系统 | `build: 配置 Vite 打包优化` |

## Scope 范围（可选）

表示影响的模块，常见取法：

- **按模块名**：`auth`、`api`、`ui`、`db`、`core`
- **按功能域**：`payment`、`notification`、`search`
- **按层级**：`frontend`、`backend`、`shared`

## Subject 主题行

- 不超过 72 个字符
- 使用祈使句（“添加”而非“添加了”）
- 不以句号结尾
- 描述“做了什么”，而非“为什么”

## Body 正文（可选）

- 解释“为什么”做这个更改
- 可多行，与 subject 之间空一行

## Footer 脚注（可选）

- Breaking Changes：`BREAKING CHANGE: <描述>`
- 关联 Issue：`Closes #123`
- 关联 PR：`Refs #456`

## 好的示例

```
feat(pay): 添加微信支付回调处理

实现微信支付结果通知的接收和验证，
包括签名校验、订单状态更新和幂等处理。

Closes #234
```

```
fix(db): 修复连接池泄漏问题

高并发下异常路径未归还连接，导致连接数持续增长最终耗尽。
添加 try-finally 确保连接始终被释放。

Refs #189
```

## 不好的示例

```
update stuff          # 太模糊，没说改了什么
fix bug               # 什么 bug？怎么修的？
WIP                   # 不要提交半成品
```

## 中文提交信息指南

- subject 可用中文，保持简洁
- 用“添加”、“修复”、“更新”、“移除”、“重构”等动词开头
- body 可中英混排（技术术语保留英文）
- 避免同一词组中英混杂（如不要写“fix 了 bug”）

## 最佳实践

1. **原子提交**：每次提交只做一件事，便于 revert 和 code review
2. **小步前进**：每个逻辑单元一次提交
3. **提交前自查**：不含敏感信息、调试代码、临时文件；不提交 `dist/`、`node_modules/`、`.pyc` 等生成物
4. **醒目标注破坏性变更**：用 `BREAKING CHANGE:` 标记
5. **关联上下文**：在 footer 引用相关 issue 和 PR

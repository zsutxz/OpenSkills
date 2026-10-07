# Verified Claude Code & Codex Tip Sources

当日报流程里的搜索结果不可验证时，优先回退到这些已核验来源：

## 官方来源：Anthropic Engineering Blog

URL: `https://www.anthropic.com/engineering`

### 提取文章标题和日期

```bash
curl -sf -o /tmp/anthropic_blog.html https://www.anthropic.com/engineering
python3 -c "
import re
with open('/tmp/anthropic_blog.html') as f:
    content = f.read()
articles = re.findall(r'<h[1-3][^>]*>([^<]+)</h[1-3]><div[^>]*class=[^>]*date[^>]*>([^<]+)</div>', content)
for title, date in articles:
    print(f'{title.strip()} --- {date.strip()}')
"
```

### 备选：从页面属性里提取标题

```bash
python3 -c "
import re
with open('/tmp/anthropic_blog.html') as f:
    content = f.read()
titles = re.findall(r'alt=([^ ]+)', content)
for t in titles:
    if any(w in t.lower() for w in ['claude', 'agent', 'code', 'eval', 'harness', 'mcp']):
        print(t.strip())
"
```

## 官方来源：Claude Code GitHub Releases

当博客不可用时，直接从 GitHub Releases API 提取已验证的功能。

| Release | Date | Verified Features |
|---------|------|-------------------|
| v2.1.177 | Jun 13 | 无 release notes（hotfix，仅有 SHA 签名及二进制文件） |
| v2.1.176 | Jun 12 | 会话标题自动跟随对话语言；页脚自定义链接；凭证缓存改进；Remote Control 修复 |
| v2.1.175 | Jun 12 | 管理设置支持强制模型白名单 |
| v2.1.174 | Jun 11 | 滚动加速设置；`/model` 选择器修复；用量归因面板；背景会话环境变量修复 |
| v2.1.178 | Jun 15 | 权限规则参数匹配；嵌套 skills 目录；自动模式子代理评估；`/bug` 描述必填；多项 Remote Control 修复 |

### 提取方法

```bash
curl -sf -o /tmp/claude_releases.json 'https://api.github.com/repos/anthropics/claude-code/releases?per_page=5'
grep -oP '"tag_name":"[^"]*"' /tmp/claude_releases.json
```

## 可靠性说明

- GitHub Releases API 最可靠，优先级最高
- Anthropic Engineering Blog 偶尔会因前端渲染或网络环境返回空内容
- 外部搜索结果必须可核验，不能直接写入日报

## 已用过的技巧

下面这些技巧已经在过去几天的日报里用过了，避免重复：

1. 自愈编辑模式
2. 补丁预览边对边对比
3. 带约束的跨文件重构
4. 自定义指令配置文件
5. 自动提交信息生成
6. 多文件并行编辑
7. --plan 分步执行
8. .claudeignore 排除规则
9. /fix 与 /review 斜杠命令
10. 深度调查模式
11. Shell 命令实时预览
12. 跨文件编辑差异视图
13. /explain 命令集成调用栈
14. 自定义 Lint 规则
15. Claude Code 自动模式
16. Agent 技能扩展系统
17. 托管 Agent 架构
18. 跨产品容器化安全
19. Claude Code 质量报告更新
20. 长运行应用 Harness 设计
21. footerLinksRegexes 页脚定制
22. enforceAvailableModels 模型白名单
23. VSCode 用量归因面板
24. wheelScrollAcceleration 设置
25. 权限规则参数匹配
26. 嵌套技能目录加载
27. 自动模式子代理安全升级
28. /bug 命令增强
29. /skill-doctor 技能体检命令
30. bashOutputMaxChars 与 taskOutputMaxChars 输出上限设置
31. --append-subagent-system-prompt-file 子代理提示词文件
32. /diff 全屏差异面板
33. /cost 缓存未命中归因

34. managedMcpServers 托管 MCP 设置
35. --permission-prompts none 无人值守开关
36. glab 命令识别（GitLab MR 徽章）
37. claude plugin validate --json
38. Claude Fable 5.1 默认模型
39. timeFormat 与 timeZone 设置
40. Codex Vim 撤销重做
41. Codex 插件 CLI 远程市场
42. Codex tui.auto_recap 开关
43. /reload-plugins 进入 headless 会话
44. /advisor 文本形态
45. Organization policy 状态行
46. CLAUDE_CODE_SUBAGENT_MODEL_FORCE
47. /effort s 会话级推理强度
48. Codex TUI 历史完整回放
49. Codex 用量窗口提前预警
50. GPT-6-Astra 经 API 配置

51. maxEffortLevel 效力等级封顶设置
52. --system-prompt-snapshot off 系统提示即时渲染
53. --plugin-dir 指向插件文件夹多插件加载
54. Codex --worktree 实验性隔离检出
55. Codex 内联问答（工作中旁路提问）
56. Codex Windows 后台共享守护服务器

57. gateway.yaml pricing 计费对齐（/cost 与遥测和消费计量一致）
58. CLAUDE_CODE_WEBFETCH_DEADLINE_MS WebFetch 挂死超时
59. claude self-hosted-runner --remove-session-state 会话目录清理
60. claude plugin 子命令 --json 化（install/uninstall/update/enable/disable/list）
61. PermissionRequest 钩子 -p 模式修复与 policy 警告 headless 打印
62. Codex Python SDK max/ultra 推理等级
63. Codex Python SDK ExternalMessage 外部消息注入

64. claude plugin eval 插件评测套件（JSON + HTML 报告）
65. /output-style 输出样式切换（含 headless / Remote Control）
66. CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS 工作流并发代理上限（1-256）
67. bashEditDiffEnabled Bash 编辑改动 diff 回显
68. /focus 聚焦视图（提示词 + 一行摘要 + 回复）
69. 提示缓存自动续写修复与 CLAUDE_CODE_BG_TASKS_REPORT_RUNNING 后台任务运行状态

70. 只读 git 命令长会话权限回归修复（v2.1.270，269 引入的回归）
71. OTEL_METRICS_INCLUDE_REPOSITORY 仓库属性遥测（配合 OTEL_LOG_TOOL_DETAILS）
72. CLAUDE_CODE_GATEWAY_MODEL_DISCOVERY_TIMEOUT_MS 网关模型发现超时
73. kitty/st/rxvt-unicode/WezTerm 终端按键回归修复
74. 上下文压缩后 git status 实时化（不再是会话开始时的旧快照）
75. claude.ai 技能与插件同步到终端（syncClaudeAiSkills / syncClaudeAiPlugins 退出，v2.1.275）
76. /plugin install --marketplace 安装时顺带添加市场（v2.1.275）
77. Ctrl+Enter / Ctrl+X Ctrl+S 立即发送排队消息（v2.1.275）
78. 插件与市场消息不再泄露 URL 中的密码 token（v2.1.275 安全修复）
79. Codex /voice 实验性语音对话（rust-v0.155.0）
80. Codex Touch ID 验证 MCP 请求（macOS，0.155.0）
81. Codex TUI 状态行实时推理摘要与回合完成时间戳（0.155.0）
82. AGENTS.md 支持：项目无 CLAUDE.md 时改读 AGENTS.md（v2.1.277）
83. ANTHROPIC_BASE_URL 指向代理/网关时 400 advisor_20260301 修复（v2.1.276，275 回归）
84. claude -p / Agent SDK 内部错误后报错并退出码 1，不再挂死（v2.1.277）
85. CLAUDE_GATEWAY_PROXY_IS_EGRESS_BOUNDARY 出站边界代理模式 + upstream headers 静态头（v2.1.277）
86. 插件重装不再破坏正在被使用的已装版本（v2.1.277）
87. Grep/Glob 系统资源耗尽时显性报错；Write 目标为目录时报错（v2.1.277）
88. /clear 后恢复会话丢首条消息致 prompt 缓存全失效的修复（v2.1.277）
89. Codex 新建本地 TUI 会话默认关闭推理摘要，兼容不支持的提供商（rust-v0.155.1）

90. attribution: false 关闭提交/PR 署名（v2.1.281，9-24 日报）
91. MCP elicitation 浏览器引导授权（v2.1.281，9-24 日报）
92. claude plugin validate 新增 MCP 检查（v2.1.281，9-24 日报）
93. /insights 量化 auto mode 收益建议（v2.1.281，9-24 日报）
94. Codex 0.156.1 模型选择器加入 GPT-6 Sol/Luna（9-24 日报）

95. /doctor prompt-audit 提示词体检（v2.1.283，9-26 日报）
96. availableModelsMatch "exact" + deniedModels 模型治理（v2.1.283，9-26 日报）
97. CLAUDE_CODE_GATEWAY_HINT_HEADERS 网关提示头 + OTEL_LOG_TOOL_CONTENT 扩展（v2.1.283，9-26 日报）
98. 动态工作流模型回退修复（v2.1.283，9-26 日报）
99. maxProseWidth 正文限宽（v2.1.282，9-26 日报）
100. 会话恢复/扩展思考丢失批量修复（v2.1.282，9-26 日报）
101. Codex 0.157.0 转正：GPT-6 Sol/Luna 进稳定版、f 键 fork 对话、全屏转录默认（9-26 日报）

102. Claude Sonnet 5.5 上架终端：claude-sonnet-5-5 默认 Sonnet、1M 上下文（v2.1.284，9-29 日报）
103. 自动模式「本次允许，下次再问」读权限选项（v2.1.284，9-29 日报）
104. 网关消费限额美元金额与 spend_limit used_usd/limit_usd/period（v2.1.284，9-29 日报）
105. /mcp reconnect all 一键重连全部失败 MCP 服务器（v2.1.284，9-29 日报）
106. 「提示词过长」二次压缩修复 + 恢复会话 MCP 等待 10 秒（v2.1.284，9-29 日报）
107. Codex 0.158.0 转正：TUI 选中即复制/右键粘贴保 Markdown、--oauth-client-secret、透明背景图像生成、Windows 10 沙箱修复（9-29 日报）

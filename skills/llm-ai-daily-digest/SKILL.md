---
name: llm-ai-daily-digest
description: 每日 LLM / AI Agent 情报速报。抓取 arXiv 最新 LLM / AI Agent 论文与微博上热门的 LLM / AI Agent 技术文章，整理成日报并归档到仓库。当用户说「今天的 AI 日报」「LLM 论文速报」或定时任务触发本 skill 时使用。
---

# LLM / AI Agent 每日速报

## 触发方式
每天 08:00 由 Windows 任务计划程序触发（任务名 `LLM-AI-Daily-Digest`，启动脚本 `~/.claude/skills/llm-ai-daily-digest/run-digest.cmd`，以无头 `claude -p` 拉起本 skill，日志写入 `E:\AI\LLMWiki-Repo\agent-workspace\digest-run.log`——排障先看日志）；也支持用户随时说「今天的 AI 日报」手动触发。本 skill 本身不负责定时，只负责被触发后执行抓取、整理与归档。

> ⚠️ 修改 `run-digest.cmd` 时必须保持 **纯 ASCII + CRLF 行尾**（中文注释/UTF-8 会在 GBK 代码页下解析碎裂）；改完可 `sed -i 's/$/\r/'` 转换。

## 执行步骤

### 1. 论文（arXiv API）
- 请求：`https://export.arxiv.org/api/query?search_query=%28abs:%22large+language+model%22+OR+abs:%22LLM%22+OR+abs:%22AI+agent%22+OR+abs:%22agents%22%29+AND+%28cat:cs.CL+OR+cat:cs.AI+OR+cat:cs.LG%29&sortBy=submittedDate&sortOrder=descending&max_results=20`——类目过滤排除机器人/生医等非 LLM 的 agents 论文；仍混入的不收录，日报尾注明「未收录」
- 解析 Atom XML 用 **Python 脚本文件**（`xml.etree.ElementTree`，ns=`http://www.w3.org/2005/Atom`），不要 `python -c` 内联单行——Windows bash 下引号/反斜杠转义易碎
- 解析字段：title、summary、authors、published、link；按 `published` 计算 age，只保留最近 24 小时提交的文章
- 作者列表取全量再截断展示；只显示前 3 人时注明「等 N 人」，避免被误当完整作者名单
- **⭐ 判定标准**：与自研 agent 框架方向直接同题者优先——模型路由/多模型调度、技能习得与跨任务迁移、记忆机制、上下文压缩、harness/Agent 架构范式；纯领域应用与常规 benchmark 默认不标

### 2. 微博热门
- 尝试非官方热搜接口：`https://weibo.com/ajax/side/hotSearch`（带浏览器 UA）
- 2026-08 实测返回 `{"error":"Forbidden"}`（已要求登录态）；环境变量 `WEIBO_COOKIE` 已设置时以 `-H "Cookie: $WEIBO_COOKIE"` 重试，未设置则按未获取到处理
- 筛选与 LLM / 大模型 / GPT / AI Agent / 智能体 相关的热词，记录排名与链接
- 从筛出的 LLM 相关热文/头条文章中挑选有技术价值的，下载保存到 `E:\AI\LLMWiki-Repo\raw\sources\llms\article\`，命名 `YYYY-MM-DD_<标题slug>.md`（正文转 Markdown，文首附原文链接与作者）
- 失效时标注「未获取到」并注明具体原因（如 Forbidden），不猜测内容，也不用其他来源的内容冒充微博文章

### 3. 整理输出
- **幂等**：写入前检查当日日报文件是否已存在；已存在则不覆盖，报告后跳过（用户明确要求重新生成时除外）
- 写入 `E:\AI\LLMWiki-Repo\raw\sources\llms\YYYY-MM-DD-llm-agent-digest.md`（当周日报留在 llms 根目录）
- 每次运行时顺带做轮转：**按文件名日期前缀 `YYYY-MM-DD` 判定「超过一周」**（不看文件 mtime），旧日报移入 `E:\AI\LLMWiki-Repo\raw\sources\llms\daily\`（`mkdir -p` 后 `mv`）
- 结构：`## 今日论文`、`## 微博热门`，每条含标题、来源链接、一句话说明；另可选：WebSearch 检索当日 LLM/Agent 社区讨论，以「## 社区与技术媒体」小节收录 3–6 条真实链接
- 「社区与技术媒体」小节的文章可按需下载到 `E:\AI\LLMWiki-Repo\raw\sources\llms\article\`：web_reader 抓取转 Markdown，命名 `YYYY-MM-DD_<标题slug>.md`（日期用原文发布日，未知则用抓取日），文首附来源链接/作者/抓取日期；**同名文件已存在则跳过，不重复抓取覆盖**
- 抓取被登录墙/反爬截断的（如知乎）：保存已得部分，文首如实标注「仅开头，截断原因」，不编造缺失内容
- 推广软文（如聚合服务导流文）：全文保留，但文首标注商业立场提醒
- 原则：抓不到就写「未获取到」，绝不编造论文、链接或观点

### 4. 下载论文 PDF
- **幂等**：目标 PDF 或其 `_abstract_zh.md` 已存在则跳过，不重复下载/重译
- 下载用户点名或标 ⭐ 的亮点论文原文：`curl -sL --max-time 60 -o "<绝对路径>.pdf" https://arxiv.org/pdf/<arxiv_id>`——`-o` 一律写绝对路径；后台并行 `&` 不会继承前面的 `cd`，相对路径会落错目录
- 保存到 `E:\AI\LLMWiki-Repo\raw\sources\llms\papers\`，命名 `Author{Year}_Title_Slug.pdf`
- 下载后校验文件头为 `%PDF`；失败如实报告，不得伪造
- **下载成功后随即翻译摘要并保存**：摘要原文即步骤 1 arXiv API 的 summary 字段，主流程直接翻译（无需子代理），存为同目录 `<同名>_abstract_zh.md`——文首英文原题 + 作者（全量）+ arXiv 链接，正文为摘要中译

### 5. 归档到 wiki（可选）
- 值得长期追踪的论文按 wiki 规范创建 `wiki/sources/<author>-<year>-<slug>.md`（frontmatter：authors/year/url/venue），并在 `wiki/index.md` 登记
- 存储布局：论文 PDF → `E:\AI\LLMWiki-Repo\raw\sources\llms\papers\`；微博精选文章与社区/技术媒体文章 → `llms\article\`；当周日报 → `llms\` 根目录；超一周旧日报 → `llms\daily\`

### 6. 论文全文翻译（仅在用户点名时启动）
- **触发条件：仅当用户明确说「翻译某篇论文」时才启动**；抓取、下载、存储（含摘要翻译）后一律不自动翻译全文
- 摘要已在下载时译好（步骤 4 的 `_abstract_zh.md`），点名翻译时从正文开始、全文交付
- 用 `open-skills:translate-it-article` 子代理（Agent 工具，后台运行）翻译为中文
- 原文获取优先级（2026-08 实测）：`https://arxiv.org/html/<arxiv_id>v1`（web_reader 可抓全文含附录）＞ 本地 PDF（Read 需 poppler，缺失则渲染失败）＞ ar5iv（仅重定向摘要页，无用）；WebFetch 对 arxiv.org 域可能被安全校验拦截
- 输出与 PDF 同目录同名：`<Author{Year}_Title_Slug>_zh.md`；保留章节层级与 LaTeX 公式（`$...$`），术语首现括注英文
- 表格数值、图内数据、抓取缺失的附录小节：显式标注「未能获取，参见原文 PDF」，绝不编造

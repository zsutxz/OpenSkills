# ============================================================
# Everyday News 每日定时任务包装脚本（无人值守 headless）
# 由 Windows 任务计划程序每天 08:40 触发
# 日志：docs\everyday-news\runs\last-run.log
# ============================================================
$ErrorActionPreference = 'Continue'
# 让 PowerShell 按 UTF-8 解析原生命令(claude.cmd)的中文输出，避免日志乱码
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Set-Location 'E:\AI\OpenSkills'

$runDir = 'docs\everyday-news\runs'
New-Item -ItemType Directory -Force -Path $runDir | Out-Null
$log = Join-Path $runDir 'last-run.log'
"=== run start ===" | Out-File -FilePath $log -Encoding utf8

$prompt = @"
每日新闻早报。这是无人值守的定时任务(headless)，禁止停下来询问用户、禁止等待选择，必须一路执行到底，最终写出完整中文日报。

请激活 everyday-news 技能，按 skills/everyday-news/SKILL.md 流程，但遵循以下无人值守规则：

1) 运行 python3 skills/everyday-news/scripts/fetch_news.py 抓取 RSS 原始数据(在当前工作目录运行，不要 cd)。
2) 读取 docs/everyday-news/今日日期.json。
3) Claude Code 与 Codex 技巧栏：先尝试 WebSearch；若 WebSearch 在本环境不可用(报错或被拦)，改用 curl 直接拉官方来源(例如 https://api.github.com/repos/anthropics/claude-code/releases 的 release notes)；若联网工具整体不可用，则该栏只写一行"今日因网络受限未更新"，绝不编造任何技巧。
4) GitHub 栏：务必实际执行 curl 请求 GitHub API 核验仓库名/stars/语言/描述(python 联网已验证可用，curl 同样可用，请实际尝试，不要因 WebSearch 失败就预判 curl 也会失败)。取 stars 高、描述清晰的仓库。
5) 翻译与排版(必须完成)：把所有英文标题统一翻译成简体中文，按栏目输出：财经/政治/世界杯/科技AI/Claude Code 与 Codex，每栏目 5 条，不显示任何 URL，与前 3 天去重。
6) 最终中文日报覆盖写入 docs/everyday-news/今日日期.md(覆盖第1步产生的英文原始版)。

当前工作目录是 E:\AI\OpenSkills。再次强调：不要问用户、不要等待，直接产出并保存中文日报。
"@

& 'C:\Users\skype\AppData\Roaming\npm\claude.cmd' -p $prompt --dangerously-skip-permissions --verbose *>&1 |
    Out-File -FilePath $log -Encoding utf8 -Append

Add-Content -Path $log -Value "`n=== run end, claude exit=$LASTEXITCODE ==="

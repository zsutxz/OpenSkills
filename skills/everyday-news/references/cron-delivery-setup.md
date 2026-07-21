# everyday-news Cron Delivery Setup

Created: 2026-05-27 (updated 2026-06-06)
Skill: everyday-news (v2.3.0)

## Job Configuration

```
job_id:    a452fd7f2511
name:      每日新闻早报
schedule:  30 8 * * * (每天 8:30)
deliver:   local (推送 + 存文件)
```

## Execution Flow (5 steps)

1. **Run fetch_news.py** — Python subprocess via PowerShell WebClient fetches:
   - RSS feeds (CNBC, MarketWatch, NPR, ESPN/SkySports, TechCrunch, Ars, The Verge)
   - GitHub search API: 多 query (claude-code, codex, ai-coding-agent, ai-agent-framework, cursor, llm-agent) + 近期活跃(`pushed:>=`)窗口，跨最近 7 天历史去重 → 独立「🐙 GitHub 热门」栏目 5 条
   - Round-robin merge (1 from each source, cycle until 5 reached)
   - 体育栏目：世界杯核心词优先，不足 5 条用同源其他体育新闻补足
   - 科技/AI = 5 RSS (round-robin across TechCrunch/Ars/The Verge)，纯 RSS 不再混 GitHub
   - Saves raw English data to JSON + MD

2. **Deduplicate news** — read last 3 days' .md, extract Chinese title first 30 chars, skip similar

3. **Search Claude Code & Codex tips** — use web search for fresh tips (not from RSS)
   - Also deduplicate: read last 3 days' tips, skip already-pushed ones
   - This ensures tips change daily

4. **Translate & format** — Chinese translation, clean output, NO URLs shown anywhere

5. **Save** — write final Chinese version to `doc/YYYY-MM-DD.md`

## Output Structure

| Section | Items | Source strategy |
|---------|-------|----------------|
| 💰 财经 | 5 | Round-robin CNBC ↔ MarketWatch |
| 🏛️ 政治 | 5 | NPR ↔ CNN (round-robin) |
| ⚽ 体育 | 5 | 世界杯核心词优先，不足用同源其他体育新闻补足 |
| 💻 科技/AI | 5 | 3 RSS round-robin (TechCrunch/Ars/The Verge)，纯 RSS |
| 🐙 GitHub 热门 | 5 | 多 query + 近期活跃窗口，跨 7 天去重，stars 降序 |
| 🔧 Claude Code & Codex | 3-5 | Web search, dedup'd daily |

## Core Rules

- **No URLs** — never display any link, just title + source name
- **Chinese only** — translate titles (20-30 chars), no English original
- **No decorative lines** — no borders, separators, or extra emoji beyond section icons
- **Source diversity** — round-robin across sources, never 5 from one source
- **Fresh tips daily** — Claude Code/Codex dedup'd against previous 3 days

## Data Pipeline

```
PowerShell WebClient
     ↓ RSS / GitHub API
fetch_news.py (Python subprocess)
     ↓ .json + .md
Agent reads JSON → translates → deduplicates → web search tips → formats → saves
     ↓
doc/YYYY-MM-DD.md
```

## Key Techniques

### PowerShell WebClient (WSL network bypass)

WSL's proxy can block most external HTTP(S) from curl/Python urllib. Solution: call PowerShell's native System.Net.WebClient which uses Windows' own networking stack.
Works for: RSS feeds (text XML), GitHub API (JSON), any public HTTP(S) endpoint.

### GitHub API from WSL

Same PowerShell approach, parse JSON response with `json.loads()`.
Rate limit: 60 unauthenticated requests/hour. Fine for daily cron (~3-6 requests/run).

### Round-robin source merge

`merge_and_limit()` in fetch_news.py cycles through sources 1-at-a-time,
not filling one source before starting the next. Ensures source diversity.

## Files

- `scripts/fetch_news.py` — main engine (RSS + GitHub + round-robin + JSON/MD output)
- `doc/YYYY-MM-DD.md` — daily Chinese report
- `doc/YYYY-MM-DD.json` — structured raw data

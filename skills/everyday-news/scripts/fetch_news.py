#!/usr/bin/env python3
"""Fetch daily news via PowerShell, save structured data.
Chinese translation done by agent on delivery.

Usage:
    python3 ~/.hermes/skills/everyday-news/scripts/fetch_news.py

Output:
    - ./docs/everyday-news/YYYY-MM-DD.md  (English raw)
    - ./docs/everyday-news/YYYY-MM-DD.json (structured data)
"""
import subprocess, html, re, datetime, os, json, urllib.request, sys, base64

# Windows 控制台默认 GBK，print 含 emoji 的汇总会抛 UnicodeEncodeError，强制 utf-8 输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 所有产物统一写入运行时当前目录的 docs/everyday-news/（SKILL.md 以绝对路径调用本脚本、不 cd，保证 getcwd 为用户目录）
NEWS_DIR = os.path.join(os.getcwd(), "docs", "everyday-news")
os.makedirs(NEWS_DIR, exist_ok=True)

SOURCES = {
    "💰 财经": [
        ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
        ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories"),
    ],
    "🏛️ 政治": [
        ("NPR Politics", "https://feeds.npr.org/1014/rss.xml"),
        ("CNN Politics", "http://rss.cnn.com/rss/cnn_topstories.rss"),
    ],
    "⚽ 体育": [
        ("ESPN", "https://www.espn.com/espn/rss/news"),
        ("Sky Sports", "https://www.skysports.com/rss/12040"),
    ],
    "💻 科技/AI": [
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
        ("Ars Technica AI", "https://arstechnica.com/tag/ai/feed/"),
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ],
}

# GitHub 热门：聚焦 AI 编程工具，多 query 扩大候选池；配 collect_github_repos 的
# 跨天去重（最近 7 天）+ 近期活跃(pushed:>=)时间窗口，让每天看到的仓库滚动变化
GITHUB_SEARCH_QUERIES = [
    "claude-code", "codex", "ai-coding-agent",
    "ai-agent-framework", "cursor", "llm-agent",
]

# 跨天去重窗口：今天不会再推最近 N 天已出现过的 GitHub 仓库
GITHUB_HISTORY_DAYS = 7

# 世界杯核心关键词（收紧：去掉过宽的 soccer/football/friendly/ronaldo/ney，
# 否则淡季也会把所有足球新闻都判成"世界杯"，无法触发用其他体育新闻补足）
WORLD_CUP_KEYWORDS = [
    "world cup", "worldcup", "fifa", "2026 world cup", "wc 2026", "qualif",
    "梅西", "姆巴佩", "世界杯", "淘汰赛",
    "messi", "mbappe", "copa", "concacaf", "conmebol", "uefa nations",
]


def _decode_bytes(b):
    """UTF-8 优先，失败回退 cp1252（Latin-1 超集，每个字节都有映射，不丢字符）。
    修复旧版无条件 UTF8.GetString 把非 UTF-8 的 RSS（含 '"'é 等）解码成 ?? 的乱码。"""
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("cp1252")


def fetch_powershell(url):
    """Fetch via PowerShell WebClient (bypasses WSL network restrictions).
    PowerShell 端只 Base64 回传原始字节，编码判定交给 Python _decode_bytes，
    避免在 PowerShell 里硬编码 UTF8.GetString 导致非 UTF-8 源乱码。"""
    escaped = url.replace("'", "''")
    ps = f"""
$wc = New-Object System.Net.WebClient;
$wc.Headers.Add("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
try {{$b=$wc.DownloadData('{escaped}');Write-Output ([Convert]::ToBase64String($b))}}
catch {{Write-Output "__FAIL__"}}"""
    try:
        r = subprocess.run(["powershell.exe","-NoProfile","-Command",ps],
            capture_output=True, text=True, timeout=20, encoding='utf-8', errors='replace')
        out = r.stdout.strip()
        if out == "__FAIL__" or not out:
            return None
        return _decode_bytes(base64.b64decode(out))
    except Exception:
        return None


def fetch_github_trending(query, label, per_page=5):
    """Search GitHub for trending repos via PowerShell."""
    encoded = urllib.parse.quote(query)
    url = f"https://api.github.com/search/repositories?q={encoded}&sort=stars&order=desc&per_page={per_page}"
    data = fetch_powershell(url)
    if not data:
        return []
    try:
        parsed = json.loads(data)
        items = parsed.get("items", [])
        results = []
        for item in items:
            results.append({
                "name": item["full_name"],
                "url": item["html_url"],
                "stars": item["stargazers_count"],
                "lang": item.get("language") or "",
                "desc": item.get("description") or "",
                "query_label": label,
            })
        return results
    except (json.JSONDecodeError, KeyError):
        return []


def load_recent_github_seen(news_dir, today, days=GITHUB_HISTORY_DAYS):
    """读最近 days 天历史 JSON，收集已推过的 GitHub 仓库 full_name（小写）。

    跨天去重的依据：今天不再推最近 N 天已出现过的仓库，从而让 GitHub 栏目每天换新。
    历史不足 N 天时只读已有的文件，不报错。
    """
    seen = set()
    for i in range(1, days + 1):
        d = today - datetime.timedelta(days=i)
        path = os.path.join(news_dir, f"{d.strftime('%Y-%m-%d')}.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        for items in data.get("results", {}).values():
            for item in items:
                if isinstance(item, dict) and item.get("is_github"):
                    seen.add((item.get("title") or "").lower())
    return seen


def collect_github_repos(today, seen, limit=5):
    """收集 GitHub 热门仓库，跨天去重后取 stars 最高的 limit 条。

    候选滚动：query 拼上 `pushed:>=近期` 时间窗口，让候选是"近 30 天仍活跃"的仓库，
    随日期滚动；叠加跨天去重，使每天看到的 repo 不同。

    兜底（保证栏目永不为空）：去重后不足 limit 时，按"去时间窗口但仍去重 → 放开去重"
    两级回退，逐级放宽直到取满 limit。
    """
    cutoff = (today - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    passes = [
        (f" pushed:>={cutoff}", True),  # 近期活跃 + 去重
        ("", True),                      # 全量 + 去重
        ("", False),                     # 全量 + 允许重复（最后兜底）
    ]
    collected = []
    local_seen = set(seen)  # 历史已推 + 本次已收
    for qualifier, dedup in passes:
        if len(collected) >= limit:
            break
        for query in GITHUB_SEARCH_QUERIES:
            if len(collected) >= limit:
                break
            repos = fetch_github_trending(query + qualifier, "GitHub", per_page=15)
            for r in repos:
                key = r["name"].lower()
                if dedup and key in local_seen:
                    continue
                local_seen.add(key)
                collected.append(r)
                if len(collected) >= limit:
                    break
    collected.sort(key=lambda r: r["stars"], reverse=True)
    return collected[:limit]


def parse_feed(xml, max_items=10):
    """Extract (title, link) pairs from RSS 2.0 or Atom XML."""
    if not xml:
        return []
    items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
    results = []
    if items:
        for item in items:
            title_m = re.search(r'<title(?:[^>]*)>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</title>', item, re.DOTALL)
            link_m = re.search(r'<link>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</link>', item, re.DOTALL)
            if not link_m:
                link_m = re.search(r'<guid[^>]*>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</guid>', item, re.DOTALL)
            if title_m:
                title = html.unescape(title_m.group(1).strip().replace("\n"," ").replace("\r",""))
                while "  " in title: title = title.replace("  ", " ")
                link = html.unescape(link_m.group(1).strip()) if link_m else ""
                if title and len(title) > 5:
                    results.append((title, link))
            if len(results) >= max_items:
                break
        return results
    # Atom
    entries = re.findall(r'<entry>(.*?)</entry>', xml, re.DOTALL)
    if entries:
        for entry in entries:
            title_m = re.search(r'<title(?:[^>]*)>(?:<!\[CDATA\[)?\s*(.*?)\s*(?:\]\]>)?\s*</title>', entry, re.DOTALL)
            link_m = re.search(r'<link[^>]*href=["\']([^"\']+)["\']', entry)
            if title_m:
                title = html.unescape(title_m.group(1).strip().replace("\n"," ").replace("\r",""))
                while "  " in title: title = title.replace("  ", " ")
                link = html.unescape(link_m.group(1)) if link_m else ""
                if title and len(title) > 5:
                    results.append((title, link))
            if len(results) >= max_items:
                break
        return results
    return []


def is_world_cup_related(title):
    t = title.lower()
    return any(kw.lower() in t for kw in WORLD_CUP_KEYWORDS)


def merge_and_limit(entries_list, limit=5):
    """Round-robin merge: 1 from each source, cycle until limit reached.
    This ensures source diversity within each category."""
    seen = set()
    merged = []
    sources = []
    for name, items in entries_list:
        sources.append((name, list(items)))
    while len(merged) < limit:
        any_added = False
        for i, (name, items) in enumerate(sources):
            if len(merged) >= limit:
                break
            while items:
                title, link = items.pop(0)
                key = title[:40].lower()
                if key not in seen:
                    seen.add(key)
                    merged.append((title, link, name))
                    any_added = True
                    break
            if len(merged) >= limit:
                break
        if not any_added:
            break
    return merged[:limit]


def main():
    today = datetime.date.today().strftime("%Y-%m-%d")
    now = datetime.datetime.now().strftime("%H:%M")

    results = {}
    meta = {"ok": 0, "fail": 0}

    # --- RSS 新闻（轮询分配，每栏目5条） ---
    for cat, feeds in SOURCES.items():
        all_entries = []
        for name, url in feeds:
            xml = fetch_powershell(url)
            items = parse_feed(xml, 10)
            if items:
                meta["ok"] += 1
            else:
                meta["fail"] += 1
            all_entries.append((name, items))
        if cat == "⚽ 体育":
            # 世界杯优先；不足 5 条用同源其他体育新闻轮询补足（merge_and_limit 内部
            # 按 title[:40] 去重，故补足条目不会与已选的世界杯条目重复）
            wc = [(name, [(t, l) for t, l in items if is_world_cup_related(t)])
                  for name, items in all_entries]
            merged = merge_and_limit(wc, 5)
            if len(merged) < 5:
                non_wc = [(name, [(t, l) for t, l in items if not is_world_cup_related(t)])
                          for name, items in all_entries]
                merged = merged + merge_and_limit(non_wc, 5 - len(merged))
        else:
            merged = merge_and_limit(all_entries, 5)
        results[cat] = merged

    # --- GitHub 热门（独立栏目，5 条，跨天去重滚动） ---
    # 科技/AI 已是纯 RSS 5 条；GitHub 单独成栏，读最近 7 天历史去重，保证每天换新
    today_date = datetime.date.today()
    seen = load_recent_github_seen(NEWS_DIR, today_date, days=GITHUB_HISTORY_DAYS)
    github_repos = collect_github_repos(today_date, seen, limit=5)
    results["🐙 GitHub 热门"] = [
        {
            "title": r["name"],
            "link": r["url"],
            "source": "GitHub",
            "stars": r["stars"],
            "lang": r["lang"],
            "desc": r["desc"],
            "is_github": True,
        }
        for r in github_repos
    ]

    # --- 保存 .md（英文原始数据，供代理翻译） ---
    lines = [f"📰 每日新闻 ｜ {today}", ""]
    for cat, entries in results.items():
        lines.append(f"─── {cat} ───\n")
        if entries:
            for i, item in enumerate(entries, 1):
                if isinstance(item, dict):
                    if item.get("is_github"):
                        lang_part = f" — {item['lang']}" if item['lang'] else ""
                        lines.append(f"  {i}. {item['title']} — ⭐ {item['stars']}{lang_part}")
                        lines.append(f"     {item['desc']}")
                    else:
                        lines.append(f"  {i}. [{item.get('source', '')}] {item.get('title', '')}")
                else:
                    title, link, src = item
                    lines.append(f"  {i}. [{src}] {title}")
        else:
            lines.append(f"  (暂无数据)\n")
        lines.append("")

    lines.append(f"📌 来源: {meta['ok']}成功 / {meta['fail']}失败 | {now} 自动抓取")

    md_path = os.path.join(NEWS_DIR, f"{today}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # --- 保存 JSON（统一 dict 格式，方便 agent 翻译） ---
    json_path = os.path.join(NEWS_DIR, f"{today}.json")
    # Normalize all items to dict format for agent
    json_results = {}
    for cat, entries in results.items():
        json_list = []
        for item in entries:
            if isinstance(item, dict):
                json_list.append(item)
            else:
                title, link, source = item
                json_list.append({"title": title, "link": link, "source": source})
        json_results[cat] = json_list
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "results": json_results, "meta": meta}, f, ensure_ascii=False, indent=2)

    print("\n".join(lines))
    print(f"\n✅ 已保存: {md_path}")
    print(f"📋 JSON: {json_path}")


if __name__ == "__main__":
    main()

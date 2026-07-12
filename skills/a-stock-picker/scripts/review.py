# -*- coding: utf-8 -*-
"""历史复盘主流程（slice-5）：读推荐 JSONL → 回测 T+1/T+5/T+10 → 中文 Markdown 报告。

对每条历史推荐，以"推荐价"为基准，取推荐日后第 1/5/10 个交易日收盘价算收益率；
汇总推荐总数、可复盘数、各持有期胜率与平均收益、最佳/最差个股（按 T+5）。

设计要点：
- backtest_record / run 为可测核心：fetch_klines 可注入（测试 mock），缺省 get_klines。
- 入选价 = 推荐记录的 price；退出价 = K 线在推荐日索引 +n 处的收盘。
- 推荐日不在 K 线范围、或后续 K 线不足某档 → 该档收益为 None，不计入该档统计。

CLI：python scripts/review.py   （读 docs/a-stock-picker/data/recommendations.jsonl，写 docs/a-stock-picker/reports/review-YYYYMMDD.md）
"""
import os
import re

from common import REPORTS_DIR, RECOMMEND_FILE, RISK_NOTICE, calc_return, fmt_pct, read_jsonl
from market_data import get_klines
from trading_calendar import today_iso

HORIZONS = ("ret_1", "ret_5", "ret_10")   # T+1 / T+5 / T+10
HORIZON_OFFSET = {"ret_1": 1, "ret_5": 5, "ret_10": 10}
HORIZON_LABEL = {"ret_1": "T+1", "ret_5": "T+5", "ret_10": "T+10"}


def backtest_record(record, klines):
    """对单条推荐计算三档收益率。

    record: 推荐记录 dict（含 date/code/name/price）。
    klines: list[dict]（旧→新，含 date/close），只含交易日。
    返回 dict{code,name,date,entry,ret_1,ret_5,ret_10}，或 None（推荐日不在 K 线范围/数据缺失）。
    """
    rec_date = record.get("date")
    entry = record.get("price")
    if not rec_date or entry is None or not klines:
        return None

    idx = None
    for i, k in enumerate(klines):
        if k.get("date") == rec_date:
            idx = i
            break
    if idx is None:
        return None  # 推荐日不在 K 线范围，无法复盘

    def ret_at(n):
        j = idx + n
        if j >= len(klines):
            return None
        return calc_return(entry, klines[j].get("close"))

    return {
        "code": record.get("code"),
        "name": record.get("name"),
        "date": rec_date,
        "entry": entry,
        "ret_1": ret_at(HORIZON_OFFSET["ret_1"]),
        "ret_5": ret_at(HORIZON_OFFSET["ret_5"]),
        "ret_10": ret_at(HORIZON_OFFSET["ret_10"]),
    }


def _stats(values):
    """一组收益率值 → {count, win_rate, avg}；空则 win_rate/avg 为 None。"""
    if not values:
        return {"count": 0, "win_rate": None, "avg": None}
    wins = sum(1 for v in values if v > 0)
    return {"count": len(values), "win_rate": wins / len(values), "avg": sum(values) / len(values)}


def summarize(reviewed):
    """可复盘结果列表 → 汇总 dict{total(by caller), reviewed, by_horizon, best, worst}。

    reviewed: backtest_record 返回的非 None 列表。
    best/worst 按 T+5 收益率（最能代表一周持有的中等周期）。
    """
    by_horizon = {}
    for h in HORIZONS:
        vals = [r[h] for r in reviewed if r[h] is not None]
        by_horizon[h] = _stats(vals)

    with_ret5 = [r for r in reviewed if r["ret_5"] is not None]
    best = max(with_ret5, key=lambda r: r["ret_5"]) if with_ret5 else None
    worst = min(with_ret5, key=lambda r: r["ret_5"]) if with_ret5 else None
    return {"by_horizon": by_horizon, "best": best, "worst": worst}


def run(records=None, fetch_klines=None):
    """复盘主流程（可测核心）。

    records: 推荐历史 list[dict]（缺省读 RECOMMEND_FILE）。
    fetch_klines: 可注入（测试 mock），缺省 get_klines。
    返回 dict{total, reviewed, by_horizon, best, worst}。
    """
    fetch_klines = fetch_klines or get_klines
    records = read_jsonl(RECOMMEND_FILE) if records is None else list(records)
    reviewed = []
    for rec in records:
        kl = fetch_klines(rec.get("code"))
        r = backtest_record(rec, kl)
        if r is not None:
            reviewed.append(r)
    summary = summarize(reviewed)
    summary["total"] = len(records)
    summary["reviewed"] = len(reviewed)
    return summary


def format_report(summary, date=None):
    """格式化为 Markdown 报告（顶部强制风险声明）。"""
    date = date or today_iso()
    lines = ["# 选股复盘报告 · %s" % date, "", RISK_NOTICE, ""]

    lines.append("## 总览")
    lines.append("- 推荐总数：%d" % summary["total"])
    lines.append("- 可复盘数：%d" % summary["reviewed"])
    lines.append("")

    lines.append("## 各持有期收益率")
    lines.append("| 持有期 | 样本数 | 胜率 | 平均收益 |")
    lines.append("|--------|--------|------|----------|")
    for h in HORIZONS:
        s = summary["by_horizon"][h]
        wr = "%.1f%%" % (s["win_rate"] * 100) if s["win_rate"] is not None else "N/A"
        lines.append("| %s | %d | %s | %s |" % (HORIZON_LABEL[h], s["count"], wr, fmt_pct(s["avg"])))
    lines.append("")

    if summary.get("best"):
        b = summary["best"]
        lines.append("## 最佳个股（按 T+5）")
        lines.append("- %s（%s） 推荐日 %s 入选价 %s T+5 %s"
                     % (b["name"], b["code"], b["date"], b["entry"], fmt_pct(b["ret_5"])))
        lines.append("")
    if summary.get("worst"):
        w = summary["worst"]
        lines.append("## 最差个股（按 T+5）")
        lines.append("- %s（%s） 推荐日 %s 入选价 %s T+5 %s"
                     % (w["name"], w["code"], w["date"], w["entry"], fmt_pct(w["ret_5"])))
        lines.append("")

    lines.append("> 历史复盘仅供策略表现回测参考，不构成投资建议。")
    return "\n".join(lines)


def save_report(text, date=None):
    """写报告到 docs/a-stock-picker/reports/review-YYYYMMDD.md，返回路径。"""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    date = date or today_iso()
    # 防御纵深：date 进入文件名，强制 ISO 格式，杜绝路径穿越（../ 等）
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("date 必须为 YYYY-MM-DD 格式：%r" % date)
    path = os.path.join(REPORTS_DIR, "review-%s.md" % date.replace("-", ""))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def main():
    """CLI 入口：跑复盘，打印并存盘 Markdown 报告。"""
    summary = run()
    txt = format_report(summary)
    path = save_report(txt)
    print(txt)
    print("\n📄 报告已保存：%s" % path)


if __name__ == "__main__":
    main()

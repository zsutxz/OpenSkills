# -*- coding: utf-8 -*-
"""选股主流程（slice-4）：当日 Top3 推荐 + 风险声明 + JSONL 落盘。

流程：交易日判定 → 全市场快照 → filter_pool 过滤 → 候选逐个取 K 线 →
score 打分 → pick_top3 → 中文报告 + 追加 JSONL（同日去重）。

设计要点：
- run() 为可测核心：fetch_list / fetch_klines 可注入（测试用 mock，不打网络），
  缺省接 market_data 真实取数。
- 纯决策与 IO 分离：run() 返回结构化 dict，format_report() 负责呈现，main() 负责打印。
- 同日去重：重跑当日覆盖该日全部条目（按 date 过滤后重写），不产生重复行。

CLI：python scripts/recommend.py
"""
from common import (RECOMMEND_FILE, RECOMMEND_MD_FILE, RISK_NOTICE,
                    ensure_utf8_stdout, read_jsonl, render_recommendations_md,
                    rewrite_jsonl, write_text)
from market_data import get_klines, get_stock_list
from strategy import filter_pool, pick_top3, score
from trading_calendar import is_trading_day, today_iso

STRATEGY_NAME = "trend-steady"


def select_picks(snapshot, fetch_klines, top_n=3):
    """快照 → 过滤 → 逐候选取 K 线打分 → 取 Top N。

    fetch_klines: 可调用对象 fetch_klines(code) -> list[dict]，可注入。
    返回 list[dict]（score 返回非 None 者，已按分降序取前 top_n）。
    """
    candidates = filter_pool(snapshot)
    scored = []
    for stock in candidates:
        try:
            klines = fetch_klines(stock.get("code"))
            result = score(stock, klines)
        except Exception:
            # 单只取数失败（退市/停牌/接口抖动）不应中断整体选股，跳过该候选
            continue
        if result is not None:
            scored.append(result)
    return pick_top3(scored, n=top_n)


def _to_record(date, pick):
    """把 score 产出转为 JSONL 落盘记录。"""
    return {
        "date": date,
        "code": pick.get("code"),
        "name": pick.get("name"),
        "price": pick.get("price"),
        "pe": pick.get("pe"),
        "strategy": STRATEGY_NAME,
        "score": pick.get("score"),
        "reason": pick.get("reason"),
    }


def _save_with_dedup(path, date, new_records):
    """同日去重落盘：读出旧记录 → 删除当日条目 → 追加新记录 → 原子覆盖写。

    返回去重后的全部记录（kept + new），供调用方同步生成 md 镜像。
    """
    existing = read_jsonl(path)
    kept = [r for r in existing if r.get("date") != date]
    all_records = kept + new_records
    rewrite_jsonl(path, all_records)
    return all_records


def run(date=None, fetch_list=None, fetch_klines=None, top_n=3, write=True):
    """选股主流程（可测核心）。

    date: 指定日期（ISO，默认今天）。
    fetch_list / fetch_klines: 可注入的数据源（测试用），缺省用 market_data 真实取数。
    返回 dict: {date, is_trading_day, picks, written}。
      - 非交易日：is_trading_day=False, picks=[], written=False（不取数、不落盘）。
    """
    date = date or today_iso()
    fetch_list = fetch_list or get_stock_list
    fetch_klines = fetch_klines or get_klines

    if not is_trading_day(date):
        return {"date": date, "is_trading_day": False, "picks": [], "written": False}

    snapshot = fetch_list()
    picks = select_picks(snapshot, fetch_klines, top_n=top_n)
    records = [_to_record(date, p) for p in picks]
    written = False
    # 仅当本次有入选才落盘（_save_with_dedup 内含同日去重覆盖）。
    # 本次 0 入选不写不清——避免一次取数抖动/空结果清掉当日已生成的有效推荐（fail-securely）。
    if write and records:
        all_records = _save_with_dedup(RECOMMEND_FILE, date, records)
        # md 镜像：与 jsonl 同源，用全部记录整体重写，保证两份始终一致
        write_text(RECOMMEND_MD_FILE, render_recommendations_md(all_records))
        written = True
    return {"date": date, "is_trading_day": True, "picks": picks, "written": written}


def format_report(result):
    """把 run() 结果格式化为中文文本（顶部强制风险声明）。"""
    lines = [RISK_NOTICE]
    date = result["date"]
    if not result["is_trading_day"]:
        lines.append(f"\n📅 今日（{date}）非交易日，休市中，不产生推荐。")
        return "\n".join(lines)

    picks = result["picks"]
    if not picks:
        lines.append(f"\n今日（{date}）未筛选出符合条件的股票（市场无满足稳健趋势条件的标的）。")
        return "\n".join(lines)

    lines.append(f"\n📈 稳健趋势策略 · {date} 推荐 Top{len(picks)}：")
    for i, p in enumerate(picks, 1):
        lines.append(f"\n{i}. {p.get('name')}（{p.get('code')}）"
                     f"  入选价 {p.get('price')}  得分 {p.get('score')}")
        lines.append(f"   理由：{p.get('reason')}")
    if result.get("written"):
        lines.append(f"\n💾 已落盘：{RECOMMEND_FILE}")
        lines.append(f"📄 可读镜像：{RECOMMEND_MD_FILE}")
    return "\n".join(lines)


def main():
    """CLI 入口：跑当日推荐并打印。"""
    ensure_utf8_stdout()
    print(format_report(run()))


if __name__ == "__main__":
    main()

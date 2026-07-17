# -*- coding: utf-8 -*-
"""A 股交易日历：基于周一到周五 + 年度节假日表判定交易日。

节假日表（HOLIDAYS_2026）按年度手动维护，依据国务院放假安排；
生产环境可再对接交易所交易日接口校验。年度切换时需补下一年表。
"""
from datetime import date, datetime, timedelta

# 2026 年 A 股休市日（元旦 / 春节 / 清明 / 劳动节 / 端午 / 中秋·国庆）
HOLIDAYS_2026 = {
    # 元旦
    "2026-01-01",
    # 春节（农历正月初一 = 2026-02-17）
    "2026-02-15", "2026-02-16", "2026-02-17", "2026-02-18",
    "2026-02-19", "2026-02-20", "2026-02-21",
    # 清明
    "2026-04-04", "2026-04-05", "2026-04-06",
    # 劳动节
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05",
    # 端午
    "2026-06-19", "2026-06-20", "2026-06-21",
    # 中秋·国庆（2026 中秋 = 09-25，与国庆连休）
    "2026-09-25", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
}

HOLIDAYS = set(HOLIDAYS_2026)


def _to_date(d):
    """把 str/datetime 归一化为 date。"""
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(str(d), "%Y-%m-%d").date()


def is_trading_day(d=None):
    """判定给定日期是否 A 股交易日（d 缺省为今天）。"""
    dt = _to_date(d) if d is not None else date.today()
    if dt.weekday() >= 5:  # 周六=5 周日=6
        return False
    if dt.isoformat() in HOLIDAYS:
        return False
    return True


def last_trading_day(d=None):
    """返回**严格早于** d 的最近一个交易日（ISO 字符串）。

    用于复盘场景：取"已完成收盘"的交易日，避免把未收盘的当天算进去。
    """
    dt = _to_date(d) if d is not None else date.today()
    dt -= timedelta(days=1)
    while not is_trading_day(dt):
        dt -= timedelta(days=1)
    return dt.isoformat()


def today_iso():
    return date.today().isoformat()

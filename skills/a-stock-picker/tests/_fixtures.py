# -*- coding: utf-8 -*-
"""a-stock-picker 测试共享 fixture：K 线序列、快照列表、浮点近似比较。

供 test_strategy / test_recommend / test_contract / test_indicators / test_review 复用，
避免各测试文件重复维护同款构造函数。导入示例：from _fixtures import rising_klines
"""
from datetime import datetime, timedelta


def rising_klines(n=120, growth=1.006, vol_base=1000.0, vol_recent_mult=1.4, end_date=None):
    """生成 n 根上升 K 线：close 按 growth 复利上升，近 5 日量放大 vol_recent_mult 倍。

    量比 = 近5日均量 / 近20日均量 = 20*mult/(15+5*mult)（mult=1.4 → 1.27；mult=6.0 → 2.67）。
    end_date 指定时每根额外带连续日期（末日=end_date），供 review 按 rec_date 定位算 T+n；
    不指定则只含 close/volume，供 strategy/indicators 纯指标计算。
    """
    closes = [100.0 * (growth ** i) for i in range(n)]
    vols = [vol_base] * (n - 5) + [vol_base * vol_recent_mult] * 5
    if end_date is None:
        return [{"close": c, "volume": v} for c, v in zip(closes, vols)]
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    dates = [(end - timedelta(days=n - 1 - i)).isoformat() for i in range(n)]
    return [{"date": d, "close": c, "volume": v} for d, c, v in zip(dates, closes, vols)]


def snapshot_fixture(include_filtered=False, n_normal=5):
    """构造 market_data.get_stock_list 风格的快照列表。

    默认返回 n_normal 只正常股（可通过 filter_pool + score 入选）；include_filtered=True
    时追加 2 只应被过滤的票（ST+亏损、亏损），用于验证 filter_pool 的剔除逻辑。
    """
    normal = [
        {"code": "600001", "name": "科创先锋", "price": 25.0, "pe": 30.0},
        {"code": "600002", "name": "蓝筹稳健", "price": 12.0, "pe": 18.0},
        {"code": "600003", "name": "成长之星", "price": 8.5, "pe": 22.0},
        {"code": "600004", "name": "价值回归", "price": 45.0, "pe": 15.0},
        {"code": "600005", "name": "新兴产业", "price": 33.0, "pe": 40.0},
    ]
    out = list(normal[:n_normal])
    if include_filtered:
        out.extend([
            {"code": "600099", "name": "ST问题股", "price": 3.0, "pe": -2.0},
            {"code": "600098", "name": "亏损股", "price": 5.0, "pe": -5.0},
        ])
    return out


def approx(a, b, tol=1e-6):
    """None 安全的浮点近似比较：双方皆 None 视为相等，仅一方为 None 视为不等。"""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol

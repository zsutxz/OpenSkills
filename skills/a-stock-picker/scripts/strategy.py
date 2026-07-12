# -*- coding: utf-8 -*-
"""稳健趋势策略（slice-3）：候选池过滤 + 条件筛选 + 综合打分 + 取 Top3。

纯函数、无 IO：输入为快照 dict 与 K 线列表，输出打分结果或 None。
网络取数（get_stock_list / get_klines）由 recommend.py 在外层完成，
本模块只做"给数据 → 出结论"的决策，便于纯单测。

入选条件（全部满足才打分）：
- MA 多头排列：close > MA5 > MA10 > MA20
- 温和放量：VOL_MILD_LO <= 量比 <= VOL_MILD_HI
- MACD 多头（零轴上方）：DIF > DEA 且 DIF > 0

打分（0~100，越大越优）：趋势强度 50% + 量价配合 30% + 动能 20%，各维度归一化到 [0,1]。
阈值（TREND_FULL / MOMENTUM_FULL 等）为经验可调常量，见模块顶部。
"""
from indicators import ma, macd, vol_ratio

# ---- 过滤与打分阈值（经验值，可调）----
MIN_LISTING_DAYS = 60      # 次新过滤：上市不足此天数剔除（快照带 listing_days 时生效）
KLINE_MIN = 60             # K 线最少根数：不足视为数据不足（含次新兜底）
VOL_MILD_LO = 1.1          # 温和放量下界
VOL_MILD_HI = 2.5          # 温和放量上界
VOL_SWEET = 1.5            # 量比甜点：越接近此值得分越高
TREND_FULL = 0.10          # (close-MA20)/MA20 达 10% → 趋势维度满分
MOMENTUM_FULL = 0.02       # (DIF-DEA)/close 达 2% → 动能维度满分
W_TREND, W_VOL, W_MOM = 0.5, 0.3, 0.2   # 三维度权重

# ST 标记：A股对 ST/*ST/退市股有强制名称前缀，子串匹配即可（"*ST" 已被 "ST" 覆盖）
_ST_MARKERS = ("ST", "退")


def filter_pool(snapshot, min_listing_days=MIN_LISTING_DAYS):
    """候选池过滤：剔除 ST/*ST/退、亏损(PE<=0)、停牌(无最新价)、次新(可选)。

    snapshot: list[dict]，每项含 {code,name,price,pe}；listing_days 为可选字段。
    返回通过过滤的 list[dict]（不修改原列表）。

    说明：快照本身不含上市日期，次新在生产路径上由 score() 的 K 线长度兜底；
    此处 listing_days 检查作为可选双保险，便于单测与未来接入 IPO 日期字段。
    """
    out = []
    for s in snapshot:
        name = str(s.get("name", ""))
        if any(m in name for m in _ST_MARKERS):
            continue
        price = s.get("price")
        if price is None or price <= 0:          # 停牌 / 无最新价
            continue
        pe = s.get("pe")
        if pe is not None and pe <= 0:           # 亏损
            continue
        ld = s.get("listing_days")
        if ld is not None and ld < min_listing_days:  # 次新（仅当字段存在）
            continue
        out.append(s)
    return out


def _last(seq):
    """取序列最后一个非 None 值；序列为空或全 None 返回 None。"""
    for v in reversed(seq):
        if v is not None:
            return v
    return None


def _clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x


def score(stock, klines):
    """对单只股票打分。

    stock: 快照 dict（含 code/name/price/pe）。
    klines: list[dict]，每项含 {close, volume, ...}，旧→新。
    返回 dict{code,name,price,pe,score,reason}，或 None（不满足入选条件 / 数据不足）。
    """
    if not klines or len(klines) < KLINE_MIN:
        return None
    closes = [k["close"] for k in klines if k.get("close") is not None]
    vols = [k["volume"] for k in klines if k.get("volume") is not None]
    if len(closes) < KLINE_MIN or len(vols) < KLINE_MIN:
        return None

    close = closes[-1]
    ma5 = _last(ma(closes, 5))
    ma10 = _last(ma(closes, 10))
    ma20 = _last(ma(closes, 20))
    dif, dea, _ = macd(closes)
    dif_v = _last(dif)
    dea_v = _last(dea)
    vr = vol_ratio(vols)

    # 任一关键指标数据不足 → 不入选
    if None in (ma5, ma10, ma20, dif_v, dea_v, vr):
        return None

    # ---- 入选条件（全部满足）----
    if not (close > ma5 > ma10 > ma20):          # MA 多头排列
        return None
    if not (VOL_MILD_LO <= vr <= VOL_MILD_HI):   # 温和放量
        return None
    if not (dif_v > dea_v and dif_v > 0):        # MACD 多头（零轴上方）
        return None

    # ---- 综合打分（各维度归一化到 [0,1] 再加权）----
    trend = _clamp01((close - ma20) / ma20 / TREND_FULL)
    volp = _clamp01(1.0 - abs(vr - VOL_SWEET))   # 越接近甜点越高
    mom = _clamp01((dif_v - dea_v) / close / MOMENTUM_FULL)
    final = 100.0 * (W_TREND * trend + W_VOL * volp + W_MOM * mom)

    reason = (
        f"均线多头排列(close{close:.2f}>MA5>MA10>MA20);"
        f"温和放量{vr:.2f}倍;MACD零轴上方多头(DIF{dif_v:.3f}>DEA{dea_v:.3f})"
    )
    return {
        "code": stock.get("code"),
        "name": stock.get("name"),
        "price": stock.get("price"),
        "pe": stock.get("pe"),
        "score": round(final, 1),
        "reason": reason,
    }


def pick_top3(scored, n=3):
    """从打分结果取 Top N（默认 3），按分数降序。

    scored: list[dict]，每项含 score 字段（由 score() 产出）。
    """
    return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:n]

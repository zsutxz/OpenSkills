# -*- coding: utf-8 -*-
"""技术指标纯函数（slice-2）：MA / EMA / MACD / 量比。

全部为无 IO、无副作用的纯函数，输入输出均为数值列表，可独立单测。
数据不足时返回 None（而非抛异常），交由上层策略判断。

序列约定：返回列表与输入等长，未定义位置（前置窗口不足）填 None，
便于与 K 线按索引对齐。
"""


def ma(values, n):
    """简单移动平均 SMA(n)。

    返回与 values 等长的列表，索引 i 处为 values[i-n+1..i] 的算术均值；
    i < n-1 的位置为 None。n <= 0 或空输入时全部为 None。

    例：ma([1,2,3,4,5], 3) == [None, None, 2.0, 3.0, 4.0]
    """
    if not values:
        return []
    if n <= 0:
        return [None] * len(values)
    out = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def ema(values, n):
    """指数移动平均 EMA(n)。

    前 n-1 位为 None；第 n 个值（索引 n-1）用前 n 个值的 SMA 作种子，
    之后 ema[i] = α*values[i] + (1-α)*ema[i-1]，α = 2/(n+1)。
    这是同花顺/通达信等 A 股行情软件的通用约定。
    输入长度不足 n 时全部为 None。
    """
    if not values:
        return []
    if len(values) < n:
        return [None] * len(values)
    alpha = 2.0 / (n + 1)
    out = [None] * (n - 1)
    prev = sum(values[:n]) / n  # SMA 种子
    out.append(prev)
    for i in range(n, len(values)):
        prev = alpha * values[i] + (1 - alpha) * prev
        out.append(prev)
    return out


def _ema_over_suffix(series, n):
    """对 series 求EMA，但跳过前导 None（如 DIF 序列前段未定义）。

    前导 None 段原样保留，对其后的非 None 连续段求 EMA 并对齐回填。
    """
    start = 0
    while start < len(series) and series[start] is None:
        start += 1
    tail = series[start:]
    return [None] * start + ema(tail, n)


def macd(closes, fast=12, slow=26, signal=9):
    """MACD(fast=12, slow=26, signal=9)。

    返回 (dif, dea, hist) 三序列，均与 closes 等长：
    - dif  = EMA(close, fast) - EMA(close, slow)   差离值
    - dea  = EMA(dif, signal)                       信号线
    - hist = 2 * (dif - dea)                        柱状图（通达信约定）

    各序列在窗口不足处为 None。完整尾部三值需 closes 长度 >= slow + signal - 1。
    """
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    dif = [
        (f - s) if (f is not None and s is not None) else None
        for f, s in zip(ema_fast, ema_slow)
    ]
    dea = _ema_over_suffix(dif, signal)
    hist = [
        2 * (d - e) if (d is not None and e is not None) else None
        for d, e in zip(dif, dea)
    ]
    return dif, dea, hist


def vol_ratio(volumes, short=5, long=20):
    """量比 = 近 short 日均量 / 近 long 日均量（取最新值）。

    用于判断温和放量：比值落在 1.1~2.5x 视为温和放量。
    数据不足（长度 < long）或分母为 0 时返回 None。
    """
    if long <= 0 or short <= 0 or len(volumes) < long:
        return None
    short_avg = sum(volumes[-short:]) / short
    long_avg = sum(volumes[-long:]) / long
    if long_avg == 0:
        return None
    return short_avg / long_avg

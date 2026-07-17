# -*- coding: utf-8 -*-
"""indicators 单元测试（slice-2 · 技术指标纯函数）。

全部为纯数值断言，无网络、无 IO。运行：python tests/test_indicators.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from indicators import ma, ema, macd, vol_ratio  # noqa: E402


def _approx(a, b, tol=1e-6):
    """None 安全的浮点近似比较。"""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def _seq_approx(xs, ys, tol=1e-6):
    if len(xs) != len(ys):
        return False
    return all(_approx(a, b, tol) for a, b in zip(xs, ys))


class TestMa(unittest.TestCase):
    def test_acceptance_exact(self):
        # slices.md 验收样例
        self.assertEqual(ma([1, 2, 3, 4, 5], 3), [None, None, 2.0, 3.0, 4.0])

    def test_window_equals_length(self):
        self.assertEqual(ma([1, 2, 3], 3), [None, None, 2.0])

    def test_window_too_big(self):
        self.assertEqual(ma([1, 2], 3), [None, None])

    def test_empty(self):
        self.assertEqual(ma([], 3), [])

    def test_n_le_zero(self):
        # 非法窗口全部返回 None，不抛异常
        self.assertEqual(ma([1, 2, 3], 0), [None, None, None])

    def test_decimal_values(self):
        # 1.0, 2.0, 3.0 的 2 日均线
        self.assertEqual(ma([1.0, 2.0, 3.0], 2), [None, 1.5, 2.5])


class TestEma(unittest.TestCase):
    def test_linear_hand_computed(self):
        # α=0.5, 种子=mean([1,2,3])=2.0, 之后 0.5*cur+0.5*prev
        self.assertTrue(_seq_approx(
            ema([1, 2, 3, 4, 5, 6], 3), [None, None, 2.0, 3.0, 4.0, 5.0]))

    def test_too_short(self):
        self.assertEqual(ema([1, 2], 3), [None, None])

    def test_empty(self):
        self.assertEqual(ema([], 3), [])

    def test_length_aligned(self):
        out = ema(list(range(1, 21)), 5)
        self.assertEqual(len(out), 20)
        self.assertEqual(out[:4], [None, None, None, None])  # 前 n-1 位 None
        self.assertIsNotNone(out[4])


class TestMacd(unittest.TestCase):
    def test_flat_all_zero(self):
        # 平盘序列：EMA12=EMA26 → DIF=DEA=0 → HIST=0
        closes = [10.0] * 40
        dif, dea, hist = macd(closes)
        self.assertEqual(len(dif), 40)
        self.assertTrue(_approx(dif[-1], 0.0))
        self.assertTrue(_approx(dea[-1], 0.0))
        self.assertTrue(_approx(hist[-1], 0.0))

    def test_linear_rising_hand_computed(self):
        # 线性上升 1..40：EMA12 与 EMA26 同斜率 → DIF 恒为 7.0
        # DEA=EMA9(常数)=7.0，稳态无加速度 → HIST=0.0
        closes = [float(i) for i in range(1, 41)]
        dif, dea, hist = macd(closes)
        self.assertTrue(_approx(dif[-1], 7.0))
        self.assertTrue(_approx(dea[-1], 7.0))
        self.assertTrue(_approx(hist[-1], 0.0))

    def test_definition_boundaries(self):
        closes = [10.0] * 40
        dif, dea, _ = macd(closes)
        # EMA26 从索引 25 起有值 → DIF[24]=None, DIF[25] 有值
        self.assertIsNone(dif[24])
        self.assertIsNotNone(dif[25])
        # DEA=EMA9(DIF) 从索引 33 起有值
        self.assertIsNone(dea[32])
        self.assertIsNotNone(dea[33])

    def test_too_short_all_none(self):
        dif, dea, hist = macd([float(i) for i in range(1, 26)])  # 25 根 < 26
        self.assertTrue(all(x is None for x in dif))
        self.assertTrue(all(x is None for x in dea))
        self.assertTrue(all(x is None for x in hist))

    def test_partial_dea(self):
        # 26~33 根：DIF 已有值但 DEA 尾部仍未定义
        dif, dea, _ = macd([float(i) for i in range(1, 31)])  # 30 根
        self.assertIsNotNone(dif[-1])
        self.assertIsNone(dea[-1])

    def test_invariants(self):
        # 加速序列：HIST 必有非零点；全程满足组合不变量
        closes = [float(i * i) for i in range(1, 41)]
        dif, dea, hist = macd(closes)
        self.assertTrue(any(h is not None and abs(h) > 1e-6 for h in hist))
        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        for i, (d, e, h) in enumerate(zip(dif, dea, hist)):
            if d is None:
                self.assertIsNone(e)
                self.assertIsNone(h)
                continue
            # DIF == EMA12 - EMA26
            self.assertTrue(_approx(d, ema12[i] - ema26[i]))
            if e is not None:
                # HIST == 2 * (DIF - DEA)（通达信柱状图约定）
                self.assertTrue(_approx(h, 2 * (d - e)))


class TestVolRatio(unittest.TestCase):
    def test_constructed(self):
        # 近 5 日均 20，近 20 日均 12.5 → 1.6
        vols = [10.0] * 15 + [20.0] * 5
        self.assertTrue(_approx(vol_ratio(vols), 1.6))

    def test_too_short(self):
        self.assertIsNone(vol_ratio([1.0] * 19))

    def test_zero_long_avg(self):
        self.assertIsNone(vol_ratio([0.0] * 20))

    def test_flat_equals_one(self):
        self.assertTrue(_approx(vol_ratio([5.0] * 20), 1.0))

    def test_swapped_params_returns_none(self):
        # short>long 为非法调用，返回 None 而非静默错误值（slice-2 遗留 M1）
        self.assertIsNone(vol_ratio([1.0] * 20, short=20, long=5))


if __name__ == "__main__":
    unittest.main(verbosity=2)

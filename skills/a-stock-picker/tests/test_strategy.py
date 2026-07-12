# -*- coding: utf-8 -*-
"""strategy 单元测试（slice-3 · 稳健趋势策略）。

全部为纯逻辑断言，无网络、无 IO。运行：python tests/test_strategy.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from strategy import filter_pool, score, pick_top3  # noqa: E402


# ---------- 测试用 fixture 构造 ----------

def _snap(code, name="测试股", price=10.0, pe=20.0, listing_days=None):
    """构造一条快照 dict（模拟 market_data.get_stock_list 返回项）。"""
    s = {"code": code, "name": name, "price": price, "pe": pe}
    if listing_days is not None:
        s["listing_days"] = listing_days
    return s


def _rising_klines(n, growth, vol_base=1000.0, vol_recent_mult=1.4):
    """生成 n 根上升 K 线：close 按 growth 复利上升，近 5 日量放大 vol_recent_mult 倍。

    量比 = 近5日均量 / 近20日均量 = 20*mult/(15+5*mult)
    （mult=1.4 → 1.27；mult=6.0 → 2.67）
    """
    closes = [100.0 * (growth ** i) for i in range(n)]
    vols = [vol_base] * (n - 5) + [vol_base * vol_recent_mult] * 5
    return [{"close": c, "volume": v} for c, v in zip(closes, vols)]


class TestFilterPool(unittest.TestCase):
    def _good(self):
        return _snap("600519", "贵州茅台", price=1680.0, pe=28.5)

    def test_keeps_normal_stock(self):
        out = filter_pool([self._good()])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["code"], "600519")

    def test_filters_st(self):
        # 名称含 ST / *ST / 退 → 剔除
        st = [_snap("600001", "ST海马"), _snap("600002", "*ST海航"),
              _snap("600003", "退市美都"), self._good()]
        out = filter_pool(st)
        self.assertEqual([s["code"] for s in out], ["600519"])

    def test_filters_loss(self):
        # 亏损：PE 为负 → 剔除；PE 缺失(None) → 保留（未知，非亏损）
        loss = _snap("600010", "亏损股", pe=-5.0)
        unknown_pe = _snap("600011", "无PE股", pe=None)
        out = filter_pool([loss, unknown_pe, self._good()])
        self.assertEqual([s["code"] for s in out], ["600011", "600519"])

    def test_filters_suspended(self):
        # 停牌：无最新价(price=None) 或 price<=0 → 剔除
        suspended = _snap("600020", "停牌A", price=None)
        zero = _snap("600021", "停牌B", price=0)
        out = filter_pool([suspended, zero, self._good()])
        self.assertEqual([s["code"] for s in out], ["600519"])

    def test_filters_xinxin_by_listing_days(self):
        # 次新：listing_days < 60 → 剔除（仅当字段存在时生效）
        xinxin = _snap("688001", "次新股", listing_days=30)
        mature = _snap("688002", "老次新", listing_days=100)
        out = filter_pool([xinxin, mature, self._good()])
        self.assertEqual([s["code"] for s in out], ["688002", "600519"])

    def test_empty_input(self):
        self.assertEqual(filter_pool([]), [])

    def test_does_not_mutate_input(self):
        src = [self._good()]
        _ = filter_pool(src)
        self.assertEqual(len(src), 1)  # 原列表不被修改


class TestScore(unittest.TestCase):
    def test_passing_stock_returns_dict(self):
        stock = _snap("600519", "贵州茅台", price=1680.0, pe=28.5)
        r = score(stock, _rising_klines(120, 1.005))
        self.assertIsNotNone(r)
        self.assertEqual(r["code"], "600519")
        for key in ("name", "price", "pe", "score", "reason"):
            self.assertIn(key, r)

    def test_score_in_0_100(self):
        stock = _snap("600519")
        for growth in (1.003, 1.005, 1.008, 1.012):
            r = score(stock, _rising_klines(120, growth))
            self.assertIsNotNone(r, f"growth={growth} 应入选")
            self.assertTrue(0.0 <= r["score"] <= 100.0, f"score={r['score']} 越界")

    def test_monotonic_stronger_trend_scores_higher(self):
        # 更强上升趋势应得更高分（趋势维度 50% 权重主导）
        stock = _snap("600519")
        weak = score(stock, _rising_klines(120, 1.005))
        strong = score(stock, _rising_klines(120, 1.012))
        self.assertIsNotNone(weak)
        self.assertIsNotNone(strong)
        self.assertGreater(strong["score"], weak["score"])

    def test_returns_none_flat_series(self):
        # 平盘：close==MA5 → 不满足 close>MA5
        flat = [{"close": 100.0, "volume": 1000.0}] * 120
        self.assertIsNone(score(_snap("600001"), flat))

    def test_returns_none_declining(self):
        self.assertIsNone(score(_snap("600001"), _rising_klines(120, 0.995)))

    def test_returns_none_flat_volume(self):
        # 上升但量能平（量比≈1.0 < 1.1）→ 隔离量能条件
        closes = [100.0 * (1.005 ** i) for i in range(120)]
        flat_vol = [{"close": c, "volume": 1000.0} for c in closes]
        self.assertIsNone(score(_snap("600519"), flat_vol))

    def test_returns_none_excessive_volume(self):
        # 量比过大（mult=6 → ≈2.67 > 2.5）→ 隔离量能上界
        self.assertIsNone(score(_snap("600519"), _rising_klines(120, 1.005, vol_recent_mult=6.0)))

    def test_returns_none_insufficient_data(self):
        # K 线不足 60 根（次新/数据不足兜底）
        self.assertIsNone(score(_snap("600001"), _rising_klines(40, 1.01)))

    def test_returns_none_empty_klines(self):
        self.assertIsNone(score(_snap("600001"), []))

    def test_reason_mentions_conditions(self):
        r = score(_snap("600519", "贵州茅台"), _rising_klines(120, 1.005))
        self.assertIsNotNone(r)
        self.assertIsInstance(r["reason"], str)
        self.assertIn("多头", r["reason"])
        self.assertIn("放量", r["reason"])
        self.assertIn("MACD", r["reason"])


class TestPickTop3(unittest.TestCase):
    def _scored(self, code, s):
        return {"code": code, "name": code, "price": 10.0, "pe": 20.0,
                "score": s, "reason": "x"}

    def test_sorted_top3(self):
        items = [self._scored("A", 50), self._scored("B", 90),
                 self._scored("C", 70), self._scored("D", 30),
                 self._scored("E", 85)]
        out = pick_top3(items)
        self.assertEqual(len(out), 3)
        self.assertEqual([o["code"] for o in out], ["B", "E", "C"])

    def test_fewer_than_3(self):
        items = [self._scored("A", 50), self._scored("B", 90)]
        self.assertEqual([o["code"] for o in pick_top3(items)], ["B", "A"])

    def test_empty(self):
        self.assertEqual(pick_top3([]), [])

    def test_custom_n(self):
        items = [self._scored(c, i) for i, c in enumerate("ABCDE")]
        self.assertEqual(len(pick_top3(items, n=2)), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

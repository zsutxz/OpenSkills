# -*- coding: utf-8 -*-
"""review 单元测试（slice-5 · 历史复盘）。

用 fixture 历史推荐 + mock K 线（不打网络）验证：T+1/T+5/T+10 收益率计算、
汇总（总数/可复盘/胜率/平均/最佳最差）、Markdown 报告含风险声明。
运行：python tests/test_review.py
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import review  # noqa: E402


def _approx(a, b, tol=1e-6):
    return a is not None and b is not None and abs(a - b) <= tol


def _klines(rec_date, base_close, exit_prices):
    """构造 K 线：rec_date 前 2 天 ~ 后 12 天，exit_prices={offset:close} 指定关键日收盘，
    其余日填 base_close。rec_date 处（offset 0）日期 == rec_date。"""
    base = datetime.strptime(rec_date, "%Y-%m-%d")
    out = []
    for off in range(-2, 13):
        d = (base + timedelta(days=off)).date().isoformat()
        out.append({"date": d, "close": exit_prices.get(off, base_close)})
    return out


class TestBacktestRecord(unittest.TestCase):
    def test_returns_at_each_horizon(self):
        rec = {"date": "2026-07-01", "code": "600001", "name": "测试股", "price": 10.0}
        kl = _klines("2026-07-01", 10.0, {1: 10.5, 5: 11.0, 10: 9.5})
        r = review.backtest_record(rec, kl)
        self.assertIsNotNone(r)
        self.assertTrue(_approx(r["ret_1"], 0.05))    # (10.5-10)/10
        self.assertTrue(_approx(r["ret_5"], 0.10))    # (11.0-10)/10
        self.assertTrue(_approx(r["ret_10"], -0.05))  # (9.5-10)/10

    def test_date_not_in_klines_returns_none(self):
        # 推荐日不在 K 线范围 → 不可复盘
        rec = {"date": "2026-01-01", "code": "600001", "name": "x", "price": 10.0}
        kl = _klines("2026-07-01", 10.0, {1: 10.5})
        self.assertIsNone(review.backtest_record(rec, kl))

    def test_insufficient_future_returns_none_for_that_horizon(self):
        # 后续 K 线不足 T+10 → ret_10 为 None（但 ret_1/ret_5 可有）
        rec = {"date": "2026-07-01", "code": "600001", "name": "x", "price": 10.0}
        base = datetime.strptime("2026-07-01", "%Y-%m-%d")
        # 只到 offset +6（不足以算 T+10）
        kl = [{"date": (base + timedelta(days=off)).date().isoformat(),
               "close": 10.0 + off * 0.1} for off in range(-2, 7)]
        r = review.backtest_record(rec, kl)
        self.assertIsNotNone(r)
        self.assertIsNotNone(r["ret_1"])
        self.assertIsNotNone(r["ret_5"])
        self.assertIsNone(r["ret_10"])

    def test_empty_klines_returns_none(self):
        rec = {"date": "2026-07-01", "code": "600001", "name": "x", "price": 10.0}
        self.assertIsNone(review.backtest_record(rec, []))


class TestRun(unittest.TestCase):
    def _records_and_klines(self):
        """3 条推荐：A T+5=+10%, B T+5=-5%, C T+5=+20%。"""
        recs = [
            {"date": "2026-07-01", "code": "A", "name": "甲股", "price": 10.0},
            {"date": "2026-07-01", "code": "B", "name": "乙股", "price": 10.0},
            {"date": "2026-07-01", "code": "C", "name": "丙股", "price": 10.0},
        ]
        klines = {
            "A": _klines("2026-07-01", 10.0, {5: 11.0}),   # +10%
            "B": _klines("2026-07-01", 10.0, {5: 9.5}),    # -5%
            "C": _klines("2026-07-01", 10.0, {5: 12.0}),   # +20%
        }
        return recs, klines

    def test_summary_stats(self):
        recs, klines = self._records_and_klines()
        s = review.run(records=recs, fetch_klines=lambda c: klines[c])
        self.assertEqual(s["total"], 3)
        self.assertEqual(s["reviewed"], 3)
        t5 = s["by_horizon"]["ret_5"]
        self.assertEqual(t5["count"], 3)
        self.assertTrue(_approx(t5["win_rate"], 2 / 3))         # A、C 为正
        self.assertTrue(_approx(t5["avg"], (0.10 - 0.05 + 0.20) / 3))

    def test_best_worst_by_ret5(self):
        recs, klines = self._records_and_klines()
        s = review.run(records=recs, fetch_klines=lambda c: klines[c])
        self.assertEqual(s["best"]["code"], "C")    # +20%
        self.assertEqual(s["worst"]["code"], "B")  # -5%

    def test_unreviewable_excluded(self):
        # D 的推荐日不在其 K 线 → 不可复盘，reviewed < total
        recs = [
            {"date": "2026-07-01", "code": "A", "name": "甲", "price": 10.0},
            {"date": "2025-01-01", "code": "D", "name": "丁", "price": 10.0},
        ]
        klines = {"A": _klines("2026-07-01", 10.0, {5: 11.0}),
                  "D": _klines("2026-07-01", 10.0, {5: 11.0})}
        s = review.run(records=recs, fetch_klines=lambda c: klines[c])
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["reviewed"], 1)


class TestFormatReport(unittest.TestCase):
    def test_contains_risk_notice_and_sections(self):
        recs, klines = TestRun._records_and_klines(self)
        s = review.run(records=recs, fetch_klines=lambda c: klines[c])
        txt = review.format_report(s, date="2026-07-12")
        self.assertIn("风险声明", txt)
        self.assertIn("复盘", txt)
        self.assertIn("T+1", txt)
        self.assertIn("T+5", txt)
        self.assertIn("T+10", txt)
        self.assertIn("胜率", txt)
        self.assertIn("丙股", txt)  # 最佳
        self.assertIn("乙股", txt)  # 最差

    def test_empty_summary_does_not_crash(self):
        txt = review.format_report(
            {"total": 0, "reviewed": 0,
             "by_horizon": {h: {"count": 0, "win_rate": None, "avg": None}
                            for h in ("ret_1", "ret_5", "ret_10")},
             "best": None, "worst": None}, date="2026-07-12")
        self.assertIn("风险声明", txt)
        self.assertIn("0", txt)


class TestSaveReport(unittest.TestCase):
    def setUp(self):
        self._orig = review.REPORTS_DIR
        review.REPORTS_DIR = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(review.REPORTS_DIR, ignore_errors=True)
        review.REPORTS_DIR = self._orig

    def test_writes_dated_file(self):
        path = review.save_report("# 报告\n内容", date="2026-07-12")
        self.assertTrue(os.path.exists(path))
        self.assertIn("20260712", path)  # 文件名 review-YYYYMMDD.md

    def test_invalid_date_raises(self):
        # 非 ISO 格式（含路径穿越尝试）→ 拒绝
        with self.assertRaises(ValueError):
            review.save_report("x", date="../../evil")
        with self.assertRaises(ValueError):
            review.save_report("x", date="not-a-date")


if __name__ == "__main__":
    unittest.main(verbosity=2)

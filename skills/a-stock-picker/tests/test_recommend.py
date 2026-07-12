# -*- coding: utf-8 -*-
"""recommend 单元测试（slice-4 · 选股主流程 + 持久化）。

用 mock 数据源（不打网络）验证：主流程聚合 Top3、JSONL 落盘字段、
非交易日不落盘、同日重跑去重、跨日保留。运行：python tests/test_recommend.py
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import recommend  # noqa: E402


def _rising_klines(n=120, growth=1.006, vol_recent_mult=1.4):
    """上升 K 线（可通过 score 入选条件）。"""
    closes = [100.0 * (growth ** i) for i in range(n)]
    vols = [1000.0] * (n - 5) + [1000.0 * vol_recent_mult] * 5
    return [{"close": c, "volume": v} for c, v in zip(closes, vols)]


def _snapshot_fixture():
    """5 只正常股（入选）+ 2 只应被 filter_pool 剔除的票。"""
    return [
        {"code": "600001", "name": "科创先锋", "price": 25.0, "pe": 30.0},
        {"code": "600002", "name": "蓝筹稳健", "price": 12.0, "pe": 18.0},
        {"code": "600003", "name": "成长之星", "price": 8.5, "pe": 22.0},
        {"code": "600004", "name": "价值回归", "price": 45.0, "pe": 15.0},
        {"code": "600005", "name": "新兴产业", "price": 33.0, "pe": 40.0},
        {"code": "600099", "name": "ST问题股", "price": 3.0, "pe": -2.0},  # 过滤(ST+亏损)
        {"code": "600098", "name": "亏损股", "price": 5.0, "pe": -5.0},   # 过滤(亏损)
    ]


def _mock_fetch_klines():
    def _fk(code):
        return _rising_klines()
    return _fk


class TestRun(unittest.TestCase):
    def setUp(self):
        # 重定向落盘路径到临时文件，避免污染真实 docs/a-stock-picker/data/recommendations.jsonl
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        self.tmp.close()
        self._orig = recommend.RECOMMEND_FILE
        recommend.RECOMMEND_FILE = self.tmp.name

    def tearDown(self):
        recommend.RECOMMEND_FILE = self._orig
        if os.path.exists(self.tmp.name):
            os.remove(self.tmp.name)

    def _lines(self):
        with open(self.tmp.name, encoding="utf-8") as f:
            return [line for line in f if line.strip()]

    def test_trading_day_selects_top3_and_writes(self):
        r = recommend.run(date="2026-07-10",  # 周五·交易日
                          fetch_list=lambda: _snapshot_fixture(),
                          fetch_klines=_mock_fetch_klines())
        self.assertTrue(r["is_trading_day"])
        self.assertEqual(len(r["picks"]), 3)
        self.assertTrue(r["written"])
        for p in r["picks"]:
            for k in ("code", "name", "price", "score", "reason"):
                self.assertIn(k, p)
        # 过滤生效：入选 code 必属 5 只正常股，不含被剔除的 600098/600099
        good_codes = {"600001", "600002", "600003", "600004", "600005"}
        self.assertTrue({p["code"] for p in r["picks"]} <= good_codes)
        # JSONL 落盘 3 条，字段齐全
        lines = self._lines()
        self.assertEqual(len(lines), 3)
        rec = json.loads(lines[0])
        for k in ("date", "code", "name", "price", "pe", "strategy", "score", "reason"):
            self.assertIn(k, rec)
        self.assertEqual(rec["strategy"], "trend-steady")
        self.assertEqual(rec["date"], "2026-07-10")

    def test_non_trading_day_no_write(self):
        r = recommend.run(date="2026-07-11",  # 周六·非交易日
                          fetch_list=lambda: _snapshot_fixture(),
                          fetch_klines=_mock_fetch_klines())
        self.assertFalse(r["is_trading_day"])
        self.assertEqual(r["picks"], [])
        self.assertFalse(r["written"])
        self.assertEqual(os.path.getsize(self.tmp.name), 0)  # 不落盘

    def test_dedup_same_day_overwrites(self):
        fk = _mock_fetch_klines()
        recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(), fetch_klines=fk)
        recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(), fetch_klines=fk)
        lines = self._lines()
        self.assertEqual(len(lines), 3)  # 同日重跑不翻倍
        for line in lines:
            self.assertEqual(json.loads(line)["date"], "2026-07-10")

    def test_dedup_keeps_other_days(self):
        fk = _mock_fetch_klines()
        recommend.run(date="2026-07-09", fetch_list=lambda: _snapshot_fixture(), fetch_klines=fk)
        recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(), fetch_klines=fk)
        recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(), fetch_klines=fk)
        dates = sorted(json.loads(line)["date"] for line in self._lines())
        self.assertEqual(dates.count("2026-07-09"), 3)
        self.assertEqual(dates.count("2026-07-10"), 3)  # 07-10 重跑覆盖，未翻倍

    def test_no_picks_writes_nothing(self):
        # 所有候选被过滤 → 无入选 → 不落盘
        bad = [{"code": "600099", "name": "ST股", "price": 3.0, "pe": -2.0}]
        r = recommend.run(date="2026-07-10", fetch_list=lambda: bad,
                          fetch_klines=_mock_fetch_klines())
        self.assertTrue(r["is_trading_day"])
        self.assertEqual(r["picks"], [])
        self.assertFalse(r["written"])
        self.assertEqual(os.path.getsize(self.tmp.name), 0)

    def test_write_false_is_dry_run(self):
        # write=False：只跑不落盘（dry-run）
        r = recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(),
                          fetch_klines=_mock_fetch_klines(), write=False)
        self.assertTrue(r["is_trading_day"])
        self.assertEqual(len(r["picks"]), 3)
        self.assertFalse(r["written"])
        self.assertEqual(os.path.getsize(self.tmp.name), 0)


class TestFormatReport(unittest.TestCase):
    def test_non_trading_mentions_risk_and_closed(self):
        txt = recommend.format_report(
            {"date": "2026-07-11", "is_trading_day": False, "picks": [], "written": False})
        self.assertIn("风险声明", txt)
        self.assertIn("非交易日", txt)

    def test_includes_picks_and_risk(self):
        picks = [{"code": "600001", "name": "科创先锋", "price": 25.0, "score": 88.5,
                  "reason": "均线多头;温和放量;MACD多头"}]
        txt = recommend.format_report(
            {"date": "2026-07-10", "is_trading_day": True, "picks": picks, "written": True})
        self.assertIn("风险声明", txt)
        self.assertIn("科创先锋", txt)
        self.assertIn("600001", txt)
        self.assertIn("88.5", txt)

    def test_no_picks_message(self):
        txt = recommend.format_report(
            {"date": "2026-07-10", "is_trading_day": True, "picks": [], "written": False})
        self.assertIn("风险声明", txt)
        self.assertIn("未筛选出", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)

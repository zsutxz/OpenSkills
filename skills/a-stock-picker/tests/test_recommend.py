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
from _fixtures import rising_klines as _rising_klines, snapshot_fixture  # noqa: E402


def _snapshot_fixture():
    """5 只正常股（入选）+ 2 只应被 filter_pool 剔除的票。"""
    return snapshot_fixture(include_filtered=True)


def _mock_fetch_klines():
    def _fk(code):
        return _rising_klines()
    return _fk


class TestRun(unittest.TestCase):
    def setUp(self):
        # 重定向落盘路径到临时文件，避免污染真实 docs/a-stock-picker/data/
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        self.tmp.close()
        self._orig = recommend.RECOMMEND_FILE
        recommend.RECOMMEND_FILE = self.tmp.name
        # md 镜像同样重定向到临时文件
        self.tmp_md = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8")
        self.tmp_md.close()
        self._orig_md = recommend.RECOMMEND_MD_FILE
        recommend.RECOMMEND_MD_FILE = self.tmp_md.name

    def tearDown(self):
        recommend.RECOMMEND_FILE = self._orig
        recommend.RECOMMEND_MD_FILE = self._orig_md
        for p in (self.tmp.name, self.tmp_md.name):
            if os.path.exists(p):
                os.remove(p)

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

    def test_writes_md_mirror_alongside_jsonl(self):
        # 双写：落盘 jsonl 的同时，用同源全部记录整体重写 md 镜像
        r = recommend.run(date="2026-07-10", fetch_list=lambda: _snapshot_fixture(),
                          fetch_klines=_mock_fetch_klines())
        self.assertTrue(r["written"])
        with open(self.tmp_md.name, encoding="utf-8") as f:
            md = f.read()
        self.assertIn("选股推荐历史", md)        # 文档标题
        self.assertIn("## 2026-07-10", md)       # 日期分节
        self.assertIn("风险声明", md)            # 顶部强制风险声明
        self.assertIn("科创先锋", md)            # 推荐股名流入 md
        self.assertIn("600001", md)              # 推荐代码流入 md


class TestSelectPicks(unittest.TestCase):
    def test_skips_candidate_on_fetch_failure(self):
        """单只取数失败（如退市票触发接口 501）被跳过，不中断整体选股。"""
        def fk(code):
            if code == "600002":
                raise RuntimeError("接口 501")
            return _rising_klines()
        picks = recommend.select_picks(_snapshot_fixture(), fk, top_n=3)
        codes = {p["code"] for p in picks}
        self.assertNotIn("600002", codes)   # 抛异常的候选被跳过
        self.assertEqual(len(picks), 3)      # 其余正常候选仍取满 Top3


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


class TestRenderMd(unittest.TestCase):
    def test_escapes_pipe_in_table_cell(self):
        """reason/name 中的管道符必须转义，否则破坏 Markdown 表格。"""
        import common
        md = common.render_recommendations_md([
            {"date": "2026-07-10", "code": "600001", "name": "A|B",
             "price": 10.0, "pe": 20.0, "score": 88.0, "reason": "x|y"}])
        self.assertIn("A\\|B", md)
        self.assertIn("x\\|y", md)

    def test_empty_records_has_risk_notice(self):
        import common
        md = common.render_recommendations_md([])
        self.assertIn("风险声明", md)
        self.assertIn("暂无推荐记录", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)

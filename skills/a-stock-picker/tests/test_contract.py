# -*- coding: utf-8 -*-
"""跨切片契约测试：recommend 落盘的记录必须能被 review 读回并回测。

防回归场景：若 _to_record 把字段 price 改名（如 entry_price），review.backtest_record
的 `entry is None` 兜底会把每条记录静默跳过，summarize 返回全 0 且不报错。本测试通过
recommend.run(write=True) → JSONL 文件 → review.run() 的真实往返，断言记录被成功复盘、
且 entry(price) 真实流入收益计算。运行：python tests/test_contract.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import recommend  # noqa: E402
import review  # noqa: E402
from _fixtures import rising_klines, snapshot_fixture  # noqa: E402


class TestRecommendReviewContract(unittest.TestCase):
    """recommend → JSONL → review 的端到端字段契约。"""

    def setUp(self):
        # recommend / review 各自从 common 导入 RECOMMEND_FILE，需同时指向同一临时文件
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
        self.tmp.close()
        self._orig_rec = recommend.RECOMMEND_FILE
        self._orig_rev = review.RECOMMEND_FILE
        recommend.RECOMMEND_FILE = self.tmp.name
        review.RECOMMEND_FILE = self.tmp.name
        # recommend 落盘时还会双写 md 镜像，同样重定向避免污染真实 recommendations.md
        self.tmp_md = tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8")
        self.tmp_md.close()
        self._orig_md = recommend.RECOMMEND_MD_FILE
        recommend.RECOMMEND_MD_FILE = self.tmp_md.name

    def tearDown(self):
        recommend.RECOMMEND_FILE = self._orig_rec
        review.RECOMMEND_FILE = self._orig_rev
        recommend.RECOMMEND_MD_FILE = self._orig_md
        for p in (self.tmp.name, self.tmp_md.name):
            if os.path.exists(p):
                os.remove(p)

    def test_recommend_output_is_reviewable(self):
        rec_date = "2026-07-10"  # 周五·交易日

        def fetch_klines(code):  # klines 末日取 rec_date 之后，使 T+1..T+10 在 review 回测时存在
            return rising_klines(end_date="2026-07-24")

        # 1) recommend 选股并落盘到 RECOMMEND_FILE
        res = recommend.run(date=rec_date, fetch_list=lambda: snapshot_fixture(n_normal=3),
                            fetch_klines=fetch_klines, write=True)
        self.assertTrue(res["is_trading_day"])
        self.assertTrue(res["written"])
        self.assertEqual(len(res["picks"]), 3)

        # 2) review 读回同一文件并回测（不传 records → 走默认 read_jsonl(RECOMMEND_FILE)）
        summary = review.run(fetch_klines=fetch_klines)
        self.assertEqual(summary["total"], 3)
        # 关键契约：记录未被 entry is None 静默跳过
        self.assertGreater(summary["reviewed"], 0)
        # entry(price) 真实流入收益计算 → T+1 / T+5 样本数 > 0
        self.assertGreater(summary["by_horizon"]["ret_1"]["count"], 0)
        self.assertGreater(summary["by_horizon"]["ret_5"]["count"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

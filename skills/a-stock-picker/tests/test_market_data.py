# -*- coding: utf-8 -*-
"""market_data 单元测试（slice-1 · 新浪列表 + 腾讯 K线）。

仅测纯解析/映射函数，网络集成见冒烟。运行：python tests/test_market_data.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from market_data import (  # noqa: E402
    tx_symbol,
    _parse_tx_kline_item,
    _parse_sina_item,
)


class TestTxSymbol(unittest.TestCase):
    def test_shanghai_main(self):
        self.assertEqual(tx_symbol("600519"), "sh600519")  # 沪市主板

    def test_star(self):
        self.assertEqual(tx_symbol("688981"), "sh688981")  # 科创板

    def test_shenzhen_main(self):
        self.assertEqual(tx_symbol("000001"), "sz000001")  # 深市主板

    def test_chinext(self):
        self.assertEqual(tx_symbol("300750"), "sz300750")  # 创业板


class TestParseTxKlineItem(unittest.TestCase):
    def test_standard_row(self):
        row = ["2026-07-10", "1182.200", "1204.980", "1204.980", "1170.280", "52213.000"]
        d = _parse_tx_kline_item(row)
        self.assertEqual(d["date"], "2026-07-10")
        self.assertAlmostEqual(d["open"], 1182.2)
        self.assertAlmostEqual(d["close"], 1204.98)
        self.assertAlmostEqual(d["high"], 1204.98)
        self.assertAlmostEqual(d["low"], 1170.28)
        self.assertEqual(d["volume"], 52213.0)

    def test_none_row(self):
        self.assertIsNone(_parse_tx_kline_item(None))

    def test_short_row(self):
        self.assertIsNone(_parse_tx_kline_item(["2026-07-10"]))  # 字段不足

    def test_bad_value(self):
        self.assertIsNone(_parse_tx_kline_item(["x", "a", "b", "c", "d", "e"]))


class TestParseSinaItem(unittest.TestCase):
    def test_normal(self):
        raw = {"code": "600519", "name": "贵州茅台", "trade": "1204.98",
               "changepercent": "1.92", "per": "28.5", "pb": "9.1", "mktcap": "2100000"}
        d = _parse_sina_item(raw)
        self.assertEqual(d["code"], "600519")
        self.assertEqual(d["name"], "贵州茅台")
        self.assertAlmostEqual(d["price"], 1204.98)
        self.assertAlmostEqual(d["pct"], 1.92)
        self.assertAlmostEqual(d["pe"], 28.5)

    def test_loss_keeps_negative_pe(self):
        # 亏损股市盈率为负，保留交由策略层判断剔除
        raw = {"code": "000001", "name": "某亏损股", "trade": "10.0", "per": "-5.2"}
        d = _parse_sina_item(raw)
        self.assertAlmostEqual(d["pe"], -5.2)

    def test_missing_fields(self):
        raw = {"code": "600000", "name": "浦发银行"}
        d = _parse_sina_item(raw)
        self.assertIsNone(d["price"])
        self.assertIsNone(d["pe"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

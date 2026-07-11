# -*- coding: utf-8 -*-
"""trading_calendar 单元测试（slice-1 · TDD 红阶段先行）。

运行：python tests/test_trading_calendar.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from trading_calendar import is_trading_day, last_trading_day  # noqa: E402


class TestTradingCalendar(unittest.TestCase):
    def test_weekday_is_trading_day(self):
        # 2026-07-10 是周五
        self.assertTrue(is_trading_day("2026-07-10"))

    def test_weekend_not_trading_day(self):
        self.assertFalse(is_trading_day("2026-07-11"))  # 周六
        self.assertFalse(is_trading_day("2026-07-12"))  # 周日

    def test_holiday_not_trading_day(self):
        self.assertFalse(is_trading_day("2026-01-01"))  # 元旦
        self.assertFalse(is_trading_day("2026-10-01"))  # 国庆

    def test_last_trading_day_from_weekend(self):
        # 周六 2026-07-11 → 最近交易日是周五 07-10
        self.assertEqual(last_trading_day("2026-07-11"), "2026-07-10")

    def test_last_trading_day_from_monday(self):
        # 周一 2026-07-13 → 最近交易日是上周五 07-10
        self.assertEqual(last_trading_day("2026-07-13"), "2026-07-10")


if __name__ == "__main__":
    unittest.main(verbosity=2)

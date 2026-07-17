# -*- coding: utf-8 -*-
"""slice-6 文档结构校验：SKILL.md frontmatter 合法性 + 触发词 + 风险声明，
README 含 Windows/Linux 定时配置。运行：python tests/test_skill_docs.py
"""
import os
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL_MD = os.path.join(SKILL_DIR, "SKILL.md")
README_MD = os.path.join(SKILL_DIR, "README.md")


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frontmatter(text):
    """返回 (frontmatter_block, body)；文件不以 --- 开头则 frontmatter 为空。"""
    if not text.startswith("---"):
        return "", text
    end = text.find("\n---", 3)
    if end < 0:
        return "", text
    return text[3:end], text[end + 4:]


class TestSkillFrontmatter(unittest.TestCase):
    def setUp(self):
        self.fm, self.body = _frontmatter(_read(SKILL_MD))

    def test_has_required_keys(self):
        for key in ("name:", "description:", "allowed-tools:"):
            self.assertIn(key, self.fm, "frontmatter 缺少 %s" % key)

    def test_name_is_a_stock_picker(self):
        self.assertIn("name: a-stock-picker", self.fm)

    def test_description_covers_triggers(self):
        # description 必须覆盖选股/推荐/复盘等触发词，保证自动激活
        self.assertIn("推荐", self.fm)
        self.assertIn("复盘", self.fm)
        self.assertIn("选股", self.fm)

    def test_allowed_tools_can_run_scripts(self):
        # 运行 python 脚本至少需要 Bash
        self.assertIn("Bash", self.fm)


class TestSkillBody(unittest.TestCase):
    def setUp(self):
        _, self.body = _frontmatter(_read(SKILL_MD))

    def test_has_risk_notice(self):
        self.assertIn("风险声明", self.body)

    def test_instructs_scripts(self):
        self.assertIn("recommend.py", self.body)
        self.assertIn("review.py", self.body)

    def test_documents_both_triggers(self):
        # 使用指引含手动 + 定时两种触发
        self.assertIn("手动", self.body)
        self.assertIn("定时", self.body)


class TestReadme(unittest.TestCase):
    def setUp(self):
        self.text = _read(README_MD)

    def test_has_windows_scheduler(self):
        self.assertIn("任务计划", self.text)

    def test_has_linux_crontab(self):
        self.assertIn("crontab", self.text)

    def test_has_risk_notice(self):
        self.assertIn("风险声明", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""公共工具：风险声明常量、路径、收益率、JSONL 读写、格式化。

所有对外输出（推荐、复盘报告）顶部必须标注 RISK_NOTICE。
"""
import json
import os

# 所有对外输出顶部强制标注的风险声明
RISK_NOTICE = (
    "⚠️ 风险声明：以下内容基于公开行情的量化筛选结果，仅供信息参考，"
    "不构成任何投资建议。股市有风险，买卖决策与盈亏由使用者自行承担。"
)

# skill 根目录：scripts/ 的上一级，即 skills/a-stock-picker/
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 项目根目录（仓库/插件根）：skills/a-stock-picker/ 的上两级，仍按 __file__ 解析，与运行目录无关
PROJECT_ROOT = os.path.dirname(os.path.dirname(SKILL_DIR))
# 运行时产物根：遵循本仓库约定 docs/<skill名>/（docs/ 已在 .gitignore，本地产物不进仓库）
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs", "a-stock-picker")
DATA_DIR = os.path.join(OUTPUT_DIR, "data")
REPORTS_DIR = os.path.join(OUTPUT_DIR, "reports")
RECOMMEND_FILE = os.path.join(DATA_DIR, "recommendations.jsonl")


def fmt_pct(ratio, width=7):
    """小数收益率 → 百分号字符串，如 0.0234 → '+2.34%'。None → 'N/A'。"""
    if ratio is None:
        return "  N/A "
    sign = "+" if ratio >= 0 else ""
    return f"{sign}{ratio * 100:>{width - 2}.2f}%"


def calc_return(entry, exit_):
    """收益率 = (exit-entry)/entry；entry/exit 为 0 或 None 返回 None。"""
    if not entry or not exit_:
        return None
    return (exit_ - entry) / entry


def append_jsonl(path, record):
    """追加一条 JSON 记录到 jsonl 文件（自动建父目录）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path):
    """读取整个 jsonl 文件为 list[dict]，文件不存在返回 []。"""
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def rewrite_jsonl(path, records):
    """整文件覆盖写（用于同日去重：读出→替换当日→回写）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)

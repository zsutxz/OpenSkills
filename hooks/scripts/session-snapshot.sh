#!/usr/bin/env bash
# session-snapshot.sh — Claude 退出时（SessionEnd）写会话指针快照，供"继续上一次"恢复
# 由 hooks.json 中的 SessionEnd hook 调用
# 输入: stdin JSON（session_id / cwd / transcript_path / reason）
# 输出: 无（SessionEnd 的 stdout 被忽略）；仅写盘
# 设计原则：轻量、绝不阻断退出。任何意外都静默退出 0，失败最多只是"没留下快照"，绝不影响 Claude 退出。
# 只写指针（session_id / cwd / transcript_path / git 摘要 / 时间），零 transcript 解析——
# 真正"读对话、判进度"的重活交给恢复时的 session-resume 技能（有模型智能 + Read 工具）。

set -uo pipefail   # 故意不用 -e：本脚本"尽力而为"，单条命令失败也不该非零退出

INPUT=$(cat)

# 从 stdin JSON 提取字符串字段（grep -oP 在 Git Bash 可用），不做完整 JSON 解析
extract() {
  printf '%s' "$INPUT" | grep -oP "\"$1\"\s*:\s*\"[^\"]*\"" 2>/dev/null | head -1 \
    | sed "s/.*\"$1\"\s*:\s*\"//; s/\"$//" || true
}

CWD=$(extract cwd)
TRANSCRIPT=$(extract transcript_path)
SESSION_ID=$(extract session_id)

# Windows 路径统一成正斜杠，规避反斜杠在 JSON / 命令行里的转义问题
CWD=${CWD//\\//}
TRANSCRIPT=${TRANSCRIPT//\\//}

# 拿不到 cwd 就放弃（没有锚点无法定位项目根）
[ -z "$CWD" ] && exit 0

# 定位项目根：git 根优先，失败回退到 cwd
ROOT=$(cd "$CWD" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$CWD")
mkdir -p "$ROOT/.session-resume" 2>/dev/null || exit 0

# git 摘要（失败优雅降级为空 / 0）
BRANCH=$(cd "$CWD" 2>/dev/null && git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '')
DIRTY=$(cd "$CWD" 2>/dev/null && git status --short 2>/dev/null | wc -l | tr -d ' ' || printf '0')
DIRTY=${DIRTY:-0}

# 原子写：临时文件 + mv，防半写损坏（与 project-orchestrator 的写法一致）
TMP=$(mktemp 2>/dev/null || printf '%s/.sess-snap-%s.tmp' "${TMPDIR:-/tmp}" "$RANDOM")
cat > "$TMP" <<JSON
{
  "schema_version": "1",
  "session_id": "${SESSION_ID}",
  "cwd": "${CWD}",
  "project_root": "${ROOT}",
  "transcript_path": "${TRANSCRIPT}",
  "saved_at": "$(date -Iseconds)",
  "git": {
    "branch": "${BRANCH}",
    "uncommitted_files": ${DIRTY}
  }
}
JSON
mv -f "$TMP" "$ROOT/.session-resume/last-session.json" 2>/dev/null || true

exit 0

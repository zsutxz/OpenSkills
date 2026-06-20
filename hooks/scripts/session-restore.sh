#!/usr/bin/env bash
# session-restore.sh — 会话启动时（SessionStart）检测上次未完成会话，注入提示让用户选择是否恢复
# 由 hooks.json 中的 SessionStart hook 调用
# 输入: stdin JSON（session_id / cwd / transcript_path / source）
# 输出: JSON（hookSpecificOutput.additionalContext 注入到 Claude 上下文）
# 设计：纯 bash 只负责「检测快照 + 注入指针提示」；判断「有无未完成任务、内容是什么」
#       交给模型读 transcript 完成——避免对已完成的会话误打扰。

set -uo pipefail   # 故意不用 -e：本脚本"尽力而为"，绝不阻断启动

INPUT=$(cat)

extract() {
  printf '%s' "$INPUT" | grep -oP "\"$1\"\s*:\s*\"[^\"]*\"" 2>/dev/null | head -1 \
    | sed "s/.*\"$1\"\s*:\s*\"//; s/\"$//" || true
}

CWD=$(extract cwd)
SOURCE=$(extract source)
[ -z "$CWD" ] && exit 0   # 无锚点，放弃

# 只在「新会话」启动时提示；resume / clear / compact 不打扰
[ "$SOURCE" = "startup" ] || exit 0

# 定位项目根
ROOT=$(cd "$CWD" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$CWD")
SNAPSHOT="$ROOT/.session-resume/last-session.json"
[ -f "$SNAPSHOT" ] || exit 0   # 无快照，无可恢复

# 从快照提取字段（简单 grep，失败留空）
field() {
  grep -oP "\"$1\"\s*:\s*(\"[^\"]*\"|[0-9]+)" "$SNAPSHOT" 2>/dev/null | head -1 \
    | sed "s/.*\"$1\"\s*:\s*//" | sed 's/^"//; s/"$//' || true
}
SAVED_AT=$(field saved_at)
BRANCH=$(field branch)
UNCOMMITTED=$(field uncommitted_files)
TRANSCRIPT=$(field transcript_path)
TRANSCRIPT=${TRANSCRIPT//\\//}   # Windows 路径统一成正斜杠
UNCOMMITTED=${UNCOMMITTED:-0}

# 组装提示（内部刻意不用反引号和双引号，避免 bash 把它当命令替换 / 提前闭合字符串）
MSG="[会话恢复] 检测到上次会话可能未正常收尾：
- 上次结束时间：${SAVED_AT:-未知}
- 分支：${BRANCH:-未知}　未提交文件数：${UNCOMMITTED}
- 上次会话 transcript 路径：${TRANSCRIPT:-无}

请你立即：
1. 用 Bash 运行 tail -n 30 加上面 transcript 路径（路径含空格或反斜杠时务必用引号包裹），或用 Read 工具读取该 JSONL 文件的尾部，理解上次在做什么、有无未完成项（最后一条 TodoWrite 里 status 为 pending 或 in_progress 的项，或明显被中断的任务）。
2. 若确有未完成任务，用 AskUserQuestion 询问用户如何处理，给出三个选项：恢复上次任务（按 session-resume 技能从断点续跑）、只看看上次进度（复述上次做到哪、先不动手）、开始新任务忽略上次（不恢复）。
3. 若上次任务已完成、无遗留，则不要打扰用户，直接等待用户的新指令。
一切以上次 transcript 的实际内容为准，不要臆测。"

# 输出 JSON（additionalContext 注入提示）。jq 在则安全转义，否则降级手工转义。
if command -v jq >/dev/null 2>&1; then
  jq -nc --arg ctx "$MSG" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$ctx}}'
else
  ESC=$(printf '%s' "$MSG" | sed 's/\\/\\\\/g; s/"/\\"/g' | awk 'BEGIN{ORS=""}{if(NR>1)printf "\\n"; print}')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' "$ESC"
fi

exit 0

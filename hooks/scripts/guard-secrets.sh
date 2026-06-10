#!/usr/bin/env bash
# guard-secrets.sh — 在写入文件前检查是否包含敏感信息
# 由 hooks.json 中的 PreToolUse hook 调用
# 输入: JSON 格式的工具调用参数（通过 stdin）
# 输出: JSON 格式的 hook 响应（通过 stdout），或无输出表示允许

set -euo pipefail

# 读取工具输入 JSON
TOOL_INPUT=$(cat)

# 提取 content/new_string 字段（实际写入的内容）
CONTENT=$(echo "$TOOL_INPUT" | grep -oP '"(content|new_string)"\s*:\s*"[^"]*"' 2>/dev/null || echo "")

if [ -z "$CONTENT" ]; then
  # 没有内容字段可检查，允许操作
  exit 0
fi

# 敏感信息模式列表
SECRET_PATTERNS=(
  'AKIA[0-9A-Z]{16}'
  '-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'
  'sk-[a-zA-Z0-9]{20,}'
  'sk_live_[a-zA-Z0-9]{24,}'
  'ghp_[a-zA-Z0-9]{36}'
  'gho_[a-zA-Z0-9]{36}'
  'xox[bpas]-[a-zA-Z0-9-]{10,}'
  '(password|passwd|secret|token)\s*[:=]\s*["\x27][^"\x27]{8,}["\x27]'
)

for pattern in "${SECRET_PATTERNS[@]}"; do
  if echo "$CONTENT" | grep -qE "$pattern" 2>/dev/null; then
    # 输出警告 JSON，要求用户确认
    cat << 'EOF'
{
  "decision": "ask",
  "reason": "⚠️ 检测到可能的敏感信息（API 密钥、密码或私钥）。确认是否要写入此内容？如果是测试数据或示例配置，可以继续。"
}
EOF
    exit 0
  fi
done

# 未发现敏感信息，允许操作
exit 0

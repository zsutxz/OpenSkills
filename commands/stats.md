---
description: 分析代码库统计信息，包括语言分布、文件数量、代码行数、目录结构等
allowed-tools: Bash, Read, Glob, Grep
argument-hint: [path]
---

# /open-skills:stats — 代码库统计分析

分析指定代码库（默认为当前目录）的统计信息。

## 步骤

1. **确定目标路径**：如果提供了 `$ARGUMENTS`，分析指定路径；否则分析当前工作目录。

2. **收集基础数据**：使用 Bash 运行以下命令收集信息：

   ```bash
   # 文件总数和类型分布（排除 node_modules, .git, dist, build, vendor, __pycache__）
   find <path> -type f \
     -not -path '*/node_modules/*' \
     -not -path '*/.git/*' \
     -not -path '*/dist/*' \
     -not -path '*/build/*' \
     -not -path '*/vendor/*' \
     -not -path '*/__pycache__/*' \
     -not -path '*/.next/*' \
     -not -path '*/target/*' \
     | sed 's/.*\.//' | sort | uniq -c | sort -rn
   ```

3. **代码行数统计**：按语言统计代码行数：
   ```bash
   # 按 .py, .js, .ts, .go, .java, .rs 等扩展名分别统计
   find <path> -name "*.py" -not -path '*/.*' | xargs wc -l 2>/dev/null | tail -1
   ```

4. **目录结构概览**：展示前 3 层目录结构（排除隐藏目录和依赖目录）。

5. **Git 统计**（如果是 git 仓库）：
   - 总提交数
   - 贡献者数量
   - 最近 7 天提交频率
   - 最近修改的 10 个文件

6. **大文件排行**：找出体积最大的 10 个源码文件。

## 输出格式

使用以下模板输出报告：

```
📊 代码库统计报告
━━━━━━━━━━━━━━━━━

📁 基本信息
  路径: ...
  总文件数: ...

🗂️ 语言分布
  | 语言 | 文件数 | 代码行数 | 占比 |
  |------|--------|----------|------|

📂 目录结构
  [树形结构]

📝 Git 活跃度（如适用）
  总提交: ...
  贡献者: ...
  最近 7 天提交: ...

📋 最大的文件 TOP 10
  | 文件 | 大小 |
  |------|------|

💡 总结
  [1-3 句话概述代码库特征]
```

## 注意事项

- 排除 node_modules、.git、dist、build、vendor、__pycache__、.next、target 等目录
- 使用 pipe 串联命令以提高效率，避免逐文件操作
- 输出使用中文
- 如果路径不存在，提示用户检查路径

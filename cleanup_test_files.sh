#!/bin/bash
# 清理测试文件脚本 (优化版)

# --- 配置 ---
# 要清理的文件/模式列表
# 注意：已将脚本自身 "cleanup_test_files.sh" 从列表中移除
TEST_FILES=(
    "test_formatter.py"
    "test_data_flow.py"
    "test_*.py"
    "verify_system.py"
    "full_test.sh"
    "test_complete_system.py"
)

# --- 脚本主逻辑 ---
set -e # 如果任何命令失败，立即退出脚本

# 检查是否为演习模式
DRY_RUN=false
if [ "$1" = "--dry-run" ]; then
    DRY_RUN=true
    echo "=========================================="
    echo "演习模式 (Dry Run) - 不会实际删除文件"
    echo "=========================================="
else
    echo "=========================================="
    echo "清理测试文件"
    echo "=========================================="
fi
echo ""

# 询问用户是否要保留 test_complete_system.py
KEEP_MAIN_TEST=true
read -p "是否保留 test_complete_system.py? (y/n, 默认y): " keep_main
if [[ "$keep_main" == "n" || "$keep_main" == "N" ]]; then
    KEEP_MAIN_TEST=false
fi
echo ""

# 准备要删除的文件列表
FILES_TO_DELETE=()
echo "以下文件将被处理："
for pattern in "${TEST_FILES[@]}"; do
    # 特殊处理 test_complete_system.py 的保留逻辑
    if [ "$pattern" = "test_complete_system.py" ] && [ "$KEEP_MAIN_TEST" = true ]; then
        continue
    fi

    # 使用 find 命令安全地查找匹配的文件，避免空格等问题
    # -maxdepth 1 确保只在当前目录查找
    while IFS= read -r -d $'\0' file; do
        FILES_TO_DELETE+=("$file")
        echo "  - $file"
    done < <(find . -maxdepth 1 -name "$pattern" -print0 2>/dev/null)
done

# 如果没有文件需要删除，则退出
if [ ${#FILES_TO_DELETE[@]} -eq 0 ]; then
    echo "没有找到需要清理的文件。"
    exit 0
fi

echo ""

# 演习模式的逻辑
if [ "$DRY_RUN" = true ]; then
    echo "演习结束。如果列表正确，请不带 --dry-run 参数重新运行以实际删除。"
    exit 0
fi

# 实际执行前的最后确认
read -p "确认要删除以上 ${#FILES_TO_DELETE[@]} 个文件吗? (y/n): " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "操作已取消。"
    exit 1
fi

echo ""
echo "开始清理 (使用 git rm)..."

# 使用 git rm 清理文件
CLEANED=0
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -f "$file" ]; then
        # 使用 git rm 并忽略未被git跟踪的文件所产生的错误
        if git rm -f "$file" > /dev/null 2>&1; then
            echo "  ✓ 已通过 git rm 删除: $file"
            CLEANED=$((CLEANED + 1))
        else
            # 如果 git rm 失败（例如文件未被跟踪），尝试普通 rm
            rm -f "$file"
            echo "  ✓ 已通过 rm 删除 (文件未被Git跟踪): $file"
        fi
    fi
done

echo ""
echo "=========================================="
echo "清理完成！处理了 $CLEANED 个文件。"
echo "这些删除操作已被Git暂存，请使用 'git commit' 来提交。"
echo "=========================================="
echo ""
echo "保留的文件（可能）:"
if [ "$KEEP_MAIN_TEST" = true ]; then
    echo "  - test_complete_system.py (整合了所有测试功能)"
fi
echo "  - TESTING_GUIDE.md (测试指南文档)"
echo "  - cleanup_test_files.sh (本脚本)"
echo ""
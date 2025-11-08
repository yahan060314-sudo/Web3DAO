#!/bin/bash
# 清理测试文件脚本

echo "=========================================="
echo "清理测试文件"
echo "=========================================="
echo ""

# 要清理的文件列表
TEST_FILES=(
    "test_formatter.py"
    "test_data_flow.py"
    "test_*.py"
    "verify_system.py"
    "full_test.sh"
    "cleanup_test_files.sh"
    "test_complete_system.py"  # 这个是我们新创建的，但用户可能想保留
)

# 询问用户是否要保留test_complete_system.py
KEEP_MAIN_TEST=true

echo "以下测试文件将被清理："
for file in "${TEST_FILES[@]}"; do
    if [ "$file" != "test_complete_system.py" ]; then
        if ls $file 1> /dev/null 2>&1; then
            echo "  - $file"
        fi
    fi
done

echo ""
read -p "是否保留 test_complete_system.py? (y/n, 默认y): " keep_main
if [ "$keep_main" = "n" ] || [ "$keep_main" = "N" ]; then
    KEEP_MAIN_TEST=false
fi

echo ""
echo "开始清理..."

# 清理文件
CLEANED=0
for pattern in "${TEST_FILES[@]}"; do
    if [ "$pattern" = "test_complete_system.py" ] && [ "$KEEP_MAIN_TEST" = true ]; then
        continue
    fi
    
    for file in $pattern; do
        if [ -f "$file" ]; then
            rm -f "$file"
            echo "  ✓ 已删除: $file"
            CLEANED=$((CLEANED + 1))
        fi
    done
done

echo ""
echo "=========================================="
echo "清理完成！删除了 $CLEANED 个文件"
echo "=========================================="
echo ""
echo "保留的文件："
echo "  - test_complete_system.py (整合了所有测试功能)"
echo "  - TESTING_GUIDE.md (测试指南文档)"
echo ""
echo "使用方法："
echo "  python test_complete_system.py          # 标准测试"
echo "  python test_complete_system.py --quick  # 快速测试"
echo "  python test_complete_system.py --full   # 完整测试"


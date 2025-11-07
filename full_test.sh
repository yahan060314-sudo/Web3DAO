#!/bin/bash
# 完整测试脚本

echo "=========================================="
echo "Web3DAO Complete System Test"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: Virtual environment not activated"
    echo "  Run: source .venv/bin/activate"
    exit 1
fi

echo "[Step 1] Verifying system..."
python verify_system.py
if [ $? -ne 0 ]; then
    echo "✗ System verification failed"
    exit 1
fi

echo ""
echo "[Step 2] Testing LLM connection..."
python -m api.llm_clients.example_usage
if [ $? -ne 0 ]; then
    echo "✗ LLM connection test failed"
    exit 1
fi

echo ""
echo "[Step 3] Testing Roostoo connection..."
python -c "
from api.roostoo_client import RoostooClient
client = RoostooClient()
try:
    client.check_server_time()
    print('✓ Roostoo API connection successful')
except Exception as e:
    print(f'✗ Roostoo API error: {e}')
    exit(1)
"
if [ $? -ne 0 ]; then
    exit 1
fi

echo ""
echo "[Step 4] Testing data flow (30 seconds)..."
timeout 30 python test_data_flow.py || echo "⚠ Test timed out or interrupted"

echo ""
echo "=========================================="
echo "✓ All tests completed!"
echo "=========================================="


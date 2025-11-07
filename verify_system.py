#!/usr/bin/env python3
"""系统验证脚本"""
import sys
import os
from pathlib import Path

checks = []
errors = []

# 1. 检查Python版本
import sys
if sys.version_info >= (3, 11):
    checks.append("✓ Python version: " + sys.version.split()[0])
else:
    errors.append("✗ Python version too old (need 3.11+)")

# 2. 检查依赖
try:
    import requests
    checks.append("✓ requests installed")
except ImportError:
    errors.append("✗ requests not installed")

try:
    import dotenv
    checks.append("✓ python-dotenv installed")
except ImportError:
    errors.append("✗ python-dotenv not installed")

# 3. 检查配置文件
env_file = Path(".env")
if env_file.exists():
    checks.append("✓ .env file exists")
    # 检查关键配置
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("DEEPSEEK_API_KEY"):
        checks.append("✓ DEEPSEEK_API_KEY configured")
    else:
        errors.append("✗ DEEPSEEK_API_KEY not set")
    
    if os.getenv("ROOSTOO_API_KEY"):
        checks.append("✓ ROOSTOO_API_KEY configured")
    else:
        errors.append("✗ ROOSTOO_API_KEY not set")
else:
    errors.append("✗ .env file not found")

# 4. 检查模块导入
try:
    from api.llm_clients.factory import get_llm_client
    checks.append("✓ LLM clients importable")
except Exception as e:
    errors.append(f"✗ LLM clients import error: {e}")

try:
    from api.roostoo_client import RoostooClient
    checks.append("✓ Roostoo client importable")
except Exception as e:
    errors.append(f"✗ Roostoo client import error: {e}")

try:
    from api.agents.manager import AgentManager
    from api.agents.market_collector import MarketDataCollector
    from api.agents.prompt_manager import PromptManager
    checks.append("✓ Agent modules importable")
except Exception as e:
    errors.append(f"✗ Agent modules import error: {e}")

# 5. 检查prompts文件夹
prompts_dir = Path("prompts")
if prompts_dir.exists():
    checks.append("✓ prompts directory exists")
    if (prompts_dir / "natural_language_prompt.txt").exists():
        checks.append("✓ natural_language_prompt.txt exists")
    else:
        errors.append("⚠ natural_language_prompt.txt not found (optional)")
else:
    errors.append("⚠ prompts directory not found (optional)")

# 输出结果
print("=" * 60)
print("System Verification")
print("=" * 60)
print("\nChecks:")
for check in checks:
    print(f"  {check}")

if errors:
    print("\nErrors/Warnings:")
    for error in errors:
        print(f"  {error}")
else:
    print("\n✓ All checks passed!")

print("\n" + "=" * 60)

if errors:
    sys.exit(1)
else:
    sys.exit(0)


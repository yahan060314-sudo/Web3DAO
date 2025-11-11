#!/usr/bin/env python3
"""
检查Roostoo API URL配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

print("=" * 60)
print("Roostoo API URL 配置检查")
print("=" * 60)
print()

# 检查环境变量
env_url = os.getenv("ROOSTOO_API_URL")
default_url = "https://mock-api.roostoo.com"

print(f"环境变量 ROOSTOO_API_URL: {env_url if env_url else '未设置'}")
print(f"代码默认 URL: {default_url}")
print()

# 确定实际使用的URL
actual_url = env_url if env_url else default_url

print(f"实际使用的 URL: {actual_url}")
print()

# 检查URL类型
if "mock" in actual_url.lower():
    print("✓ 使用 Mock API (测试环境)")
    print("  这将使用模拟API，不会真正下单")
elif "api.roostoo.com" in actual_url and "mock" not in actual_url.lower():
    print("⚠️ 使用真实 API (生产环境)")
    print("  这将使用真实API，会真正下单")
    print("  如果只想测试，请在 .env 文件中设置:")
    print(f"  ROOSTOO_API_URL=https://mock-api.roostoo.com")
else:
    print(f"⚠️ 使用自定义 URL: {actual_url}")

print()
print("=" * 60)
print("如何修改 URL")
print("=" * 60)
print()
print("方法1: 在 .env 文件中设置（推荐）")
print("  打开 .env 文件，添加或修改:")
print(f"  ROOSTOO_API_URL=https://mock-api.roostoo.com")
print()
print("方法2: 在代码中直接设置")
print("  from api.roostoo_client import RoostooClient")
print(f"  client = RoostooClient(base_url='https://mock-api.roostoo.com')")
print()
print("=" * 60)


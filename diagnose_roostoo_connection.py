#!/usr/bin/env python3
"""
Roostoo API连接诊断脚本
帮助诊断和解决Roostoo API连接问题
"""
import sys
import os
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import requests
from api.roostoo_client import RoostooClient


def test_network_connectivity():
    """测试网络连接"""
    print("=" * 80)
    print("1. 网络连接测试")
    print("=" * 80)
    
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    base_domain = api_url.replace("https://", "").replace("http://", "").split("/")[0]
    
    print(f"测试连接到: {base_domain}")
    
    # 测试1: DNS解析
    print("\n[1.1] DNS解析测试...")
    try:
        import socket
        ip = socket.gethostbyname(base_domain)
        print(f"   ✓ DNS解析成功: {base_domain} -> {ip}")
    except Exception as e:
        print(f"   ✗ DNS解析失败: {e}")
        return False
    
    # 测试2: HTTP连接
    print("\n[1.2] HTTP连接测试...")
    try:
        response = requests.get(f"https://{base_domain}", timeout=10)
        print(f"   ✓ HTTP连接成功: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"   ⚠️ HTTP连接超时（可能被防火墙阻止）")
    except requests.exceptions.ConnectionError as e:
        print(f"   ✗ HTTP连接失败: {e}")
        return False
    except Exception as e:
        print(f"   ⚠️ HTTP连接异常: {e}")
    
    return True


def test_api_endpoint():
    """测试API端点"""
    print("\n" + "=" * 80)
    print("2. API端点测试")
    print("=" * 80)
    
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    endpoint = f"{api_url}/v3/serverTime"
    
    print(f"测试端点: {endpoint}")
    
    # 测试不同超时时间
    timeouts = [10, 30, 60]
    
    for timeout in timeouts:
        print(f"\n[2.{timeouts.index(timeout) + 1}] 测试超时时间: {timeout}秒...")
        try:
            start_time = time.time()
            response = requests.get(endpoint, timeout=timeout)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                print(f"   ✓ 连接成功 (耗时: {elapsed:.2f}秒)")
                try:
                    data = response.json()
                    print(f"   ✓ 响应数据: {data}")
                    return True
                except Exception as e:
                    print(f"   ⚠️ 响应格式错误: {e}")
                    return False
            else:
                print(f"   ⚠️ HTTP状态码: {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"   ✗ 连接超时 ({timeout}秒)")
        except requests.exceptions.ConnectionError as e:
            print(f"   ✗ 连接错误: {e}")
        except Exception as e:
            print(f"   ✗ 异常: {e}")
    
    return False


def test_roostoo_client():
    """测试Roostoo客户端"""
    print("\n" + "=" * 80)
    print("3. Roostoo客户端测试")
    print("=" * 80)
    
    # 检查API凭证
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    
    print(f"API URL: {api_url}")
    print(f"API Key: {'✓ 已配置' if api_key else '✗ 未配置'}")
    print(f"Secret Key: {'✓ 已配置' if secret_key else '✗ 未配置'}")
    
    if not api_key or not secret_key:
        print("\n   ✗ API凭证未配置，请检查.env文件")
        return False
    
    try:
        # 创建客户端
        print("\n[3.1] 创建Roostoo客户端...")
        client = RoostooClient()
        print("   ✓ 客户端创建成功")
        
        # 测试服务器时间（不需要认证）
        print("\n[3.2] 测试服务器时间接口（无需认证）...")
        try:
            server_time = client.check_server_time(timeout=60.0)
            print(f"   ✓ 服务器时间获取成功: {server_time}")
        except Exception as e:
            print(f"   ✗ 服务器时间获取失败: {e}")
            return False
        
        # 测试获取交易所信息（不需要认证）
        print("\n[3.3] 测试交易所信息接口（无需认证）...")
        try:
            exchange_info = client.get_exchange_info(timeout=60.0)
            print(f"   ✓ 交易所信息获取成功")
            if isinstance(exchange_info, dict):
                print(f"   响应键: {list(exchange_info.keys())[:5]}")
        except Exception as e:
            print(f"   ⚠️ 交易所信息获取失败: {e}")
        
        # 测试获取市场数据（需要时间戳检查）
        print("\n[3.4] 测试市场数据接口（需要时间戳检查）...")
        try:
            ticker = client.get_ticker(pair="BTC/USD", timeout=60.0)
            print(f"   ✓ 市场数据获取成功")
            if isinstance(ticker, dict):
                print(f"   响应键: {list(ticker.keys())[:5]}")
        except Exception as e:
            print(f"   ⚠️ 市场数据获取失败: {e}")
        
        # 测试获取余额（需要完整认证）
        print("\n[3.5] 测试余额接口（需要完整认证）...")
        try:
            balance = client.get_balance(timeout=60.0)
            print(f"   ✓ 余额获取成功")
            if isinstance(balance, dict):
                print(f"   响应键: {list(balance.keys())[:5]}")
        except Exception as e:
            print(f"   ⚠️ 余额获取失败: {e}")
            print(f"   提示: 这可能是API认证问题，或比赛还未开始")
        
        return True
        
    except Exception as e:
        print(f"\n   ✗ 客户端测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Roostoo API连接诊断工具")
    print("=" * 80)
    print()
    
    results = []
    
    # 测试1: 网络连接
    results.append(("网络连接", test_network_connectivity()))
    
    # 测试2: API端点
    results.append(("API端点", test_api_endpoint()))
    
    # 测试3: Roostoo客户端
    results.append(("Roostoo客户端", test_roostoo_client()))
    
    # 总结
    print("\n" + "=" * 80)
    print("诊断结果总结")
    print("=" * 80)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print("\n" + "=" * 80)
    print("建议")
    print("=" * 80)
    
    if not results[0][1]:
        print("1. 网络连接失败:")
        print("   - 检查网络连接")
        print("   - 检查DNS设置")
        print("   - 检查防火墙/代理设置")
        print("   - 尝试使用VPN或更换网络")
    
    if not results[1][1]:
        print("2. API端点测试失败:")
        print("   - 检查API URL是否正确")
        print("   - 检查API服务器是否可用")
        print("   - 尝试增加超时时间")
        print("   - 检查防火墙是否阻止HTTPS连接")
    
    if not results[2][1]:
        print("3. Roostoo客户端测试失败:")
        print("   - 检查API凭证是否正确")
        print("   - 检查API URL是否正确")
        print("   - 检查网络连接")
        print("   - 检查API服务器状态")
        print("   - 如果使用真实API，确保比赛已开始")
    
    if all(result for _, result in results):
        print("✓ 所有测试通过！Roostoo API连接正常。")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


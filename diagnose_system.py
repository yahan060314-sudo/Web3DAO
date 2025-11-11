#!/usr/bin/env python3
"""
系统诊断脚本 - 检查所有可能导致失败的因素
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

def check_env_file():
    """检查.env文件"""
    print("=" * 80)
    print("检查1: .env文件")
    print("=" * 80)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env文件不存在")
        print("   请创建.env文件并配置必要的环境变量")
        return False
    
    print("✅ .env文件存在")
    return True

def check_roostoo_config():
    """检查Roostoo API配置"""
    print("\n" + "=" * 80)
    print("检查2: Roostoo API配置")
    print("=" * 80)
    
    issues = []
    
    # 检查API Key
    api_key = os.getenv("ROOSTOO_API_KEY")
    if not api_key:
        issues.append("❌ ROOSTOO_API_KEY未设置")
    elif "your" in api_key.lower() or "placeholder" in api_key.lower():
        issues.append("⚠️ ROOSTOO_API_KEY可能是占位符")
    else:
        print(f"✅ ROOSTOO_API_KEY已设置: {api_key[:10]}...{api_key[-10:]}")
    
    # 检查Secret Key
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    if not secret_key:
        issues.append("❌ ROOSTOO_SECRET_KEY未设置")
    elif "your" in secret_key.lower() or "placeholder" in secret_key.lower():
        issues.append("⚠️ ROOSTOO_SECRET_KEY可能是占位符")
    else:
        print(f"✅ ROOSTOO_SECRET_KEY已设置: {secret_key[:10]}...{secret_key[-10:]}")
    
    # 检查API URL
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    if "mock" in api_url.lower():
        issues.append(f"❌ ROOSTOO_API_URL使用模拟API: {api_url}")
        issues.append("   需要设置真实的比赛API URL")
    else:
        print(f"✅ ROOSTOO_API_URL已设置: {api_url}")
    
    if issues:
        print("\n问题:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    return True

def check_llm_config():
    """检查LLM配置"""
    print("\n" + "=" * 80)
    print("检查3: LLM配置")
    print("=" * 80)
    
    issues = []
    
    # 检查LLM Provider
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    print(f"LLM Provider: {provider}")
    
    # 检查对应的API Key
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            issues.append("❌ DEEPSEEK_API_KEY未设置")
        elif "your" in api_key.lower() or "placeholder" in api_key.lower():
            issues.append("⚠️ DEEPSEEK_API_KEY可能是占位符")
        else:
            print(f"✅ DEEPSEEK_API_KEY已设置: {api_key[:10]}...")
    elif provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key:
            issues.append("❌ QWEN_API_KEY未设置")
        elif "your" in api_key.lower() or "placeholder" in api_key.lower():
            issues.append("⚠️ QWEN_API_KEY可能是占位符")
        else:
            print(f"✅ QWEN_API_KEY已设置: {api_key[:10]}...")
    elif provider == "minimax":
        api_key = os.getenv("MINIMAX_API_KEY")
        if not api_key:
            issues.append("❌ MINIMAX_API_KEY未设置")
        elif "your" in api_key.lower() or "placeholder" in api_key.lower():
            issues.append("⚠️ MINIMAX_API_KEY可能是占位符")
        else:
            print(f"✅ MINIMAX_API_KEY已设置: {api_key[:10]}...")
    
    if issues:
        print("\n问题:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    return True

def check_api_connection():
    """检查API连接"""
    print("\n" + "=" * 80)
    print("检查4: API连接测试")
    print("=" * 80)
    
    try:
        from api.roostoo_client import RoostooClient
        
        client = RoostooClient()
        print(f"API URL: {client.base_url}")
        
        if "mock" in client.base_url.lower():
            print("⚠️ 使用模拟API，不会真正下单")
            return False
        
        # 测试连接
        try:
            server_time = client.check_server_time()
            print(f"✅ Roostoo API连接成功")
            return True
        except Exception as e:
            print(f"❌ Roostoo API连接失败: {e}")
            print("   可能的原因:")
            print("   1. API URL不正确")
            print("   2. 比赛还未开始（API服务未启动）")
            print("   3. 网络问题")
            return False
    except Exception as e:
        print(f"❌ 无法创建RoostooClient: {e}")
        return False

def check_llm_connection():
    """检查LLM连接"""
    print("\n" + "=" * 80)
    print("检查5: LLM连接测试")
    print("=" * 80)
    
    try:
        from api.llm_clients.factory import get_llm_client
        
        llm = get_llm_client()
        print(f"LLM Provider: {type(llm).__name__}")
        
        # 测试连接
        try:
            messages = [{"role": "user", "content": "Hello"}]
            response = llm.chat(messages, max_tokens=10)
            print(f"✅ LLM连接成功")
            return True
        except Exception as e:
            print(f"❌ LLM连接失败: {e}")
            print("   可能的原因:")
            print("   1. LLM API Key不正确")
            print("   2. LLM API服务不可用")
            print("   3. 网络问题")
            return False
    except Exception as e:
        print(f"❌ 无法创建LLM客户端: {e}")
        return False

def check_code_config():
    """检查代码配置"""
    print("\n" + "=" * 80)
    print("检查6: 代码配置")
    print("=" * 80)
    
    issues = []
    
    # 检查integrated_example.py中的dry_run设置
    integrated_file = Path("api/agents/integrated_example.py")
    if integrated_file.exists():
        content = integrated_file.read_text()
        if "dry_run" in content:
            if "dry_run=True" in content and "dry_run=False" not in content:
                issues.append("⚠️ integrated_example.py中可能使用dry_run=True（测试模式）")
            else:
                print("✅ integrated_example.py中dry_run配置正确（默认False，真实交易）")
        else:
            print("✅ integrated_example.py中未硬编码dry_run（使用默认值False）")
    
    if issues:
        print("\n问题:")
        for issue in issues:
            print(f"  {issue}")
        return False
    
    return True

def check_agent_count():
    """检查Agent数量"""
    print("\n" + "=" * 80)
    print("检查7: Agent配置")
    print("=" * 80)
    
    integrated_file = Path("api/agents/integrated_example.py")
    if integrated_file.exists():
        content = integrated_file.read_text()
        
        # 统计add_agent调用
        add_agent_count = content.count("mgr.add_agent")
        print(f"✅ 找到 {add_agent_count} 个Agent配置")
        
        # 检查是否有被注释的Agent
        if "# mgr.add_agent" in content or "# aggressive_agent" in content:
            print("⚠️ 有Agent被注释（未使用）")
            print("   这是正常的，不影响系统运行")
    
    return True

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("系统诊断 - 检查所有可能导致失败的因素")
    print("=" * 80)
    print()
    
    results = {}
    
    # 运行所有检查
    results["env_file"] = check_env_file()
    results["roostoo_config"] = check_roostoo_config()
    results["llm_config"] = check_llm_config()
    results["api_connection"] = check_api_connection()
    results["llm_connection"] = check_llm_connection()
    results["code_config"] = check_code_config()
    results["agent_count"] = check_agent_count()
    
    # 总结
    print("\n" + "=" * 80)
    print("诊断总结")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 检查通过")
    
    # 关键问题提示
    print("\n" + "=" * 80)
    print("关键问题提示")
    print("=" * 80)
    
    if not results["roostoo_config"]:
        print("\n❌ Roostoo API配置有问题")
        print("   最可能的问题: ROOSTOO_API_URL使用模拟API")
        print("   修复方法: 在.env文件中设置 ROOSTOO_API_URL=https://api.roostoo.com")
        print("   （需要替换为真实的比赛API URL）")
    
    if not results["llm_config"]:
        print("\n❌ LLM配置有问题")
        print("   修复方法: 在.env文件中设置LLM API Key")
        print("   例如: DEEPSEEK_API_KEY=sk-your-actual-key-here")
    
    if not results["api_connection"]:
        print("\n❌ Roostoo API连接失败")
        print("   可能的原因:")
        print("   1. API URL不正确")
        print("   2. 比赛还未开始（API服务未启动）")
        print("   3. 网络问题")
        print("   4. API凭证错误")
    
    if not results["llm_connection"]:
        print("\n❌ LLM连接失败")
        print("   可能的原因:")
        print("   1. LLM API Key不正确")
        print("   2. LLM API服务不可用")
        print("   3. 网络问题")
    
    # 需要的信息
    print("\n" + "=" * 80)
    print("需要的信息")
    print("=" * 80)
    
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    if "mock" in api_url.lower():
        print("\n⚠️ 需要提供: 真实的Roostoo比赛API URL")
        print("   当前使用: https://mock-api.roostoo.com（模拟API）")
        print("   需要替换为真实的比赛API URL")
        print("   可能的值:")
        print("   - https://api.roostoo.com")
        print("   - https://competition-api.roostoo.com")
        print("   - 或其他比赛专用URL")
    
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    if provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key or "your" in api_key.lower():
            print("\n⚠️ 需要提供: DeepSeek API Key")
            print("   获取方式: https://platform.deepseek.com")
    elif provider == "qwen":
        api_key = os.getenv("QWEN_API_KEY")
        if not api_key or "your" in api_key.lower():
            print("\n⚠️ 需要提供: Qwen API Key")
            print("   获取方式: https://dashscope.aliyun.com")
    elif provider == "minimax":
        api_key = os.getenv("MINIMAX_API_KEY")
        if not api_key or "your" in api_key.lower():
            print("\n⚠️ 需要提供: Minimax API Key")
            print("   获取方式: https://www.minimax.chat")
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)
    
    if passed == total:
        print("\n✅ 所有检查通过！系统应该可以正常运行。")
        return 0
    else:
        print("\n⚠️ 部分检查失败，请根据上述提示修复问题。")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断诊断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n诊断出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


"""
快速测试多 AI 综合调用
这是一个简化的测试脚本，方便快速验证多 AI 功能
"""
from .multi_llm_client import MultiLLMClient


def quick_test():
    """快速测试"""
    print("=" * 80)
    print("多 AI 综合调用快速测试")
    print("=" * 80)
    
    try:
        # 创建多 AI 客户端
        print("\n1. 初始化多 AI 客户端...")
        client = MultiLLMClient()
        print(f"   已初始化 {len(client.clients)} 个客户端: {', '.join(client.clients.keys())}")
        
        # 准备测试消息
        print("\n2. 准备测试消息...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Answer briefly."},
            {"role": "user", "content": "用一句话回答：什么是区块链？"}
        ]
        
        # 并行调用
        print("\n3. 并行调用所有 AI...")
        response = client.chat_parallel(messages, max_tokens=100, temperature=0.7)
        
        # 显示结果
        print("\n4. 结果汇总:")
        print(client.format_results(response, format_type="summary"))
        
        print("\n5. 详细结果:")
        print(client.format_results(response, format_type="consolidated"))
        
        print("\n6. 表格格式:")
        print(client.format_results(response, format_type="table"))
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    quick_test()


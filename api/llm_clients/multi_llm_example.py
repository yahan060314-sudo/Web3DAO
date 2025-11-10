"""
多 AI 提供商综合调用示例
演示如何同时调用多个 AI 提供商并综合输出结果
"""
from .multi_llm_client import MultiLLMClient


def example_basic_usage():
    """基本使用示例"""
    print("=" * 80)
    print("示例 1: 基本使用 - 并行调用所有 AI 提供商")
    print("=" * 80)
    
    # 创建多 AI 客户端（使用所有可用的提供商）
    client = MultiLLMClient()
    
    # 准备消息
    messages = [
        {"role": "system", "content": "You are a helpful trading assistant."},
        {"role": "user", "content": "请用一句话分析当前 BTC 市场的趋势。")
    ]
    
    # 并行调用所有 AI
    print("\n正在并行调用所有 AI 提供商...")
    response = client.chat_parallel(
        messages,
        temperature=0.7,
        max_tokens=200
    )
    
    # 详细格式输出
    print("\n" + client.format_results(response, format_type="detailed"))
    
    # 综合格式输出
    print("\n" + client.format_results(response, format_type="consolidated"))


def example_specific_providers():
    """指定特定提供商示例"""
    print("\n" + "=" * 80)
    print("示例 2: 只使用指定的 AI 提供商")
    print("=" * 80)
    
    # 只使用 deepseek 和 qwen
    client = MultiLLMClient(providers=["deepseek", "qwen"])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "什么是人工智能？请用一句话回答。")
    ]
    
    print("\n正在调用 deepseek 和 qwen...")
    response = client.chat_parallel(messages, max_tokens=100)
    
    # 表格格式输出
    print("\n" + client.format_results(response, format_type="table"))
    
    # 摘要格式输出
    print("\n" + client.format_results(response, format_type="summary"))


def example_consensus():
    """共识分析示例"""
    print("\n" + "=" * 80)
    print("示例 3: 获取多个 AI 的共识")
    print("=" * 80)
    
    client = MultiLLMClient()
    
    messages = [
        {"role": "system", "content": "You are a trading analyst."},
        {"role": "user", "content": "BTC 价格是 50000 美元，你认为应该买入还是卖出？只回答'买入'或'卖出'。")
    ]
    
    print("\n正在获取多个 AI 的意见...")
    response = client.chat_parallel(messages, temperature=0.3, max_tokens=50)
    
    # 获取共识
    consensus = client.get_consensus(response)
    print(f"\n共识结果数: {consensus['consensus_count']}")
    print(f"所有 AI 意见一致: {consensus['all_agree']}")
    print("\n各 AI 的回答:")
    for provider, content in consensus["results"].items():
        print(f"  {provider.upper()}: {content}")


def example_sequential_vs_parallel():
    """顺序调用 vs 并行调用对比"""
    print("\n" + "=" * 80)
    print("示例 4: 顺序调用 vs 并行调用")
    print("=" * 80)
    
    client = MultiLLMClient(providers=["deepseek", "qwen"])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "说'你好'"}
    ]
    
    # 并行调用
    print("\n并行调用...")
    parallel_response = client.chat_parallel(messages, max_tokens=50)
    parallel_time = parallel_response["summary"]["total_time"]
    
    # 顺序调用
    print("顺序调用...")
    sequential_response = client.chat_sequential(messages, max_tokens=50)
    sequential_time = sequential_response["summary"]["total_time"]
    
    print(f"\n并行调用总耗时: {parallel_time:.2f} 秒")
    print(f"顺序调用总耗时: {sequential_time:.2f} 秒")
    print(f"性能提升: {((sequential_time - parallel_time) / sequential_time * 100):.1f}%")


def example_error_handling():
    """错误处理示例"""
    print("\n" + "=" * 80)
    print("示例 5: 错误处理")
    print("=" * 80)
    
    client = MultiLLMClient()
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "测试消息"}
    ]
    
    # 即使某些提供商失败，其他提供商的结果仍然会返回
    response = client.chat_parallel(messages, max_tokens=50, timeout=30.0)
    
    print("\n" + client.format_results(response, format_type="detailed"))
    
    # 检查是否有失败
    if response["summary"]["fail_count"] > 0:
        print(f"\n⚠️ 警告: {response['summary']['fail_count']} 个提供商调用失败")
        for provider, result in response["results"].items():
            if not result["success"]:
                print(f"  {provider}: {result['error']}")


def main():
    """主函数 - 运行所有示例"""
    try:
        example_basic_usage()
        example_specific_providers()
        example_consensus()
        example_sequential_vs_parallel()
        example_error_handling()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


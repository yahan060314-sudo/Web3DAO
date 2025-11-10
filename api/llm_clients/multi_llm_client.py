"""
多 AI 提供商综合调用模块
支持并行调用多个 AI 提供商（DeepSeek, Qwen, Minimax），并综合输出结果
"""
import concurrent.futures
import time
from typing import List, Dict, Any, Optional, Tuple
from .factory import get_llm_client
from .base import LLMClient


class MultiLLMClient:
    """
    多 AI 客户端，支持同时调用多个 AI 提供商并综合输出结果
    """
    
    def __init__(self, providers: Optional[List[str]] = None):
        """
        初始化多 AI 客户端
        
        Args:
            providers: AI 提供商列表，如 ["deepseek", "qwen", "minimax"]
                      如果为 None，则使用所有可用的提供商
        """
        available_providers = ["deepseek", "qwen", "minimax"]
        
        if providers is None:
            self.providers = available_providers
        else:
            # 验证提供商是否可用
            invalid_providers = [p for p in providers if p.lower() not in available_providers]
            if invalid_providers:
                raise ValueError(f"不支持的提供商: {invalid_providers}. 支持的提供商: {available_providers}")
            self.providers = [p.lower() for p in providers]
        
        # 初始化所有客户端
        self.clients: Dict[str, LLMClient] = {}
        self._init_clients()
    
    def _init_clients(self):
        """初始化所有客户端"""
        for provider in self.providers:
            try:
                self.clients[provider] = get_llm_client(provider=provider)
                print(f"✓ 成功初始化 {provider} 客户端")
            except Exception as e:
                print(f"⚠️ 初始化 {provider} 客户端失败: {e}")
                # 继续初始化其他客户端，但不添加失败的客户端
        
        if not self.clients:
            raise ValueError("没有成功初始化任何客户端，请检查 API 密钥配置")
    
    def chat_parallel(self,
                     messages: List[Dict[str, str]],
                     *,
                     model: Optional[str] = None,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None,
                     extra_params: Optional[Dict[str, Any]] = None,
                     timeout: float = 60.0) -> Dict[str, Any]:
        """
        并行调用所有 AI 提供商
        
        Args:
            messages: 对话消息列表
            model: 模型名称（如果支持）
            temperature: 温度参数
            max_tokens: 最大 token 数
            extra_params: 额外参数
            timeout: 超时时间（秒）
            
        Returns:
            包含所有提供商结果的字典，格式：
            {
                "results": {
                    "deepseek": {"content": "...", "raw": {...}, "success": True, "error": None},
                    "qwen": {"content": "...", "raw": {...}, "success": True, "error": None},
                    "minimax": {"content": "...", "raw": {...}, "success": True, "error": None}
                },
                "summary": {
                    "total_providers": 3,
                    "success_count": 3,
                    "fail_count": 0,
                    "response_times": {"deepseek": 1.2, "qwen": 1.5, "minimax": 1.8}
                },
                "timestamp": 1234567890.0
            }
        """
        results = {}
        response_times = {}
        start_time = time.time()
        
        def call_llm(provider: str, client: LLMClient) -> Tuple[str, Dict[str, Any]]:
            """调用单个 LLM 提供商的辅助函数"""
            provider_start = time.time()
            try:
                response = client.chat(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_params=extra_params
                )
                provider_time = time.time() - provider_start
                return provider, {
                    "content": response.get("content", ""),
                    "raw": response.get("raw"),
                    "success": True,
                    "error": None,
                    "response_time": provider_time
                }
            except Exception as e:
                provider_time = time.time() - provider_start
                return provider, {
                    "content": None,
                    "raw": None,
                    "success": False,
                    "error": str(e),
                    "response_time": provider_time
                }
        
        # 并行调用所有客户端
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_provider = {
                executor.submit(call_llm, provider, client): provider
                for provider, client in self.clients.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_provider, timeout=timeout):
                provider, result = future.result()
                results[provider] = result
                response_times[provider] = result["response_time"]
        
        # 计算统计信息
        success_count = sum(1 for r in results.values() if r["success"])
        fail_count = len(results) - success_count
        
        return {
            "results": results,
            "summary": {
                "total_providers": len(self.providers),
                "success_count": success_count,
                "fail_count": fail_count,
                "response_times": response_times,
                "total_time": time.time() - start_time
            },
            "timestamp": time.time()
        }
    
    def chat_sequential(self,
                       messages: List[Dict[str, str]],
                       *,
                       model: Optional[str] = None,
                       temperature: Optional[float] = None,
                       max_tokens: Optional[int] = None,
                       extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        顺序调用所有 AI 提供商（如果并行调用有问题时使用）
        
        Returns:
            与 chat_parallel 相同的格式
        """
        results = {}
        response_times = {}
        start_time = time.time()
        
        for provider, client in self.clients.items():
            provider_start = time.time()
            try:
                response = client.chat(
                    messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_params=extra_params
                )
                provider_time = time.time() - provider_start
                results[provider] = {
                    "content": response.get("content", ""),
                    "raw": response.get("raw"),
                    "success": True,
                    "error": None,
                    "response_time": provider_time
                }
            except Exception as e:
                provider_time = time.time() - provider_start
                results[provider] = {
                    "content": None,
                    "raw": None,
                    "success": False,
                    "error": str(e),
                    "response_time": provider_time
                }
            response_times[provider] = results[provider]["response_time"]
        
        success_count = sum(1 for r in results.values() if r["success"])
        fail_count = len(results) - success_count
        
        return {
            "results": results,
            "summary": {
                "total_providers": len(self.providers),
                "success_count": success_count,
                "fail_count": fail_count,
                "response_times": response_times,
                "total_time": time.time() - start_time
            },
            "timestamp": time.time()
        }
    
    def format_results(self, response: Dict[str, Any], format_type: str = "detailed") -> str:
        """
        格式化输出结果
        
        Args:
            response: chat_parallel 或 chat_sequential 的返回结果
            format_type: 输出格式类型
                - "detailed": 详细输出所有结果
                - "summary": 只输出摘要
                - "consolidated": 综合所有成功的结果
                - "table": 表格格式
                
        Returns:
            格式化后的字符串
        """
        if format_type == "detailed":
            return self._format_detailed(response)
        elif format_type == "summary":
            return self._format_summary(response)
        elif format_type == "consolidated":
            return self._format_consolidated(response)
        elif format_type == "table":
            return self._format_table(response)
        else:
            raise ValueError(f"不支持的格式类型: {format_type}")
    
    def _format_detailed(self, response: Dict[str, Any]) -> str:
        """详细格式输出"""
        lines = []
        lines.append("=" * 80)
        lines.append("多 AI 提供商综合结果")
        lines.append("=" * 80)
        lines.append("")
        
        summary = response["summary"]
        lines.append(f"总提供商数: {summary['total_providers']}")
        lines.append(f"成功: {summary['success_count']}")
        lines.append(f"失败: {summary['fail_count']}")
        lines.append(f"总耗时: {summary['total_time']:.2f} 秒")
        lines.append("")
        
        for provider, result in response["results"].items():
            lines.append("-" * 80)
            lines.append(f"提供商: {provider.upper()}")
            lines.append(f"状态: {'✓ 成功' if result['success'] else '✗ 失败'}")
            lines.append(f"响应时间: {result['response_time']:.2f} 秒")
            
            if result['success']:
                lines.append(f"内容:")
                lines.append(result['content'] or "(无内容)")
            else:
                lines.append(f"错误: {result['error']}")
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _format_summary(self, response: Dict[str, Any]) -> str:
        """摘要格式输出"""
        lines = []
        summary = response["summary"]
        lines.append(f"成功: {summary['success_count']}/{summary['total_providers']}")
        lines.append(f"总耗时: {summary['total_time']:.2f} 秒")
        
        for provider, result in response["results"].items():
            status = "✓" if result['success'] else "✗"
            lines.append(f"{status} {provider}: {result['response_time']:.2f}s")
        
        return "\n".join(lines)
    
    def _format_consolidated(self, response: Dict[str, Any]) -> str:
        """综合格式输出 - 将所有成功的结果合并"""
        lines = []
        lines.append("=" * 80)
        lines.append("综合 AI 结果")
        lines.append("=" * 80)
        lines.append("")
        
        successful_results = {
            provider: result
            for provider, result in response["results"].items()
            if result["success"] and result["content"]
        }
        
        if not successful_results:
            lines.append("⚠️ 所有 AI 提供商都失败了，无法生成综合结果")
            return "\n".join(lines)
        
        # 按提供商顺序输出
        for provider, result in successful_results.items():
            lines.append(f"[{provider.upper()}]")
            lines.append(result["content"])
            lines.append("")
        
        lines.append("=" * 80)
        return "\n".join(lines)
    
    def _format_table(self, response: Dict[str, Any]) -> str:
        """表格格式输出"""
        lines = []
        lines.append("提供商        | 状态  | 响应时间 | 内容长度")
        lines.append("-" * 60)
        
        for provider, result in response["results"].items():
            status = "✓" if result['success'] else "✗"
            content_len = len(result['content']) if result['content'] else 0
            lines.append(
                f"{provider:12} | {status:4} | {result['response_time']:7.2f}s | {content_len:8}"
            )
        
        return "\n".join(lines)
    
    def get_consensus(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取所有成功结果的共识（简单版本：返回所有成功的结果）
        
        Args:
            response: chat_parallel 或 chat_sequential 的返回结果
            
        Returns:
            共识结果字典
        """
        successful_results = {
            provider: result["content"]
            for provider, result in response["results"].items()
            if result["success"] and result["content"]
        }
        
        return {
            "consensus_count": len(successful_results),
            "results": successful_results,
            "all_agree": len(set(successful_results.values())) == 1 if successful_results else False
        }


if __name__ == "__main__":
    # 示例用法
    client = MultiLLMClient(providers=["deepseek", "qwen", "minimax"])
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "用一句话概括什么是区块链？"}
    ]
    
    print("正在并行调用所有 AI 提供商...")
    response = client.chat_parallel(messages, max_tokens=100, temperature=0.7)
    
    print("\n" + client.format_results(response, format_type="detailed"))
    print("\n" + client.format_results(response, format_type="consolidated"))


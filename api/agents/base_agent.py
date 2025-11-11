import threading
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from api.llm_clients.factory import get_llm_client
from .bus import MessageBus, Subscription
from .data_formatter import DataFormatter

# 导入决策频率限制器
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from utils.rate_limiter import DECISION_RATE_LIMITER, GLOBAL_DECISION_RATE_LIMITER


class BaseAgent(threading.Thread):
    """
    通用 Agent 基类：
    - 独立线程运行
    - 订阅市场数据与对话消息
    - 通过 LLM 生成简单决策（占位实现）
    - 将决策发布到决策通道
    
    改进：
    - 使用DataFormatter格式化市场数据
    - 支持结构化的市场数据（ticker、balance等）
    - 更好的数据聚合和上下文管理
    """

    def __init__(self,
                 name: str,
                 bus: MessageBus,
                 market_topic: str,
                 dialog_topic: str,
                 decision_topic: str,
                 system_prompt: str,
                 poll_timeout: float = 1.0,
                 decision_interval: float = 60.0,
                 llm_provider: Optional[str] = None,
                 allocated_capital: Optional[float] = None):
        super().__init__(name=name)
        self.daemon = True
        self.bus = bus
        self.market_sub: Subscription = bus.subscribe(market_topic)
        self.dialog_sub: Subscription = bus.subscribe(dialog_topic)
        self.decision_topic = decision_topic
        self.system_prompt = system_prompt
        self.poll_timeout = poll_timeout
        self.decision_interval = decision_interval  # 决策生成间隔
        self._stopped = False
        
        # 支持指定LLM提供商
        self.llm_provider = llm_provider
        self.llm = get_llm_client(provider=llm_provider)
        
        # 支持指定资金额度
        self.allocated_capital = allocated_capital
        
        self.formatter = DataFormatter()

        # Agent 内部状态（可扩展）
        self.last_market_snapshot: Optional[Dict[str, Any]] = None
        self.dialog_history: List[Dict[str, str]] = []
        
        # 聚合市场数据
        self.current_tickers: Dict[str, Dict[str, Any]] = {}  # pair -> ticker data
        self.current_balance: Optional[Dict[str, Any]] = None
        self._last_decision_ts: float = 0

    def stop(self):
        self._stopped = True

    def run(self):
        # 主循环：轮询市场数据与对话消息
        while not self._stopped:
            # 接收市场数据
            market_msg = self.market_sub.recv(timeout=self.poll_timeout)
            if market_msg is not None:
                self._handle_market_data(market_msg)

            # 接收对话消息
            dialog_msg = self.dialog_sub.recv(timeout=0.01)
            if dialog_msg is not None:
                self._handle_dialog(dialog_msg)

            # 定期生成决策（基于最新市场数据）
            now = time.time()
            if now - self._last_decision_ts >= self.decision_interval:
                self._maybe_make_decision()
                self._last_decision_ts = now

            # 简单节流，避免忙等
            time.sleep(0.01)
    
    def _handle_market_data(self, msg: Dict[str, Any]) -> None:
        """
        处理接收到的市场数据，根据数据类型进行聚合
        
        Args:
            msg: 市场数据消息（可能是ticker、balance等）
        """
        data_type = msg.get("type", "unknown")
        
        if data_type == "ticker":
            # 更新ticker数据
            pair = msg.get("pair")
            if pair:
                self.current_tickers[pair] = msg
        elif data_type == "balance":
            # 更新余额数据
            self.current_balance = msg
        
        # 创建综合市场快照
        ticker = None
        if self.current_tickers:
            # 使用第一个交易对的ticker作为主要数据
            ticker = list(self.current_tickers.values())[0]
        
        self.last_market_snapshot = self.formatter.create_market_snapshot(
            ticker=ticker,
            balance=self.current_balance
        )

    def _handle_dialog(self, msg: Dict[str, Any]) -> None:
        """
        处理对话消息（来自PromptManager或其他Agent）
        
        Args:
            msg: 对话消息，包含 role 和 content
        """
        # 将对话消息追加到历史
        role = msg.get("role", "user")
        content = msg.get("content", "")
        self.dialog_history.append({"role": role, "content": content})
        
        # 立即响应对话消息
        self._make_decision_from_dialog(msg)
    
    def _maybe_make_decision(self) -> None:
        """
        基于当前市场数据自动生成决策（定期调用）
        """
        if self.last_market_snapshot is None:
            return  # 没有市场数据，不生成决策
        
        # 构建决策提示词
        market_text = self.formatter.format_for_llm(self.last_market_snapshot)
        user_prompt = f"""Current market situation:
{market_text}

Based on this information, what trading action do you recommend? Provide your decision."""
        
        # 生成决策
        self._generate_decision(user_prompt)
    
    def _make_decision_from_dialog(self, dialog_msg: Dict[str, Any]) -> None:
        """
        基于对话消息生成决策
        
        Args:
            dialog_msg: 对话消息
        """
        content = dialog_msg.get("content", "")
        self._generate_decision(content)
    
    def _generate_decision(self, user_prompt: str) -> None:
        """
        生成交易决策的核心方法
        包含决策频率限制（每分钟最多1次）。
        
        Args:
            user_prompt: 用户提示词
        """
        # 全局决策频率限制：整个bot每分钟最多1次
        if not GLOBAL_DECISION_RATE_LIMITER.can_call():
            wait_time = GLOBAL_DECISION_RATE_LIMITER.wait_time()
            if wait_time > 0:
                print(f"[{self.name}] ⚠️ 全局决策频率限制: 需要等待 {wait_time:.1f} 秒")
                return  # 跳过本次决策生成
        
        # 记录决策生成（全局限制）
        GLOBAL_DECISION_RATE_LIMITER.record_call()
        
        # 构建 LLM 输入：系统提示 + 对话历史 + 市场数据
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # 添加市场数据上下文
        if self.last_market_snapshot is not None:
            market_text = self.formatter.format_for_llm(self.last_market_snapshot)
            messages.append({
                "role": "system",
                "content": f"Current Market Data:\n{market_text}"
            })
        
        # 添加最近的对话历史（控制上下文长度）
        messages.extend(self.dialog_history[-5:])
        
        # 添加当前用户提示
        messages.append({"role": "user", "content": user_prompt})

        # 请求 LLM 得到决策
        try:
            llm_out = self.llm.chat(messages, temperature=0.3, max_tokens=512)
            decision_text = llm_out.get("content") or ""
            
            # 验证JSON格式（如果可能）
            json_valid = self._validate_json_decision(decision_text)
            if not json_valid:
                print(f"[{self.name}] ⚠ WARNING: Decision may not be in JSON format:")
                print(f"    {decision_text[:200]}...")
                print(f"    System will attempt to parse, but JSON format is required.")

            decision = {
                "agent": self.name,
                "decision": decision_text,
                "market_snapshot": self.last_market_snapshot,
                "timestamp": time.time(),
                "json_valid": json_valid,  # 标记JSON格式是否有效
                "allocated_capital": self.allocated_capital,  # 添加资金额度信息
                "llm_provider": self.llm_provider  # 添加LLM提供商信息
            }
            self.bus.publish(self.decision_topic, decision)
            print(f"[{self.name}] Published decision: {decision_text[:100]}")
            if self.allocated_capital:
                print(f"[{self.name}] 资金额度: {self.allocated_capital:.2f} USD")
        except Exception as e:
            print(f"[{self.name}] Error generating decision: {e}")
    
    def _validate_json_decision(self, text: str) -> bool:
        """
        验证决策文本是否包含有效的JSON格式
        
        Returns:
            True if JSON format detected, False otherwise
        """
        if not text:
            return False
        
        import json
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                # 检查是否有必需的字段
                if "action" in data:
                    return True
            except (json.JSONDecodeError, ValueError):
                pass
        
        # 尝试直接解析整个文本
        try:
            data = json.loads(text.strip())
            if "action" in data:
                return True
        except (json.JSONDecodeError, ValueError):
            pass
        
        return False


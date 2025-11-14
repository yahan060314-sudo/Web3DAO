import threading
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from api.llm_clients.factory import get_llm_client
from .bus import MessageBus, Subscription
from .data_formatter import DataFormatter
from .capital_manager import CapitalManager

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
                 allocated_capital: Optional[float] = None,
                 capital_manager: Optional[CapitalManager] = None,
                 position_tracker=None):
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
        self.capital_manager = capital_manager
        self.position_tracker = position_tracker
        
        self.formatter = DataFormatter()

        # Agent 内部状态（可扩展）
        self.last_market_snapshot: Optional[Dict[str, Any]] = None
        self.dialog_history: List[Dict[str, str]] = []
        
        # 聚合市场数据
        self.current_tickers: Dict[str, Dict[str, Any]] = {}  # pair -> ticker data
        self.current_balance: Optional[Dict[str, Any]] = None
        self.current_exchange_info: Optional[Dict[str, Any]] = None  # 交易所信息（包含所有可用交易对）
        self._last_decision_ts: float = 0

    def stop(self):
        self._stopped = True

    def run(self):
        # 主循环：轮询市场数据与对话消息
        while not self._stopped:
            # 接收市场数据（使用较短的timeout，但循环接收，确保不遗漏消息）
            # 连续接收多个消息，直到没有更多消息
            received_any = False
            for _ in range(10):  # 最多连续接收10条消息
                market_msg = self.market_sub.recv(timeout=0.1)
                if market_msg is not None:
                    self._handle_market_data(market_msg)
                    received_any = True
                else:
                    break  # 没有更多消息，退出循环
            
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
            if not received_any:
                time.sleep(0.01)
    
    def _handle_market_data(self, msg: Dict[str, Any]) -> None:
        """
        处理接收到的市场数据，根据数据类型进行聚合
        
        Args:
            msg: 市场数据消息（可能是ticker、balance、exchange_info等）
        """
        data_type = msg.get("type", "unknown")
        
        if data_type == "ticker":
            # 更新ticker数据
            pair = msg.get("pair")
            if pair:
                self.current_tickers[pair] = msg
                # 调试：打印接收到的ticker（只打印前几个，避免日志过多）
                if len(self.current_tickers) <= 3 or pair in ["BTC/USD", "ETH/USD", "SOL/USD"]:
                    print(f"[{self.name}] ✓ 收到ticker数据: {pair} = ${msg.get('price', 'N/A')}")
        elif data_type == "balance":
            # 更新余额数据
            self.current_balance = msg
            print(f"[{self.name}] ✓ 收到余额数据: ${msg.get('total_balance', 'N/A')}")
        elif data_type == "exchange_info":
            # 更新交易所信息（包含所有可用交易对）
            self.current_exchange_info = msg
        else:
            # 调试：打印未知类型的消息
            print(f"[{self.name}] ⚠️ 收到未知类型的市场数据: type={data_type}, keys={list(msg.keys())[:5]}")
        
        # 创建综合市场快照（包含所有ticker数据）
        # 使用tickers字典格式，而不是单个ticker
        tickers_dict = self.current_tickers if self.current_tickers else None
        
        # 即使没有balance，只要有ticker数据就创建快照（允许Agent基于价格数据做决策）
        self.last_market_snapshot = self.formatter.create_market_snapshot(
            tickers=tickers_dict,
            balance=self.current_balance,
            exchange_info=getattr(self, 'current_exchange_info', None)
        )
        
        # 调试：确认快照已创建（只在有ticker数据时打印，避免日志过多）
        if self.last_market_snapshot and tickers_dict:
            ticker_count = len(tickers_dict)
            # 只在ticker数量变化或收到balance时打印
            if ticker_count <= 5 or self.current_balance:
                print(f"[{self.name}] ✓ 市场快照已更新: {ticker_count}个ticker, balance={'有' if self.current_balance else '无'}")

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
            # 调试：检查为什么没有市场数据
            ticker_count = len(self.current_tickers) if self.current_tickers else 0
            has_balance = self.current_balance is not None
            print(f"[{self.name}] ⚠️ 没有市场快照数据 - tickers: {ticker_count}, balance: {has_balance}")
            return  # 没有市场数据，不生成决策
        
        # 构建决策提示词
        market_text = self.formatter.format_for_llm(self.last_market_snapshot)
        
        # 调试：检查格式化后的市场数据
        if not market_text or market_text == "No market data available":
            ticker_count = len(self.current_tickers) if self.current_tickers else 0
            has_balance = self.current_balance is not None
            print(f"[{self.name}] ⚠️ 市场数据格式化后为空 - tickers: {ticker_count}, balance: {has_balance}")
            print(f"[{self.name}] ⚠️ 快照keys: {list(self.last_market_snapshot.keys())}")
            if self.last_market_snapshot.get("tickers"):
                print(f"[{self.name}] ⚠️ tickers类型: {type(self.last_market_snapshot.get('tickers'))}, 数量: {len(self.last_market_snapshot.get('tickers', {}))}")
        
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
            
            # 调试：检查格式化后的市场数据
            if not market_text or market_text == "No market data available":
                ticker_count = len(self.current_tickers) if self.current_tickers else 0
                has_balance = self.current_balance is not None
                print(f"[{self.name}] ⚠️ 市场数据格式化后为空 - tickers: {ticker_count}, balance: {has_balance}")
                print(f"[{self.name}] ⚠️ 快照内容: {list(self.last_market_snapshot.keys())}")
            
            # 构建资金和持仓信息
            info_parts = []
            
            # 1. 资金信息
            capital_info = ""
            allocated = self.allocated_capital
            available = None
            used = None
            if self.capital_manager:
                allocated = self.capital_manager.get_allocated_capital(self.name)
                available = self.capital_manager.get_available_capital(self.name)
                used = self.capital_manager.get_used_capital(self.name)
            if allocated is not None:
                capital_lines = [
                    "",
                    "",
                    f"💰 Your Allocated Capital: ${allocated:.2f} USD"
                ]
                if available is not None:
                    capital_lines.append(f"   Available Capital: ${available:.2f} USD")
                if used is not None:
                    capital_lines.append(f"   Currently Reserved/Used: ${used:.2f} USD")
                capital_lines.append("⚠️ IMPORTANT: These figures reflect YOUR personal allocation.")
                capital_lines.append("   The account balance shown above is shared with other agents.")
                capital_lines.append("   Base your position sizes on YOUR available capital, not the total account balance.")
                capital_info = "\n".join(capital_lines)
            
            # 2. 持仓信息（如果启用了持仓跟踪）
            position_info = ""
            if self.position_tracker:
                # 从市场快照中提取当前价格，用于计算持仓价值
                current_prices = {}
                if self.last_market_snapshot.get("tickers"):
                    tickers = self.last_market_snapshot["tickers"]
                    if isinstance(tickers, dict):
                        for pair, ticker_data in tickers.items():
                            if isinstance(ticker_data, dict) and "price" in ticker_data:
                                # 提取币种：BTC/USD -> BTC
                                base_currency = pair.split("/")[0] if "/" in pair else pair.replace("USD", "").replace("USDT", "")
                                current_prices[base_currency] = float(ticker_data["price"])
                    elif isinstance(tickers, list) and len(tickers) > 0:
                        ticker = tickers[0]
                        if isinstance(ticker, dict) and "price" in ticker:
                            pair = ticker.get("pair", "")
                            base_currency = pair.split("/")[0] if "/" in pair else pair.replace("USD", "").replace("USDT", "")
                            current_prices[base_currency] = float(ticker["price"])
                
                # 格式化持仓信息
                position_info = self.position_tracker.format_positions_for_llm(
                    agent_name=self.name,
                    current_prices=current_prices if current_prices else None
                )
            
            # 组合所有信息
            combined_info = market_text
            if capital_info:
                combined_info += "\n" + capital_info
            if position_info:
                combined_info += "\n\n" + position_info
            
            messages.append({
                "role": "system",
                "content": f"Current Market Data:\n{combined_info}"
            })
        
        # 添加最近的对话历史（控制上下文长度）
        messages.extend(self.dialog_history[-5:])
        
        # 添加当前用户提示
        messages.append({"role": "user", "content": user_prompt})

        # 请求 LLM 得到决策（提高temperature到0.7，让模型更愿意做出决策）
        try:
            llm_out = self.llm.chat(messages, temperature=0.7, max_tokens=512)
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
            if self.capital_manager:
                decision["capital_info"] = {
                    "allocated": self.capital_manager.get_allocated_capital(self.name),
                    "available": self.capital_manager.get_available_capital(self.name),
                    "used": self.capital_manager.get_used_capital(self.name)
                }
            self.bus.publish(self.decision_topic, decision)
            print(f"[{self.name}] Published decision: {decision_text[:100]}")
            if self.capital_manager:
                allocated = self.capital_manager.get_allocated_capital(self.name)
                available = self.capital_manager.get_available_capital(self.name)
                used = self.capital_manager.get_used_capital(self.name)
                print(f"[{self.name}] 资金概览: 分配={allocated:.2f} USD, 可用={available:.2f} USD, 已占用={used:.2f} USD")
            elif self.allocated_capital:
                print(f"[{self.name}] 分配资金: {self.allocated_capital:.2f} USD (初始分配，实际余额需从API获取)")
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


 


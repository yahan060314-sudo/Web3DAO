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
        try:
            # 主循环：轮询市场数据与对话消息
            loop_count = 0
            start_time = time.time()
            while not self._stopped:
                loop_count += 1
                
                # 接收市场数据（使用较短的timeout，但循环接收，确保不遗漏消息）
                # 连续接收多个消息，直到没有更多消息
                received_any = False
                complete_snapshot_received = False
                
                # 首先快速检查队列中是否有完整快照（优先级最高）
                # 持续监听，直到找到完整快照或确认没有更多消息
                pending_messages = []
                # 先尝试快速接收几次，看是否有完整快照
                for quick_check in range(30):  # 快速检查30次，每次0.2秒，总共6秒
                    market_msg = self.market_sub.recv(timeout=0.2)
                    if market_msg is not None:
                        msg_type = market_msg.get("type", "unknown")
                        is_complete = market_msg.get("is_complete", False)
                        if is_complete or msg_type == "complete_market_snapshot":
                            self._handle_market_data(market_msg)
                            complete_snapshot_received = True
                            received_any = True
                            break
                        else:
                            pending_messages.append(market_msg)
                
                # 如果还没找到完整快照，继续扫描消息
                if not complete_snapshot_received:
                    scan_count = len(pending_messages)
                    empty_count = 0  # 连续空队列次数
                    
                    # 持续监听消息，直到找到完整快照或确认没有更多消息
                    for _ in range(500):
                        market_msg = self.market_sub.recv(timeout=0.2)
                        if market_msg is not None:
                            empty_count = 0
                            scan_count += 1
                            msg_type = market_msg.get("type", "unknown")
                            is_complete = market_msg.get("is_complete", False)
                            if is_complete or msg_type == "complete_market_snapshot":
                                self._handle_market_data(market_msg)
                                complete_snapshot_received = True
                                received_any = True
                                break
                            else:
                                pending_messages.append(market_msg)
                                if len(pending_messages) > 50 and scan_count % 50 == 0:
                                    print(f"[{self.name}] ⚠️ 消息积压: {len(pending_messages)}条待处理消息")
                        else:
                            # 队列为空
                            empty_count += 1
                            # 如果连续3次空队列，且没有待处理消息，可能真的没有更多消息了
                            # 但为了确保不遗漏完整快照，我们继续等待一段时间
                            if empty_count >= 3 and len(pending_messages) == 0:
                                # 再等待1秒，确保完整快照有时间到达
                                market_msg = self.market_sub.recv(timeout=1.0)
                                if market_msg is not None:
                                    empty_count = 0
                                    scan_count += 1
                                    msg_type = market_msg.get("type", "unknown")
                                    is_complete = market_msg.get("is_complete", False)
                                    if is_complete or msg_type == "complete_market_snapshot":
                                        self._handle_market_data(market_msg)
                                        complete_snapshot_received = True
                                        received_any = True
                                        break
                                    else:
                                        pending_messages.append(market_msg)
                                else:
                                    # 真的没有更多消息了
                                    break
                
                # 如果没有找到完整快照，处理所有待处理的消息
                if not complete_snapshot_received:
                    batch_size = 10
                    for i in range(0, len(pending_messages), batch_size):
                        batch = pending_messages[i:i+batch_size]
                        for msg in batch:
                            self._handle_market_data(msg)
                            received_any = True
                        
                        market_msg = self.market_sub.recv(timeout=0.1)
                        if market_msg is not None:
                            msg_type = market_msg.get("type", "unknown")
                            is_complete = market_msg.get("is_complete", False)
                            if is_complete or msg_type == "complete_market_snapshot":
                                self._handle_market_data(market_msg)
                                complete_snapshot_received = True
                                received_any = True
                                break
                            else:
                                self._handle_market_data(market_msg)
                                received_any = True
                    
                    if not complete_snapshot_received:
                        for wait_attempt in range(20):
                            market_msg = self.market_sub.recv(timeout=0.3)
                            if market_msg is not None:
                                msg_type = market_msg.get("type", "unknown")
                                is_complete = market_msg.get("is_complete", False)
                                if is_complete or msg_type == "complete_market_snapshot":
                                    self._handle_market_data(market_msg)
                                    complete_snapshot_received = True
                                    received_any = True
                                    break
                                else:
                                    self._handle_market_data(market_msg)
                                received_any = True
                
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
                    quick_check_msg = self.market_sub.recv(timeout=0.05)
                    if quick_check_msg is not None:
                        msg_type = quick_check_msg.get("type", "unknown")
                        is_complete = quick_check_msg.get("is_complete", False)
                        if is_complete or msg_type == "complete_market_snapshot":
                            self._handle_market_data(quick_check_msg)
                            complete_snapshot_received = True
                            received_any = True
                        else:
                            self._handle_market_data(quick_check_msg)
                            received_any = True
                    else:
                        time.sleep(0.01)
        except Exception as e:
            print(f"[{self.name}] ❌ Agent运行异常: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_market_data(self, msg: Dict[str, Any]) -> None:
        """
        处理接收到的市场数据，根据数据类型进行聚合
        
        Args:
            msg: 市场数据消息（可能是ticker、balance、exchange_info、complete_market_snapshot等）
        """
        data_type = msg.get("type", "unknown")
        
        # 检查是否是完整市场快照（采集完一轮后发布）
        is_complete_snapshot = msg.get("is_complete", False) or data_type == "complete_market_snapshot"
        
        if is_complete_snapshot:
            # 收到完整市场快照，直接使用它
            self.last_market_snapshot = msg
            
            # 更新内部的ticker和balance数据
            if "tickers" in msg and isinstance(msg["tickers"], dict):
                self.current_tickers = msg["tickers"]
            if "balance" in msg:
                self.current_balance = msg["balance"]
            
            # 收到完整快照后，立即触发决策生成（分析所有交易对）
            self._trigger_decision_from_complete_snapshot()
            return
        
        if data_type == "ticker":
            # 更新ticker数据
            pair = msg.get("pair")
            if pair:
                self.current_tickers[pair] = msg
        elif data_type == "balance":
            # 更新余额数据
            self.current_balance = msg
        elif data_type == "exchange_info":
            # 更新交易所信息（包含所有可用交易对）
            self.current_exchange_info = msg
        else:
            print(f"[{self.name}] ⚠️ 收到未知类型的市场数据: type={data_type}")
        
        # 创建综合市场快照（包含所有ticker数据）
        # 使用tickers字典格式，而不是单个ticker
        tickers_dict = self.current_tickers if self.current_tickers else None
        
        # 即使没有balance，只要有ticker数据就创建快照（允许Agent基于价格数据做决策）
        self.last_market_snapshot = self.formatter.create_market_snapshot(
            tickers=tickers_dict,
            balance=self.current_balance,
            exchange_info=getattr(self, 'current_exchange_info', None)
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
    
    def _trigger_decision_from_complete_snapshot(self):
        """
        基于完整市场快照触发决策生成
        在收到完整快照后调用，让Agent分析所有交易对
        """
        if self.last_market_snapshot is None:
            return
        
        # 构建决策提示词，强调分析所有交易对
        market_text = self.formatter.format_for_llm(self.last_market_snapshot)
        
        if not market_text or market_text == "No market data available":
            return
        
        user_prompt = f"""Complete market snapshot with all trading pairs has been collected. Analyze ALL available trading pairs and make a trading decision.

Current Market Data (All Pairs):
{market_text}

IMPORTANT: You have access to data from ALL trading pairs. Compare opportunities across all currencies and select the BEST trading opportunity based on:
- Price trends and momentum
- 24h change percentage
- Volume and liquidity
- Risk-reward ratios

Provide your decision in JSON format, selecting the currency with the best opportunity."""
        
        # 生成决策（会检查全局频率限制）
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
        # 全局决策频率限制：整个bot每分钟最多2次（允许两个Agent都能做决策）
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
            
            if not market_text or market_text == "No market data available":
                ticker_count = len(self.current_tickers) if self.current_tickers else 0
                has_balance = self.current_balance is not None
                print(f"[{self.name}] ⚠️ 市场数据格式化后为空 - tickers: {ticker_count}, balance: {has_balance}")
            
            # 构建资金和持仓信息
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
            
            if not decision_text:
                print(f"[{self.name}] ⚠️ LLM返回的content为空！llm_out={llm_out}")
                return  # 如果LLM返回空内容，不发布决策
            
            # 验证JSON格式（如果可能）
            json_valid = self._validate_json_decision(decision_text)
            if not json_valid:
                print(f"[{self.name}] ⚠ WARNING: Decision may not be in JSON format:")
                print(f"    {decision_text[:200]}...")

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
            print(f"[{self.name}] ✅ Published decision: {decision_text[:100]}")
        except Exception as e:
            print(f"[{self.name}] ❌ Error generating decision: {e}")
            import traceback
            traceback.print_exc()
    
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




















import threading
import time
from typing import Dict, Any, List, Optional

from api.llm_clients.factory import get_llm_client
from .bus import MessageBus, Subscription
from .data_formatter import DataFormatter

#minimax用的
import json
import re


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

    #以下是minimax用的
    def _generate_decision(self, user_prompt: str) -> None:
        """生成交易决策（添加 MiniMax JSON 修复）"""
        try:
            # 构建消息
            messages = self._build_messages(user_prompt)
            
            # 调用 LLM
            result = self.llm.chat(messages, temperature=0.3, max_tokens=512)
            raw_content = result.get("content", "").strip()
            
            print(f"[{self.name}] LLM 原始响应: {raw_content[:200]}...")
            
            # 尝试解析 JSON（添加修复逻辑）
            decision_data = self._parse_and_fix_decision(raw_content)
            
            if decision_data:
                # 发布决策
                decision_msg = {
                    "agent": self.name,
                    "decision": decision_data,
                    "market_snapshot": self.market_snapshot,
                    "timestamp": time.time(),
                    "json_valid": True
                }
                self.bus.publish(topic=self.decision_topic, message=decision_msg)
                print(f"[{self.name}] Published decision: {decision_data}")
            else:
                # 如果无法解析，发布警告
                warning_msg = {
                    "agent": self.name,
                    "decision": raw_content,
                    "market_snapshot": self.market_snapshot,
                    "timestamp": time.time(),
                    "json_valid": False
                }
                self.bus.publish(topic=self.decision_topic, message=warning_msg)
                print(f"[{self.name}] ⚠ WARNING: Decision may not be in JSON format: {raw_content[:100]}...")
                
        except Exception as e:
            print(f"[{self.name}] Error generating decision: {e}")
    
    def _parse_and_fix_decision(self, raw_text: str) -> Optional[Dict]:
        """解析和修复 MiniMax 的 JSON 决策输出"""
        if not raw_text:
            return None
            
        # 方法1: 直接解析 JSON
        try:
            return json.loads(raw_text.strip())
        except:
            pass
        
        # 方法2: 提取 JSON 部分
        json_match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}|\{[^{}]*\}', raw_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # 方法3: 为 MiniMax 专门修复 - 处理自然语言输出
        return self._fix_minimax_natural_language(raw_text)
    
    def _fix_minimax_natural_language(self, text: str) -> Optional[Dict]:
        """修复 MiniMax 的自然语言输出，转换为 JSON 格式"""
        text_lower = text.lower()
        
        # 检测动作关键词
        action = "wait"
        if any(word in text_lower for word in ["buy", "开多", "open_long", "买入", "做多"]):
            action = "open_long"
        elif any(word in text_lower for word in ["sell", "平多", "close_long", "卖出", "平仓"]):
            action = "close_long"
        elif any(word in text_lower for word in ["hold", "持有", "保持"]):
            action = "hold"
        
        # 检测交易对符号
        symbol = "BTCUSDT"  # 默认
        symbol_match = re.search(r'(BTC|ETH|BNB|ADA|DOT|LINK|LTC|BCH|XRP|EOS)[A-Z]*', text.upper())
        if symbol_match:
            symbol = symbol_match.group(0) + "USDT"
        
        # 检测信心值
        confidence = 50  # 默认
        confidence_match = re.search(r'(\d+)%', text)
        if confidence_match:
            confidence = min(100, max(0, int(confidence_match.group(1))))
        else:
            # 根据关键词估算信心值
            if any(word in text_lower for word in ["高信心", "强烈", "definitely", "sure"]):
                confidence = 80
            elif any(word in text_lower for word in ["中等", "可能", "probably", "likely"]):
                confidence = 60
            elif any(word in text_lower for word in ["低信心", "不确定", "unsure", "maybe"]):
                confidence = 40
        
        # 构建修复后的 JSON 决策
        return {
            "action": action,
            "symbol": symbol,
            "reasoning": text[:300],  # 截取前300字符作为理由
            "confidence": confidence,
            "price_ref": 0,
            "position_size_usd": 0,
            "stop_loss": 0,
            "take_profit": 0,
            "partial_close_pct": 0,
            "invalidation_condition": "自动修复的决策",
            "slippage_buffer": 0.0005,
            "_repaired": True  # 标记这是修复后的决策
        }
        #以上是minimax用的

    def __init__(self,
                 name: str,
                 bus: MessageBus,
                 market_topic: str,
                 dialog_topic: str,
                 decision_topic: str,
                 system_prompt: str,
                 poll_timeout: float = 1.0,
                 decision_interval: float = 10.0):
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
        self.llm = get_llm_client()
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
        
        Args:
            user_prompt: 用户提示词
        """
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
                "json_valid": json_valid  # 标记JSON格式是否有效
            }
            self.bus.publish(self.decision_topic, decision)
            print(f"[{self.name}] Published decision: {decision_text[:100]}")
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


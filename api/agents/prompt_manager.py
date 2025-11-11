"""
Prompt管理模块 - 管理AI Agent的提示词，方便扩展和修改

这个模块负责：
1. 定义和管理不同类型的prompt（系统prompt、交易prompt等）
2. 支持动态prompt生成（基于市场数据、账户状态等）
3. 提供prompt模板，方便组友扩展
4. 支持多语言prompt
5. 整合prompts文件夹中的prompt模板
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from .data_formatter import DataFormatter


class PromptManager:
    """
    Prompt管理器：管理AI Agent使用的各种提示词
    
    整合了prompts文件夹中的prompt模板（组友的工作）
    """
    
    def __init__(self):
        self.formatter = DataFormatter()
        # 加载prompts文件夹中的模板
        self._load_prompt_templates()
    
    def _load_prompt_templates(self):
        """加载prompts文件夹中的prompt模板"""
        try:
            # 获取项目根目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            prompts_dir = project_root / "prompts"
            
            # 加载natural_language_prompt.txt（加密货币现货交易模板）
            # 注意：这个文件实际上是Python代码，包含agent_system_prompt_spot变量
            natural_lang_file = prompts_dir / "natural_language_prompt.txt"
            if natural_lang_file.exists():
                # 读取文件内容
                with open(natural_lang_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 尝试提取agent_system_prompt_spot变量的值
                # 文件格式：agent_system_prompt_spot = dedent("""...""")
                import re
                # 查找agent_system_prompt_spot = dedent("""...""")模式
                match = re.search(r'agent_system_prompt_spot\s*=\s*dedent\("""(.*?)"""\)', content, re.DOTALL)
                if match:
                    # 提取模板内容并去除首尾空白
                    template_content = match.group(1).strip()
                    # 处理dedent（去除每行的公共前导空白）
                    from textwrap import dedent
                    self.spot_trading_template = dedent(template_content)
                    print(f"[PromptManager] Loaded spot trading template from {natural_lang_file}")
                else:
                    # 如果找不到，尝试直接使用文件内容（可能是纯文本）
                    self.spot_trading_template = content.strip()
                    print(f"[PromptManager] Loaded spot trading template (as plain text) from {natural_lang_file}")
            else:
                self.spot_trading_template = None
                print(f"[PromptManager] Warning: {natural_lang_file} not found")
        except Exception as e:
            print(f"[PromptManager] Error loading prompt templates: {e}")
            self.spot_trading_template = None
    
    def get_system_prompt(
        self,
        agent_name: str,
        trading_strategy: Optional[str] = None,
        risk_level: str = "moderate"
    ) -> str:
        """
        获取系统提示词（定义Agent的角色和行为）
        
        Args:
            agent_name: Agent名称
            trading_strategy: 交易策略描述（可选）
            risk_level: 风险等级（conservative/moderate/aggressive）
            
        Returns:
            系统提示词
        """
        base_prompt = f"""You are {agent_name}, an AI trading assistant for Web3 quantitative trading.

Your responsibilities:
1. Analyze real-time market data (prices, volumes, trends)
2. Monitor account balance and available funds
3. Make trading decisions based on market conditions
4. Consider risk management in all decisions

Risk Level: {risk_level}
"""
        
        if trading_strategy:
            base_prompt += f"\nTrading Strategy: {trading_strategy}\n"
        
        risk_guidelines = {
            "conservative": "Be very cautious. Only trade when there's high confidence. Preserve capital.",
            "moderate": "Balance risk and reward. Look for good opportunities but don't take excessive risks. Make decisions when you have reasonable confidence (70%+).",
            "aggressive": "Be active in trading. Take calculated risks for higher returns. Make decisions when you have 60%+ confidence. Don't wait for perfect conditions - act on reasonable opportunities."
        }
        
        base_prompt += f"\nRisk Guidelines: {risk_guidelines.get(risk_level, risk_guidelines['moderate'])}\n"
        
        # 根据风险等级调整信心度阈值
        confidence_threshold = "60%" if risk_level == "aggressive" else "70%"
        
        # 构建决策哲学部分（使用f-string）
        decision_philosophy = f"""
IMPORTANT - Decision Making Philosophy:
- You should make trading decisions when you have reasonable confidence ({confidence_threshold} confidence is sufficient)
- For initial decisions and when market data is available, {confidence_threshold} confidence is enough to take action
- Don't always choose wait/hold - analyze the market and make decisions when opportunities exist
- Only choose wait/hold when market conditions are truly unclear or unfavorable (not just uncertain)
- Be proactive in identifying trading opportunities based on available market data
- Remember: Missing opportunities is also a risk - act when you have reasonable confidence

When making decisions, provide clear reasoning:
- What market signals you're seeing
- Why you're making this decision
- Expected outcome and risk assessment
"""
        
        # 构建JSON格式说明部分（不使用f-string，避免花括号冲突）
        json_format_section = """
CRITICAL - Decision Format (MANDATORY JSON):
You MUST output your decision in JSON format ONLY. No exceptions.

Required JSON format:
{{
  "action": "open_long | close_long | wait | hold",
  "symbol": "BTCUSDT",
  "price_ref": 100000.0,
  "position_size_usd": 1200.0,
  "stop_loss": 98700.0,
  "take_profit": 104000.0,
  "partial_close_pct": 0,
  "confidence": 88,
  "invalidation_condition": "示例：跌破 1h EMA20",
  "slippage_buffer": 0.0002,
  "reasoning": "要点：BTC 多周期一致；MACD>0；EMA20 支撑；放量 + 均线粘连突破；RR≥1:2；冷却期满足；信心 88。"
}}

For wait/hold actions, you can omit price and position fields, but MUST include reasoning:
{{
  "action": "wait",
  "reasoning": "Market conditions not favorable, waiting for better entry point"
}}

CRITICAL RULES:
- Output MUST be valid JSON (can be wrapped in text, but JSON must be present)
- Use ONLY ONE action: "open_long" OR "close_long" OR "wait" OR "hold"
- action="open_long" means BUY, action="close_long" means SELL
- If you cannot output JSON, the system will reject your decision
- Be explicit and clear in your reasoning field

Example valid outputs:
✓ {{"action": "open_long", "symbol": "BTCUSDT", "position_size_usd": 1000, "price_ref": 103000, "reasoning": "..."}}
✓ Based on analysis: {{"action": "wait", "reasoning": "..."}}
✗ "buy 0.01 BTC" (NOT ACCEPTED - must be JSON)
✗ I recommend buying (NOT ACCEPTED - must be JSON)
"""
        
        base_prompt += decision_philosophy + json_format_section
        
        return base_prompt
    
    def create_trading_prompt(
        self,
        market_snapshot: Dict[str, Any],
        additional_context: Optional[str] = None,
        require_decision: bool = False
    ) -> str:
        """
        创建交易决策提示词（包含当前市场数据）
        
        Args:
            market_snapshot: 市场快照数据
            additional_context: 额外的上下文信息（可选）
            require_decision: 是否要求必须做出决策（而不是wait/hold）
            
        Returns:
            格式化的交易提示词
        """
        # 格式化市场数据为文本
        market_text = self.formatter.format_for_llm(market_snapshot)
        
        prompt = f"""Analyze the current market situation and make a trading decision.

{market_text}

"""
        
        if additional_context:
            prompt += f"Additional Context: {additional_context}\n\n"
        
        if require_decision:
            prompt += """IMPORTANT: You MUST make a trading decision based on the available market data:
- Confidence threshold is LOWERED: 60%+ confidence is sufficient (not 85%+)
- If you see a reasonable opportunity (60%+ confidence), choose "open_long" or "close_long"
- Only choose "wait" or "hold" if market conditions are truly unclear or unfavorable (not just uncertain)
- Don't be overly cautious - make a decision based on the current market data
- Remember: Acting with 60% confidence is better than waiting indefinitely
- Use smaller position size (300-500 USD) if you're less confident, but still make a decision

"""
        
        prompt += """Based on the above information:
1. What is your analysis of the current market?
2. What trading action do you recommend?
3. What is your reasoning?

Provide your decision in the format specified in your system prompt."""
        
        return prompt
    
    def create_analysis_prompt(
        self,
        market_snapshot: Dict[str, Any],
        question: str
    ) -> str:
        """
        创建分析提示词（用于询问市场情况，不直接交易）
        
        Args:
            market_snapshot: 市场快照数据
            question: 要询问的问题
            
        Returns:
            格式化的分析提示词
        """
        market_text = self.formatter.format_for_llm(market_snapshot)
        
        return f"""Current Market Data:
{market_text}

Question: {question}

Please provide your analysis."""
    
    def create_custom_prompt(
        self,
        template: str,
        **kwargs
    ) -> str:
        """
        使用模板创建自定义提示词
        
        Args:
            template: 提示词模板（支持 {variable} 格式）
            **kwargs: 模板变量
            
        Returns:
            格式化后的提示词
        """
        return template.format(**kwargs)
    
    # 预定义的prompt模板
    TEMPLATES = {
        "daily_summary": """Provide a daily trading summary:
- Total trades executed: {trade_count}
- Current portfolio value: {portfolio_value}
- Best performing asset: {best_asset}
- Market sentiment: {sentiment}

What are your insights and recommendations for tomorrow?""",
        
        "risk_assessment": """Assess the current risk level:
- Market volatility: {volatility}
- Account balance: {balance}
- Open positions: {positions}

What risk management actions should be taken?""",
        
        "opportunity_scan": """Scan the market for trading opportunities:
- Current prices: {prices}
- Recent trends: {trends}
- Volume patterns: {volumes}

What opportunities do you see?"""
    }
    
    def get_template(self, template_name: str) -> Optional[str]:
        """获取预定义的prompt模板"""
        return self.TEMPLATES.get(template_name)
    
    def get_spot_trading_prompt(
        self,
        date: str,
        account_equity: str,
        available_cash: str,
        positions: str,
        price_series: str = "",
        volume_series: str = "",
        recent_sharpe: str = "",
        trade_stats: str = "",
        stop_signal: str = "__STOP__"
    ) -> Optional[str]:
        """
        使用prompts/natural_language_prompt.txt模板生成现货交易prompt
        
        这是组友创建的详细加密货币现货交易prompt模板，包含：
        - 严格的交易规则（禁止杠杆、禁止做空）
        - 风险管理协议
        - 策略与信号
        - 结构化输出格式（JSON）
        
        Args:
            date: 今日日期
            account_equity: 账户净值（USDT）
            available_cash: 可用现金（USDT）
            positions: 持仓信息（格式：symbol:数量）
            price_series: 价格时间序列（可选）
            volume_series: 成交量时间序列（可选）
            recent_sharpe: 近期夏普比率（可选）
            trade_stats: 交易统计（可选）
            stop_signal: 停止信号（默认"__STOP__"）
            
        Returns:
            格式化后的prompt字符串，如果模板未加载则返回None
        """
        if self.spot_trading_template is None:
            return None
        
        try:
            # 使用简单的字符串替换（避免JSON示例中的花括号被format()误解析）
            # 这样可以保留模板中JSON示例的原始格式
            result = self.spot_trading_template
            result = result.replace('{date}', date)
            result = result.replace('{account_equity}', account_equity)
            result = result.replace('{available_cash}', available_cash)
            result = result.replace('{positions}', positions)
            result = result.replace('{price_series}', price_series)
            result = result.replace('{volume_series}', volume_series)
            result = result.replace('{recent_sharpe}', recent_sharpe)
            result = result.replace('{trade_stats}', trade_stats)
            result = result.replace('{STOP_SIGNAL}', stop_signal)
            
            return result
        except Exception as e:
            print(f"[PromptManager] Error formatting spot trading prompt: {e}")
            return None
    
    def create_spot_prompt_from_market_data(
        self,
        market_snapshot: Dict[str, Any],
        date: Optional[str] = None,
        price_series: str = "",
        volume_series: str = "",
        recent_sharpe: str = "",
        trade_stats: str = ""
    ) -> Optional[str]:
        """
        从市场快照数据创建现货交易prompt（使用组友的模板）
        
        这个方法会自动从market_snapshot中提取：
        - account_equity: 从balance中提取total_balance
        - available_cash: 从balance中提取available_balance
        - positions: 从balance中提取各币种持仓
        
        Args:
            market_snapshot: 市场快照数据（包含ticker和balance）
            date: 日期（可选，默认使用当前日期）
            price_series: 价格时间序列（可选）
            volume_series: 成交量时间序列（可选）
            recent_sharpe: 近期夏普比率（可选）
            trade_stats: 交易统计（可选）
            
        Returns:
            格式化后的prompt字符串
        """
        if self.spot_trading_template is None:
            print("[PromptManager] Spot trading template not loaded, using default prompt")
            return self.create_trading_prompt(market_snapshot)
        
        # 提取账户信息
        balance = market_snapshot.get("balance")
        # 处理balance为None的情况
        if balance is None:
            balance = {}
        elif not isinstance(balance, dict):
            # 如果balance不是字典，设置为空字典
            balance = {}
        
        account_equity = str(balance.get("total_balance", "0")) if balance else "0"
        available_cash = str(balance.get("available_balance", "0")) if balance else "0"
        
        # 格式化持仓信息
        positions_parts = []
        if balance and "currencies" in balance:
            currencies = balance.get("currencies", {})
            if isinstance(currencies, dict):
                for currency, amounts in currencies.items():
                    if isinstance(amounts, dict):
                        total = amounts.get("total", 0)
                        if total > 0:
                            positions_parts.append(f"{currency}: {total}")
        positions = ", ".join(positions_parts) if positions_parts else "无持仓"
        
        # 获取日期
        if date is None:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
        
        return self.get_spot_trading_prompt(
            date=date,
            account_equity=account_equity,
            available_cash=available_cash,
            positions=positions,
            price_series=price_series,
            volume_series=volume_series,
            recent_sharpe=recent_sharpe,
            trade_stats=trade_stats
        )


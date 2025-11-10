import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

class TradingDecisionFileManager:
    """
    交易决策文件管理器
    专门处理交易 AI 的 JSON 输出并保存为决策文件
    """
    
    def __init__(self, base_dir: str = "trading_decisions"):
        self.base_dir = base_dir
        self._ensure_directories()
    
    def _ensure_directories(self):
        """创建必要的目录结构"""
        dirs = [
            self.base_dir,
            os.path.join(self.base_dir, "pending"),
            os.path.join(self.base_dir, "executed"),
            os.path.join(self.base_dir, "rejected")
        ]
        
        for directory in dirs:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"📁 创建目录: {directory}")
    
    def extract_json_from_llm_response(self, llm_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从 LLM 客户端响应中提取和验证 JSON 决策
        """
        raw_content = llm_response.get("content", "").strip()
        
        if not raw_content:
            print("❌ LLM 响应内容为空")
            return None
        
        print(f"🤖 LLM 原始响应: {raw_content[:200]}...")
        
        # 清理响应文本
        cleaned_text = self._clean_trading_decision_text(raw_content)
        
        # 验证和解析 JSON
        return self._validate_trading_decision(cleaned_text)
    
    def _clean_trading_decision_text(self, text: str) -> str:
        """清理交易决策文本"""
        text = text.strip()
        
        # 移除代码块标记
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        # 提取 JSON 部分（从第一个 { 开始）
        start_idx = text.find('{')
        if start_idx != -1:
            text = text[start_idx:]
        
        return text.strip()
    
    def _validate_trading_decision(self, json_text: str) -> Optional[Dict[str, Any]]:
        """验证交易决策 JSON"""
        try:
            decision = json.loads(json_text)
            
            # 验证必需字段
            required_fields = ['action', 'symbol']
            for field in required_fields:
                if field not in decision:
                    print(f"❌ 决策缺少必需字段: {field}")
                    return None
            
            # 验证 action 值
            valid_actions = ['buy', 'sell', 'hold', 'open_long', 'close_long', 'wait']
            if decision.get('action') not in valid_actions:
                print(f"❌ 无效的 action: {decision.get('action')}")
                return None
            
            print("✅ 交易决策验证通过")
            return decision
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败: {e}")
            return None
    
    def save_decision_to_file(self, 
                            decision: Dict[str, Any], 
                            agent_name: str,
                            status: str = "pending") -> Optional[str]:
        """
        保存决策到文件，返回文件路径
        """
        if not decision:
            return None
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol = decision.get('symbol', 'UNKNOWN').replace('/', '_')
        filename = f"{timestamp}_{agent_name}_{symbol}_{status}.json"
        
        # 确定保存目录
        if status == "executed":
            directory = os.path.join(self.base_dir, "executed")
        elif status == "rejected":
            directory = os.path.join(self.base_dir, "rejected")
        else:
            directory = os.path.join(self.base_dir, "pending")
        
        file_path = os.path.join(directory, filename)
        
        # 添加元数据
        decision_with_meta = decision.copy()
        decision_with_meta['_metadata'] = {
            'agent': agent_name,
            'timestamp': datetime.now().isoformat(),
            'file_saved': file_path,
            'status': status
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(decision_with_meta, f, ensure_ascii=False, indent=2)
            
            print(f"💾 决策保存到: {file_path}")
            return file_path
        except Exception as e:
            print(f"❌ 文件保存失败: {e}")
            return None
    
    def process_agent_decision(self, 
                             llm_response: Dict[str, Any], 
                             agent_name: str) -> Optional[str]:
        """
        处理 Agent 的决策：提取 -> 验证 -> 保存
        """
        print(f"\n=== 处理 {agent_name} 的决策 ===")
        
        # 1. 提取和验证 JSON
        decision = self.extract_json_from_llm_response(llm_response)
        if not decision:
            print(f"❌ {agent_name} 的决策无效")
            # 保存无效决策用于分析
            invalid_decision = {
                "action": "invalid",
                "symbol": "N/A",
                "reason": "Failed to parse decision",
                "raw_response": llm_response.get("content", "")[:500]
            }
            return self.save_decision_to_file(invalid_decision, agent_name, "rejected")
        
        # 2. 保存有效决策
        return self.save_decision_to_file(decision, agent_name, "pending")

# 集成到您的 Agent 系统中的示例
def integrate_with_agents():
    """
    展示如何将文件管理器集成到您的 Agent 系统中
    """
    file_manager = TradingDecisionFileManager()
    
    # 模拟从您的 Agent 系统获取 LLM 响应
    mock_llm_responses = [
        {
            "agent": "alpha_agent",
            "response": {
                "content": '{"action": "buy", "symbol": "BTC/USDT", "quantity": 0.5, "price": 50000, "reason": "突破阻力位"}',
                "raw": {"some": "raw_data"}
            }
        },
        {
            "agent": "beta_agent", 
            "response": {
                "content": '```json\n{"action": "sell", "symbol": "ETH/USDT", "quantity": 10, "reason": "到达目标价"}\n```',
                "raw": {"some": "raw_data"}
            }
        }
    ]
    
    # 处理每个 Agent 的决策
    for agent_data in mock_llm_responses:
        file_path = file_manager.process_agent_decision(
            agent_data["response"], 
            agent_data["agent"]
        )
        
        if file_path:
            print(f"✅ {agent_data['agent']} 决策已保存: {file_path}")
        else:
            print(f"❌ {agent_data['agent']} 决策处理失败")

if __name__ == "__main__":
    print("🧪 测试基础文件生成器:")
    example_usage()
    
    print("\n" + "="*50 + "\n")
    
    print("🧪 测试交易决策文件管理器:")
    integrate_with_agents()

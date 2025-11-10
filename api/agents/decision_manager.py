"""
决策管理器 (DecisionManager)
负责收集、存储、验证、综合多个AI的决策，并管理执行队列
"""
import time
import json
import sqlite3
import threading
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from pathlib import Path
from .bus import MessageBus


class DecisionManager:
    """
    决策管理器：
    - 收集多个AI的决策
    - 决策存储（SQLite数据库）
    - 决策验证（价格、数量、时间）
    - 决策综合（多AI投票）
    - 执行队列管理
    """
    
    def __init__(self, 
                 db_path: str = "decisions.db",
                 decision_timeout: float = 5.0,
                 enable_multi_ai_consensus: bool = True):
        """
        初始化决策管理器
        
        Args:
            db_path: 数据库文件路径
            decision_timeout: 决策有效期（秒），过期决策不执行
            enable_multi_ai_consensus: 是否启用多AI决策综合
        """
        self.db_path = db_path
        self.decision_timeout = decision_timeout
        self.enable_multi_ai_consensus = enable_multi_ai_consensus
        
        # 初始化数据库
        self._init_database()
        
        # 决策缓存（用于多AI综合）
        self.pending_decisions: Dict[str, List[Dict[str, Any]]] = {}  # timestamp_key -> decisions
        self.consensus_window = 2.0  # 决策综合时间窗口（秒）
        self.consensus_lock = threading.Lock()
        
        # 执行队列
        self.execution_queue: List[Dict[str, Any]] = []
        self.execution_lock = threading.Lock()
    
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 决策表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                decision TEXT NOT NULL,
                decision_json TEXT,
                market_snapshot TEXT,
                timestamp REAL NOT NULL,
                json_valid INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 执行结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id INTEGER,
                order_id TEXT,
                status TEXT NOT NULL,
                error TEXT,
                execution_time REAL,
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        """)
        
        # 市场数据表（用于分析）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                ticker TEXT,
                balance TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print(f"[DecisionManager] ✓ 数据库初始化完成: {self.db_path}")
    
    def add_decision(self, decision_msg: Dict[str, Any]) -> int:
        """
        添加决策到数据库
        
        Args:
            decision_msg: 决策消息，包含 agent, decision, market_snapshot, timestamp, json_valid
            
        Returns:
            决策ID
        """
        agent = decision_msg.get("agent", "unknown")
        decision = decision_msg.get("decision", "")
        market_snapshot = decision_msg.get("market_snapshot")
        timestamp = decision_msg.get("timestamp", time.time())
        json_valid = decision_msg.get("json_valid", False)
        
        # 尝试解析JSON
        decision_json = None
        try:
            if json_valid:
                # 提取JSON
                import re
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', decision, re.DOTALL)
                if json_match:
                    decision_json = json_match.group(0)
        except Exception:
            pass
        
        # 存储到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO decisions (agent, decision, decision_json, market_snapshot, 
                                 timestamp, json_valid, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (
            agent,
            decision,
            decision_json,
            json.dumps(market_snapshot) if market_snapshot else None,
            timestamp,
            1 if json_valid else 0
        ))
        
        decision_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DecisionManager] ✓ 决策已存储: ID={decision_id}, Agent={agent}")
        return decision_id
    
    def get_decision(self, decision_id: int) -> Optional[Dict[str, Any]]:
        """获取决策信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "agent": row[1],
            "decision": row[2],
            "decision_json": row[3],
            "market_snapshot": json.loads(row[4]) if row[4] else None,
            "timestamp": row[5],
            "json_valid": bool(row[6]),
            "status": row[7],
            "created_at": row[8]
        }
    
    def record_execution_result(self, 
                                decision_id: int, 
                                order_id: Optional[str] = None,
                                status: str = "success",
                                error: Optional[str] = None,
                                execution_time: Optional[float] = None):
        """
        记录执行结果
        
        Args:
            decision_id: 决策ID
            order_id: 订单ID
            status: 执行状态（success/failed）
            error: 错误信息
            execution_time: 执行时间
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 更新决策状态
        cursor.execute("""
            UPDATE decisions SET status = ? WHERE id = ?
        """, (status, decision_id))
        
        # 插入执行结果
        cursor.execute("""
            INSERT INTO execution_results (decision_id, order_id, status, error, execution_time)
            VALUES (?, ?, ?, ?, ?)
        """, (decision_id, order_id, status, error, execution_time))
        
        conn.commit()
        conn.close()
        
        print(f"[DecisionManager] ✓ 执行结果已记录: Decision ID={decision_id}, Status={status}")
    
    def validate_decision(self, decision: Dict[str, Any], 
                         current_price: Optional[float] = None,
                         balance: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        验证决策是否有效
        
        Args:
            decision: 决策字典（包含 side, quantity, price, pair）
            current_price: 当前价格（用于验证价格合理性）
            balance: 账户余额（用于验证余额充足性）
            
        Returns:
            (is_valid, error_message)
        """
        # 检查必需字段
        if "side" not in decision or "quantity" not in decision:
            return False, "缺少必需字段: side 或 quantity"
        
        # 检查数量合理性
        quantity = decision.get("quantity", 0)
        if quantity <= 0:
            return False, f"数量无效: {quantity}"
        if quantity > 1000:  # 假设最大数量限制
            return False, f"数量过大: {quantity}"
        
        # 检查价格合理性（如果有价格）
        price = decision.get("price")
        if price is not None:
            if price <= 0:
                return False, f"价格无效: {price}"
            if current_price is not None:
                # 检查价格是否在合理范围内（±10%）
                price_range = current_price * 0.1
                if abs(price - current_price) > price_range:
                    return False, f"价格超出合理范围: {price} (当前价格: {current_price})"
        
        # 检查时间有效性
        timestamp = decision.get("timestamp", time.time())
        age = time.time() - timestamp
        if age > self.decision_timeout:
            return False, f"决策已过期: {age:.2f}秒 > {self.decision_timeout}秒"
        
        # 检查余额充足性（如果有余额信息）
        if balance is not None and decision.get("side") == "BUY":
            # 这里需要根据实际余额结构来检查
            # 假设 balance 包含可用余额信息
            pass
        
        return True, None
    
    def get_consensus_decision(self, 
                              decisions: List[Dict[str, Any]],
                              window_seconds: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        从多个决策中获取共识决策（简单投票机制）
        
        Args:
            decisions: 决策列表
            window_seconds: 时间窗口（秒），在此时间窗口内的决策参与投票
            
        Returns:
            共识决策，如果无法达成共识则返回None
        """
        if not decisions:
            return None
        
        if len(decisions) == 1:
            return decisions[0]
        
        # 按side分组统计
        buy_count = 0
        sell_count = 0
        buy_decisions = []
        sell_decisions = []
        
        for decision in decisions:
            side = decision.get("side")
            if side == "BUY":
                buy_count += 1
                buy_decisions.append(decision)
            elif side == "SELL":
                sell_count += 1
                sell_decisions.append(decision)
        
        # 如果buy和sell数量相等，无法达成共识
        if buy_count == sell_count:
            return None
        
        # 选择多数决策
        if buy_count > sell_count:
            consensus_side = "BUY"
            consensus_decisions = buy_decisions
        else:
            consensus_side = "SELL"
            consensus_decisions = sell_decisions
        
        # 计算平均数量
        total_quantity = sum(d.get("quantity", 0) for d in consensus_decisions)
        avg_quantity = total_quantity / len(consensus_decisions)
        
        # 计算平均价格（如果有）
        prices = [d.get("price") for d in consensus_decisions if d.get("price")]
        avg_price = sum(prices) / len(prices) if prices else None
        
        # 使用第一个决策的交易对
        pair = consensus_decisions[0].get("pair", "BTC/USD")
        
        return {
            "side": consensus_side,
            "quantity": avg_quantity,
            "price": avg_price,
            "pair": pair,
            "consensus_count": len(consensus_decisions),
            "total_decisions": len(decisions),
            "timestamp": time.time()
        }
    
    def add_to_execution_queue(self, decision: Dict[str, Any], priority: int = 0):
        """
        添加决策到执行队列
        
        Args:
            decision: 决策字典
            priority: 优先级（数字越大优先级越高）
        """
        with self.execution_lock:
            self.execution_queue.append({
                "decision": decision,
                "priority": priority,
                "added_at": time.time()
            })
            # 按优先级排序
            self.execution_queue.sort(key=lambda x: x["priority"], reverse=True)
    
    def get_next_decision_to_execute(self) -> Optional[Dict[str, Any]]:
        """
        从执行队列获取下一个要执行的决策
        
        Returns:
            决策字典，如果队列为空则返回None
        """
        with self.execution_lock:
            if not self.execution_queue:
                return None
            
            item = self.execution_queue.pop(0)
            return item["decision"]
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取统计信息
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 计算时间范围
        since_time = time.time() - (hours * 3600)
        
        # 总决策数
        cursor.execute("SELECT COUNT(*) FROM decisions WHERE timestamp > ?", (since_time,))
        total_decisions = cursor.fetchone()[0]
        
        # 成功执行数
        cursor.execute("""
            SELECT COUNT(*) FROM execution_results 
            WHERE status = 'success' AND execution_time > ?
        """, (since_time,))
        success_count = cursor.fetchone()[0]
        
        # 失败执行数
        cursor.execute("""
            SELECT COUNT(*) FROM execution_results 
            WHERE status = 'failed' AND execution_time > ?
        """, (since_time,))
        fail_count = cursor.fetchone()[0]
        
        # 平均执行时间
        cursor.execute("""
            SELECT AVG(execution_time) FROM execution_results 
            WHERE execution_time > ? AND execution_time IS NOT NULL
        """, (since_time,))
        avg_execution_time = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_decisions": total_decisions,
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": success_count / total_decisions if total_decisions > 0 else 0,
            "avg_execution_time": avg_execution_time
        }


if __name__ == "__main__":
    # 测试代码
    manager = DecisionManager()
    
    # 添加测试决策
    test_decision = {
        "agent": "test_agent",
        "decision": '{"action": "buy", "quantity": 0.01}',
        "market_snapshot": {"price": 50000},
        "timestamp": time.time(),
        "json_valid": True
    }
    
    decision_id = manager.add_decision(test_decision)
    print(f"添加决策: ID={decision_id}")
    
    # 获取决策
    decision = manager.get_decision(decision_id)
    print(f"获取决策: {decision}")
    
    # 记录执行结果
    manager.record_execution_result(decision_id, order_id="test_order_123", status="success")
    
    # 获取统计信息
    stats = manager.get_statistics()
    print(f"统计信息: {stats}")


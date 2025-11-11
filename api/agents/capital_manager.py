"""
资本管理器 (CapitalManager)
负责管理初始资金和每个Agent的资金分配
"""
import threading
from typing import Dict, Optional, List
from datetime import datetime


class CapitalManager:
    """
    资本管理器：
    - 管理初始资金（默认50000）
    - 为每个Agent分配资金额度
    - 跟踪每个Agent的资金使用情况
    - 提供资金查询和分配接口
    """
    
    def __init__(self, initial_capital: float = 50000.0):
        """
        初始化资本管理器
        
        Args:
            initial_capital: 初始资金（默认50000）
        """
        self.initial_capital = initial_capital
        self.total_capital = initial_capital
        
        # Agent资金分配：agent_name -> allocated_capital
        self.allocated_capital: Dict[str, float] = {}
        
        # Agent资金使用情况：agent_name -> used_capital
        self.used_capital: Dict[str, float] = {}
        
        # Agent可用资金：agent_name -> available_capital
        self.available_capital: Dict[str, float] = {}
        
        # 线程锁
        self.lock = threading.Lock()
        
        print(f"[CapitalManager] 初始化完成: 初始资金 = {initial_capital:.2f} USD")
    
    def allocate_capital(self, agent_name: str, amount: float) -> bool:
        """
        为Agent分配资金
        
        Args:
            agent_name: Agent名称
            amount: 分配的资金额度
            
        Returns:
            True if allocation successful, False otherwise
        """
        with self.lock:
            # 检查总资金是否足够
            total_allocated = sum(self.allocated_capital.values())
            if total_allocated + amount > self.total_capital:
                print(f"[CapitalManager] ✗ 资金不足: 已分配 {total_allocated:.2f}, 请求分配 {amount:.2f}, 总资金 {self.total_capital:.2f}")
                return False
            
            # 分配资金
            self.allocated_capital[agent_name] = amount
            self.used_capital[agent_name] = 0.0
            self.available_capital[agent_name] = amount
            
            print(f"[CapitalManager] ✓ 为 {agent_name} 分配资金: {amount:.2f} USD")
            return True
    
    def allocate_equal(self, agent_names: List[str]) -> Dict[str, float]:
        """
        为多个Agent平均分配资金
        
        Args:
            agent_names: Agent名称列表
            
        Returns:
            分配结果字典：agent_name -> allocated_amount
        """
        if not agent_names:
            return {}
        
        amount_per_agent = self.total_capital / len(agent_names)
        results = {}
        
        for agent_name in agent_names:
            success = self.allocate_capital(agent_name, amount_per_agent)
            if success:
                results[agent_name] = amount_per_agent
            else:
                print(f"[CapitalManager] ✗ 为 {agent_name} 分配资金失败")
        
        return results
    
    def get_available_capital(self, agent_name: str) -> float:
        """
        获取Agent的可用资金
        
        Args:
            agent_name: Agent名称
            
        Returns:
            可用资金额度
        """
        with self.lock:
            return self.available_capital.get(agent_name, 0.0)
    
    def get_allocated_capital(self, agent_name: str) -> float:
        """
        获取Agent的分配资金
        
        Args:
            agent_name: Agent名称
            
        Returns:
            分配资金额度
        """
        with self.lock:
            return self.allocated_capital.get(agent_name, 0.0)
    
    def get_used_capital(self, agent_name: str) -> float:
        """
        获取Agent的已使用资金
        
        Args:
            agent_name: Agent名称
            
        Returns:
            已使用资金额度
        """
        with self.lock:
            return self.used_capital.get(agent_name, 0.0)
    
    def reserve_capital(self, agent_name: str, amount: float) -> bool:
        """
        预留资金（用于交易）
        
        Args:
            agent_name: Agent名称
            amount: 预留的资金额度
            
        Returns:
            True if reservation successful, False otherwise
        """
        with self.lock:
            available = self.available_capital.get(agent_name, 0.0)
            if available < amount:
                print(f"[CapitalManager] ✗ {agent_name} 可用资金不足: {available:.2f} < {amount:.2f}")
                return False
            
            # 预留资金
            self.available_capital[agent_name] -= amount
            self.used_capital[agent_name] += amount
            
            print(f"[CapitalManager] ✓ {agent_name} 预留资金: {amount:.2f} USD (可用: {self.available_capital[agent_name]:.2f})")
            return True
    
    def release_capital(self, agent_name: str, amount: float) -> bool:
        """
        释放资金（交易完成或取消）
        
        Args:
            agent_name: Agent名称
            amount: 释放的资金额度
            
        Returns:
            True if release successful, False otherwise
        """
        with self.lock:
            used = self.used_capital.get(agent_name, 0.0)
            if used < amount:
                print(f"[CapitalManager] ✗ {agent_name} 已使用资金不足: {used:.2f} < {amount:.2f}")
                return False
            
            # 释放资金
            self.used_capital[agent_name] -= amount
            self.available_capital[agent_name] += amount
            
            print(f"[CapitalManager] ✓ {agent_name} 释放资金: {amount:.2f} USD (可用: {self.available_capital[agent_name]:.2f})")
            return True
    
    def get_summary(self) -> Dict[str, any]:
        """
        获取资金分配摘要
        
        Returns:
            资金分配摘要字典
        """
        with self.lock:
            total_allocated = sum(self.allocated_capital.values())
            total_used = sum(self.used_capital.values())
            total_available = sum(self.available_capital.values())
            
            return {
                "initial_capital": self.initial_capital,
                "total_capital": self.total_capital,
                "total_allocated": total_allocated,
                "total_used": total_used,
                "total_available": total_available,
                "allocations": dict(self.allocated_capital),
                "used": dict(self.used_capital),
                "available": dict(self.available_capital)
            }
    
    def print_summary(self):
        """打印资金分配摘要"""
        summary = self.get_summary()
        print("\n" + "=" * 60)
        print("资金分配摘要")
        print("=" * 60)
        print(f"初始资金: {summary['initial_capital']:.2f} USD")
        print(f"总分配: {summary['total_allocated']:.2f} USD")
        print(f"总使用: {summary['total_used']:.2f} USD")
        print(f"总可用: {summary['total_available']:.2f} USD")
        print("\n各Agent资金分配:")
        for agent_name, allocated in summary['allocations'].items():
            used = summary['used'].get(agent_name, 0.0)
            available = summary['available'].get(agent_name, 0.0)
            print(f"  {agent_name}:")
            print(f"    分配: {allocated:.2f} USD")
            print(f"    使用: {used:.2f} USD")
            print(f"    可用: {available:.2f} USD")
        print("=" * 60 + "\n")


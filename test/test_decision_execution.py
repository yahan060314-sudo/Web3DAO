#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试决策执行情况
用于验证决策是否真的被成功传递到市场上

使用方法:
    python test_decision_execution.py [选项]

选项:
    --hours N      查看最近N小时的决策（默认24）
    --agent NAME   只查看指定Agent的决策
    --orders       同时查询订单历史
    --balance      显示当前余额
"""
import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

from api.roostoo_client import RoostooClient
from api.agents.decision_manager import DecisionManager


def format_timestamp(ts: float) -> str:
    """格式化时间戳"""
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


def print_decision_summary(decision: Dict[str, Any], execution_result: Optional[Dict[str, Any]] = None):
    """打印决策摘要"""
    print("\n" + "=" * 80)
    print(f"决策 ID: {decision['id']}")
    print(f"Agent: {decision['agent']}")
    print(f"时间: {format_timestamp(decision['timestamp'])}")
    print(f"状态: {decision['status']}")
    print(f"JSON格式有效: {decision['json_valid']}")
    
    # 打印决策内容
    decision_text = decision['decision']
    if len(decision_text) > 200:
        print(f"决策内容: {decision_text[:200]}...")
    else:
        print(f"决策内容: {decision_text}")
    
    # 打印执行结果
    if execution_result:
        print(f"\n执行结果:")
        print(f"  订单ID: {execution_result.get('order_id', 'N/A')}")
        print(f"  状态: {execution_result.get('status', 'N/A')}")
        print(f"  执行时间: {execution_result.get('execution_time', 'N/A')}秒")
        if execution_result.get('error'):
            print(f"  错误: {execution_result['error']}")
    else:
        print("\n执行结果: 无")


def get_recent_decisions(db_path: str, hours: int = 24, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取最近的决策"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    since_time = (datetime.now() - timedelta(hours=hours)).timestamp()
    
    if agent_name:
        cursor.execute("""
            SELECT * FROM decisions 
            WHERE timestamp > ? AND agent = ?
            ORDER BY timestamp DESC
        """, (since_time, agent_name))
    else:
        cursor.execute("""
            SELECT * FROM decisions 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (since_time,))
    
    rows = cursor.fetchall()
    conn.close()
    
    decisions = []
    for row in rows:
        decisions.append({
            "id": row[0],
            "agent": row[1],
            "decision": row[2],
            "decision_json": row[3],
            "market_snapshot": row[4],
            "timestamp": row[5],
            "json_valid": bool(row[6]),
            "status": row[7],
            "created_at": row[8]
        })
    
    return decisions


def get_execution_results(db_path: str, decision_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """获取执行结果"""
    if not decision_ids:
        return {}
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    placeholders = ','.join(['?'] * len(decision_ids))
    cursor.execute(f"""
        SELECT decision_id, order_id, status, error, execution_time, executed_at
        FROM execution_results
        WHERE decision_id IN ({placeholders})
        ORDER BY executed_at DESC
    """, decision_ids)
    
    rows = cursor.fetchall()
    conn.close()
    
    results = {}
    for row in rows:
        decision_id = row[0]
        results[decision_id] = {
            "order_id": row[1],
            "status": row[2],
            "error": row[3],
            "execution_time": row[4],
            "executed_at": row[5]
        }
    
    return results


def query_orders_from_api(client: RoostooClient, pair: Optional[str] = None) -> Dict[str, Any]:
    """从API查询订单历史"""
    try:
        print("\n" + "=" * 80)
        print("从API查询订单历史...")
        print("=" * 80)
        
        # 查询订单（可以指定pair或查询所有）
        if pair:
            orders = client.query_order(pair=pair)
        else:
            orders = client.query_order()
        
        if isinstance(orders, dict):
            if orders.get("Success"):
                order_list = orders.get("Orders", [])
                print(f"✓ 查询成功，找到 {len(order_list)} 个订单")
                
                if order_list:
                    print("\n最近的订单:")
                    for i, order in enumerate(order_list[:10], 1):  # 只显示最近10个
                        order_detail = order.get("OrderDetail", {})
                        print(f"\n订单 {i}:")
                        print(f"  订单ID: {order_detail.get('OrderID', 'N/A')}")
                        print(f"  交易对: {order_detail.get('Pair', 'N/A')}")
                        print(f"  方向: {order_detail.get('Side', 'N/A')}")
                        print(f"  类型: {order_detail.get('Type', 'N/A')}")
                        print(f"  状态: {order_detail.get('Status', 'N/A')}")
                        print(f"  数量: {order_detail.get('Quantity', 'N/A')}")
                        print(f"  价格: {order_detail.get('Price', 'N/A')}")
                        print(f"  已成交数量: {order_detail.get('FilledQuantity', 'N/A')}")
                        if order_detail.get('CreateTimestamp'):
                            create_time = datetime.fromtimestamp(order_detail['CreateTimestamp'] / 1000)
                            print(f"  创建时间: {create_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print("  没有找到订单")
            else:
                print(f"⚠️ 查询失败: {orders.get('ErrMsg', 'Unknown error')}")
        else:
            print(f"⚠️ API返回格式异常: {type(orders)}")
        
        return orders
    except Exception as e:
        print(f"❌ 查询订单失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def get_current_balance(client: RoostooClient) -> Dict[str, Any]:
    """获取当前余额"""
    try:
        print("\n" + "=" * 80)
        print("当前账户余额")
        print("=" * 80)
        
        balance = client.get_balance()
        
        if isinstance(balance, dict) and balance.get("Success"):
            wallet = balance.get("Wallet", {})
            print("✓ 余额查询成功:")
            
            for currency, amounts in wallet.items():
                free = amounts.get("Free", 0)
                lock = amounts.get("Lock", 0)
                total = free + lock
                print(f"  {currency}:")
                print(f"    可用: {free}")
                print(f"    锁定: {lock}")
                print(f"    总计: {total}")
        else:
            print(f"⚠️ 余额查询失败: {balance.get('ErrMsg', 'Unknown error')}")
        
        return balance
    except Exception as e:
        print(f"❌ 查询余额失败: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    parser = argparse.ArgumentParser(description="测试决策执行情况")
    parser.add_argument("--hours", type=int, default=24, help="查看最近N小时的决策（默认24）")
    parser.add_argument("--agent", type=str, default=None, help="只查看指定Agent的决策")
    parser.add_argument("--orders", action="store_true", help="同时查询订单历史")
    parser.add_argument("--balance", action="store_true", help="显示当前余额")
    parser.add_argument("--db", type=str, default="decisions.db", help="决策数据库路径")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("决策执行情况测试")
    print("=" * 80)
    print(f"时间范围: 最近 {args.hours} 小时")
    if args.agent:
        print(f"Agent过滤: {args.agent}")
    print(f"数据库: {args.db}")
    print("=" * 80)
    
    # 检查数据库是否存在
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        print("   请先运行bot生成决策数据")
        return
    
    # 1. 从数据库获取决策
    print("\n[1] 从数据库获取决策...")
    decisions = get_recent_decisions(str(db_path), hours=args.hours, agent_name=args.agent)
    print(f"✓ 找到 {len(decisions)} 个决策")
    
    if not decisions:
        print("\n⚠️ 没有找到决策记录")
        print("   可能的原因:")
        print("   1. bot还没有生成任何决策")
        print("   2. 时间范围太短")
        print("   3. Agent名称不匹配")
        return
    
    # 2. 获取执行结果
    print("\n[2] 获取执行结果...")
    decision_ids = [d['id'] for d in decisions]
    execution_results = get_execution_results(str(db_path), decision_ids)
    print(f"✓ 找到 {len(execution_results)} 个执行结果")
    
    # 3. 显示决策和执行结果
    print("\n[3] 决策详情:")
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for decision in decisions:
        decision_id = decision['id']
        execution_result = execution_results.get(decision_id)
        
        print_decision_summary(decision, execution_result)
        
        # 统计
        if execution_result:
            status = execution_result.get('status', 'unknown')
            if status == 'success':
                success_count += 1
            elif status == 'failed':
                failed_count += 1
            elif status == 'skipped':
                skipped_count += 1
        elif decision['status'] == 'pending':
            skipped_count += 1
    
    # 4. 统计摘要
    print("\n" + "=" * 80)
    print("统计摘要")
    print("=" * 80)
    print(f"总决策数: {len(decisions)}")
    print(f"成功执行: {success_count}")
    print(f"执行失败: {failed_count}")
    print(f"跳过/等待: {skipped_count}")
    if len(decisions) > 0:
        success_rate = (success_count / len(decisions)) * 100
        print(f"成功率: {success_rate:.2f}%")
    print("=" * 80)
    
    # 5. 从API查询订单（如果启用）
    if args.orders:
        try:
            client = RoostooClient()
            query_orders_from_api(client)
        except Exception as e:
            print(f"❌ 无法连接API: {e}")
    
    # 6. 显示当前余额（如果启用）
    if args.balance:
        try:
            client = RoostooClient()
            get_current_balance(client)
        except Exception as e:
            print(f"❌ 无法连接API: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    print("\n💡 提示:")
    print("  - 如果看到 'status: success' 和 'order_id'，说明决策已成功执行")
    print("  - 如果看到 'status: failed' 或 'status: skipped'，说明决策未执行")
    print("  - 使用 --orders 选项可以查看API中的实际订单")
    print("  - 使用 --balance 选项可以查看当前账户余额变化")
    print("=" * 80)


if __name__ == "__main__":
    main()


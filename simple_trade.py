#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最简单的交易脚本
直接执行一个买入订单，不依赖复杂的Agent系统

使用方法:
    python simple_trade.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.roostoo_client import RoostooClient


def main():
    """主函数：执行一个简单的买入订单"""
    print("=" * 80)
    print("简单交易脚本")
    print("=" * 80)
    
    # 1. 检查配置
    api_key = os.getenv("ROOSTOO_API_KEY")
    secret_key = os.getenv("ROOSTOO_SECRET_KEY")
    api_url = os.getenv("ROOSTOO_API_URL", "https://mock-api.roostoo.com")
    
    if not api_key or not secret_key:
        print("❌ 错误: 请设置 ROOSTOO_API_KEY 和 ROOSTOO_SECRET_KEY")
        print("   在 .env 文件中设置这些变量")
        return False
    
    print(f"✓ API配置检查通过")
    print(f"  API URL: {api_url}")
    print(f"  API Key: {api_key[:10]}...")
    
    # 2. 创建客户端
    try:
        client = RoostooClient()
        print("✓ RoostooClient 创建成功")
    except Exception as e:
        print(f"❌ 创建客户端失败: {e}")
        return False
    
    # 3. 获取当前价格
    print("\n获取当前市场价格...")
    try:
        ticker = client.get_ticker(pair="BTC/USD")
        print(f"✓ 市场数据获取成功")
        
        # 提取价格
        current_price = None
        if isinstance(ticker, dict):
            data = ticker.get("Data", ticker.get("data", ticker))
            if isinstance(data, dict):
                pair_data = data.get("BTC/USD", data)
                if isinstance(pair_data, dict):
                    current_price = pair_data.get("LastPrice") or pair_data.get("price")
        
        if current_price:
            current_price = float(current_price)
            print(f"  当前BTC价格: ${current_price:.2f}")
        else:
            print("⚠️  无法从响应中提取价格，使用默认值 100000")
            current_price = 100000.0
    except Exception as e:
        print(f"⚠️  获取价格失败: {e}，使用默认值 100000")
        current_price = 100000.0
    
    # 4. 设置交易参数
    pair = "BTC/USD"
    side = "BUY"  # 买入
    position_size_usd = 500.0  # 买入金额：500 USD
    quantity = position_size_usd / current_price  # 计算BTC数量
    quantity = round(quantity, 8)  # 保留8位小数
    
    print("\n" + "=" * 80)
    print("交易参数")
    print("=" * 80)
    print(f"  交易对: {pair}")
    print(f"  方向: {side}")
    print(f"  数量: {quantity:.8f} BTC")
    print(f"  金额: {position_size_usd:.2f} USD")
    print(f"  参考价格: {current_price:.2f} USD")
    print(f"  订单类型: MARKET (市价单)")
    print("=" * 80)
    
    # 5. 执行交易
    print("\n执行交易...")
    try:
        # 市价单（不指定价格）
        response = client.place_order(
            pair=pair,
            side=side,
            quantity=quantity
        )
        
        print("=" * 80)
        print("✓ 订单已提交")
        print("=" * 80)
        print(f"API响应: {response}")
        print("=" * 80)
        
        # 检查响应
        if isinstance(response, dict):
            if "code" in response:
                if response["code"] == 0 or response["code"] == 200:
                    print("✓ 订单执行成功")
                else:
                    print(f"⚠️  订单响应代码: {response['code']}")
                    print(f"   消息: {response.get('message', 'N/A')}")
            elif "order_id" in response or "data" in response:
                print("✓ 订单已创建")
            else:
                print("⚠️  订单响应格式异常，但已发送到API")
        
        return True
        
    except Exception as e:
        print("=" * 80)
        print("❌ 交易失败")
        print("=" * 80)
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        import traceback
        print("\n错误堆栈:")
        traceback.print_exc()
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("\n✓ 交易脚本执行完成")
        sys.exit(0)
    else:
        print("\n❌ 交易脚本执行失败")
        sys.exit(1)


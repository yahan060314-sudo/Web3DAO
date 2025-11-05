# data_fetcher.py

import time
import json
from roostoo_client import RoostooClient

def pretty_print(data: dict):
    """以美观的JSON格式打印字典。"""
    print(json.dumps(data, indent=4, ensure_ascii=False))

def run_data_fetcher():
    """
    一个示例数据获取器的主函数。
    它会执行一次性信息获取，然后进入一个循环，定期获取行情和余额。
    """
    print("--- 启动Roostoo数据获取器 ---")
    
    try:
        # 1. 初始化客户端
        # RoostooClient会自动从.env文件中加载API密钥
        client = RoostooClient()
        print("客户端初始化成功。")
    except ValueError as e:
        print(f"客户端初始化失败: {e}")
        return # 无法继续，退出程序

    # 2. 执行一次性调用，获取基本信息
    print("\n--- [一次性任务] 获取服务器时间和交易所信息 ---")
    try:
        server_time = client.check_server_time()
        print("服务器时间:")
        pretty_print(server_time)

        exchange_info = client.get_exchange_info()
        print("\n交易所信息 (部分示例):")
        # 只打印前两个交易对的信息作为示例
        if 'data' in exchange_info and 'TradePairs' in exchange_info['data']:
            sample_pairs = list(exchange_info['data']['TradePairs'].items())[:2]
            pretty_print(dict(sample_pairs))
        else:
            pretty_print(exchange_info)
            
    except Exception as e:
        print(f"获取基本信息时出错: {e}")

    # 3. 进入循环，定期获取动态数据
    print("\n--- [循环任务] 开始每5秒获取一次Ticker和余额 ---")
    print("按 Ctrl+C 停止程序。")
    
    fetch_interval_seconds = 5
    while True:
        try:
            print(f"\n--- {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            # 获取BTC/USD的Ticker信息
            print("正在获取 BTC/USD Ticker...")
            btc_ticker = client.get_ticker(pair="BTC/USD")
            pretty_print(btc_ticker)
            
            # 获取账户余额
            print("\n正在获取账户余额...")
            balance = client.get_balance()
            pretty_print(balance)

            print(f"------------------------------------")
            print(f"下一次获取将在 {fetch_interval_seconds} 秒后...")
            time.sleep(fetch_interval_seconds)

        except KeyboardInterrupt:
            print("\n程序被用户中断。正在退出...")
            break
        except Exception as e:
            # 捕获在循环中可能发生的任何请求错误，防止程序崩溃
            print(f"在数据获取循环中发生错误: {e}")
            print(f"将在 {fetch_interval_seconds} 秒后重试...")
            time.sleep(fetch_interval_seconds)

if __name__ == "__main__":
    run_data_fetcher()
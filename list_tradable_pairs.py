import os
import sys
from typing import List
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Ensure project imports work when running directly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from api.roostoo_client import RoostooClient


def _to_pair_with_slash(symbol: str) -> str:
    s = str(symbol).strip().upper()
    if "/" in s:
        return s
    if s.endswith("USDT"):
        base = s[:-4]
        return f"{base}/USD"
    if s.endswith("USD"):
        base = s[:-3]
        return f"{base}/USD"
    if len(s) == 6:
        return f"{s[:3]}/{s[3:]}"
    return s


def load_all_tradeable_usd_pairs() -> List[str]:
    """
    从 exchangeInfo 动态加载可交易的 USD 计价交易对，统一为 'BASE/USD'。
    支持多种API响应格式，解析失败时回退为 ['BTC/USD']。
    """
    try:
        client = RoostooClient()
        print(f"[ListPairs] Using API: {client.base_url}")
        info = client.get_exchange_info()
        
        # Debug: print response structure
        print(f"[ListPairs] Response keys: {list(info.keys()) if isinstance(info, dict) else 'Not a dict'}")
        
        candidates = []
        if isinstance(info, dict):
            # 方法1: 检查 data.TradePairs (Roostoo API的标准格式)
            data = info.get("data", info)
            if isinstance(data, dict) and "TradePairs" in data:
                trade_pairs = data["TradePairs"]
                if isinstance(trade_pairs, dict):
                    # TradePairs 是字典，key就是交易对名称
                    for pair_key in trade_pairs.keys():
                        candidates.append(_to_pair_with_slash(pair_key))
                elif isinstance(trade_pairs, list):
                    # TradePairs 是列表
                    for item in trade_pairs:
                        if isinstance(item, str):
                            candidates.append(_to_pair_with_slash(item))
                        elif isinstance(item, dict):
                            pair_val = item.get("Pair") or item.get("pair") or item.get("Symbol") or item.get("symbol")
                            if pair_val:
                                candidates.append(_to_pair_with_slash(pair_val))
            
            # 方法2: 检查顶层的 TradePairs
            if "TradePairs" in info and isinstance(info["TradePairs"], dict):
                for pair_key in info["TradePairs"].keys():
                    candidates.append(_to_pair_with_slash(pair_key))
            
            # 方法3: 检查 Symbols (某些API格式)
            if "Symbols" in info and isinstance(info["Symbols"], list):
                for item in info["Symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("Pair") or item.get("pair") or item.get("Symbol") or item.get("symbol")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            
            # 方法4: 检查 symbols (小写)
            if "symbols" in info and isinstance(info["symbols"], list):
                for item in info["symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("symbol") or item.get("pair")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            
            # 方法5: 检查 Pairs
            if "Pairs" in info and isinstance(info["Pairs"], list):
                for s in info["Pairs"]:
                    candidates.append(_to_pair_with_slash(s))
        
        # 仅保留 USD 计价，去重且保持顺序
        seen = set()
        usd_pairs = []
        for p in candidates:
            normalized = _to_pair_with_slash(p)
            if normalized.endswith("/USD") and normalized not in seen:
                seen.add(normalized)
                usd_pairs.append(normalized)
        
        if not usd_pairs:
            print(f"[ListPairs] ⚠️ 未找到USD交易对，使用默认值 BTC/USD")
            print(f"[ListPairs] Debug: candidates = {candidates[:10]}...")
            usd_pairs = ["BTC/USD"]
        
        return usd_pairs
    except Exception as e:
        import traceback
        print(f"[ListPairs] Failed to load exchange info: {e}")
        traceback.print_exc()
        return ["BTC/USD"]


def main():
    # Debug: Check environment variables
    api_url = os.getenv("ROOSTOO_API_URL")
    print(f"[ListPairs] Environment ROOSTOO_API_URL: {api_url if api_url else 'Not set'}")
    
    usd_pairs = load_all_tradeable_usd_pairs()
    print("========================================")
    print("Tradable USD pairs (normalized):")
    print("========================================")
    print(f"Count: {len(usd_pairs)}")
    for p in usd_pairs:
        print(p)


if __name__ == "__main__":
    main()



import os
import sys
from typing import List

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
    try:
        client = RoostooClient()
        info = client.get_exchange_info()
        candidates = []
        if isinstance(info, dict):
            if "Symbols" in info and isinstance(info["Symbols"], list):
                for item in info["Symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("Pair") or item.get("pair") or item.get("Symbol") or item.get("symbol")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            elif "symbols" in info and isinstance(info["symbols"], list):
                for item in info["symbols"]:
                    pair_val = None
                    if isinstance(item, dict):
                        pair_val = item.get("symbol") or item.get("pair")
                    elif isinstance(item, str):
                        pair_val = item
                    if pair_val:
                        candidates.append(_to_pair_with_slash(pair_val))
            elif "Pairs" in info and isinstance(info["Pairs"], list):
                for s in info["Pairs"]:
                    candidates.append(_to_pair_with_slash(s))
        seen = set()
        usd_pairs = []
        for p in candidates:
            if p.endswith("/USD") and p not in seen:
                seen.add(p)
                usd_pairs.append(p)
        if not usd_pairs:
            usd_pairs = ["BTC/USD"]
        return usd_pairs
    except Exception as e:
        print(f"[ListPairs] Failed to load exchange info: {e}")
        return ["BTC/USD"]


def main():
    usd_pairs = load_all_tradeable_usd_pairs()
    print("========================================")
    print("Tradable USD pairs (normalized):")
    print("========================================")
    print(f"Count: {len(usd_pairs)}")
    for p in usd_pairs:
        print(p)


if __name__ == "__main__":
    main()



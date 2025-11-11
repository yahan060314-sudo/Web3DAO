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

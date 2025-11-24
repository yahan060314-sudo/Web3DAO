import os
import sys
from typing import Optional, Dict, Any

# Ensure project imports work when running directly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from api.roostoo_client import RoostooClient


def get_account_balance(client: Optional[RoostooClient] = None) -> Dict[str, Any]:
    client = client or RoostooClient()
    print("[ManualBalance] Fetching account balance...")
    result = client.get_balance()
    print("[ManualBalance] Balance result:")
    print(result)
    return result


if __name__ == "__main__":
    get_account_balance()


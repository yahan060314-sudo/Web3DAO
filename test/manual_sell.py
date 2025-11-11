import os
import sys
import argparse
from typing import Optional

# Ensure project package imports work when running this script directly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from api.roostoo_client import RoostooClient


def place_market_sell(
    symbol: str,
    quantity: float,
    client: Optional[RoostooClient] = None
) -> None:
    """
    Place a MARKET sell order using RoostooClient.
    """
    client = client or RoostooClient()
    pair = symbol if "/" in symbol else f"{symbol[:3]}/{symbol[3:]}"
    side = "SELL"
    order_type = "MARKET"

    print("========================================")
    print("Manual Sell Order")
    print("========================================")
    print(f"Pair     : {pair}")
    print(f"Side     : {side}")
    print(f"Quantity : {quantity}")
    print(f"Type     : {order_type}")
    print("========================================")

    resp = client.place_order(
        pair=pair,
        side=side,
        quantity=quantity,
        order_type=order_type
    )
    print("✓ Order placed successfully")
    print(resp)


def main():
    parser = argparse.ArgumentParser(
        description="Place a MARKET sell order via RoostooClient."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC/USD",
        help="Trading pair symbol, e.g., BTC/USD or BTCUSDT (default: BTC/USD)"
    )
    parser.add_argument(
        "--quantity",
        type=float,
        required=True,
        help="Quantity to sell (base asset amount), e.g., 0.005"
    )
    args = parser.parse_args()

    place_market_sell(
        symbol=args.symbol,
        quantity=args.quantity
    )


if __name__ == "__main__":
    main()



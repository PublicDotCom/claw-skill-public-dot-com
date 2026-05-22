import argparse
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        TimeInForce,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        TimeInForce,
    )


SPREAD_METHOD_MAP = {
    "CALL_CREDIT": "place_call_credit_spread",
    "CALL_DEBIT": "place_call_debit_spread",
    "PUT_CREDIT": "place_put_credit_spread",
    "PUT_DEBIT": "place_put_debit_spread",
}


def place_spread(
    spread_type,
    sell_contract_osi,
    buy_contract_osi,
    quantity,
    limit_price,
    time_in_force="DAY",
    expiration_time=None,
    account_id=None,
):
    """
    Place a live vertical option spread order using the OSI-direct helpers
    added in publicdotcom-py 0.1.11. The SDK generates the idempotency key.

    Args:
        spread_type: One of CALL_CREDIT, CALL_DEBIT, PUT_CREDIT, PUT_DEBIT
        sell_contract_osi: OSI symbol of the leg to sell
        buy_contract_osi: OSI symbol of the leg to buy
        quantity: Number of spread contracts (integer)
        limit_price: Net debit/credit as a positive Decimal
        time_in_force: DAY (default) or GTD
        account_id: Account ID (optional; falls back to env var)
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)
    if spread_type not in SPREAD_METHOD_MAP:
        print(f"Error: Invalid spread type '{spread_type}'. Must be one of: {', '.join(SPREAD_METHOD_MAP)}")
        sys.exit(1)

    time_in_force_map = {"DAY": TimeInForce.DAY, "GTD": TimeInForce.GTD}
    if time_in_force not in time_in_force_map:
        print(f"Error: Invalid time-in-force '{time_in_force}'. Must be DAY or GTD.")
        sys.exit(1)
    if time_in_force == "GTD" and not expiration_time:
        print("Error: --expiration-time YYYY-MM-DD is required when --time-in-force is GTD")
        sys.exit(1)

    expiration_time_dt = None
    if expiration_time:
        expiration_time_dt = datetime.fromisoformat(expiration_time)
        if expiration_time_dt.tzinfo is None:
            expiration_time_dt = expiration_time_dt.replace(tzinfo=timezone.utc)

    try:
        client = create_client(secret, account_id)

        method = getattr(client, SPREAD_METHOD_MAP[spread_type])
        kwargs = {
            "sell_contract_osi": sell_contract_osi,
            "buy_contract_osi": buy_contract_osi,
            "quantity": int(quantity),
            "limit_price": Decimal(str(limit_price)),
            "time_in_force": time_in_force_map[time_in_force],
        }
        if expiration_time_dt is not None:
            kwargs["expiration_time"] = expiration_time_dt
        new_order = method(**kwargs)

        print("Spread Order Placed Successfully!")
        print("-" * 40)
        print(f"Order ID:     {new_order.order_id}")
        print(f"Spread Type:  {spread_type}")
        print(f"Sell Leg:     {sell_contract_osi}")
        print(f"Buy Leg:      {buy_contract_osi}")
        print(f"Quantity:     {quantity}")
        print(f"Limit Price:  ${limit_price}")
        print(f"Time In Force: {time_in_force}")
        print("-" * 40)

        client.close()
    except Exception as e:
        print(f"Error placing spread order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Place a vertical option spread order (OSI-direct helpers from SDK 0.1.11)",
        epilog="Spread types:\n"
               "  CALL_CREDIT - Bear Call Spread: sell lower-strike CALL, buy higher-strike CALL\n"
               "  CALL_DEBIT  - Bull Call Spread: buy lower-strike CALL, sell higher-strike CALL\n"
               "  PUT_CREDIT  - Bull Put Spread:  sell higher-strike PUT, buy lower-strike PUT\n"
               "  PUT_DEBIT   - Bear Put Spread:  buy higher-strike PUT, sell lower-strike PUT\n\n"
               "Examples:\n"
               "  python3 place_spread.py --spread-type CALL_DEBIT \\\n"
               "    --sell AAPL251219C00200000 --buy AAPL251219C00190000 \\\n"
               "    --quantity 1 --limit-price 3.00",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--spread-type", required=True, choices=list(SPREAD_METHOD_MAP.keys()))
    parser.add_argument("--sell", dest="sell_contract_osi", required=True, help="OSI symbol of the leg to sell")
    parser.add_argument("--buy", dest="buy_contract_osi", required=True, help="OSI symbol of the leg to buy")
    parser.add_argument("--quantity", type=int, required=True, help="Number of spread contracts")
    parser.add_argument(
        "--limit-price",
        type=float,
        required=True,
        help="Net debit/credit as a positive value (SDK negates credits internally)",
    )
    parser.add_argument("--time-in-force", choices=["DAY", "GTD"], default="DAY")
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. YYYY-MM-DD or ISO 8601. Max 90 days out.",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()

    place_spread(
        spread_type=args.spread_type,
        sell_contract_osi=args.sell_contract_osi,
        buy_contract_osi=args.buy_contract_osi,
        quantity=args.quantity,
        limit_price=args.limit_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        account_id=args.account_id,
    )

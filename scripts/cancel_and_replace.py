import argparse
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        CancelAndReplaceRequest,
        OrderExpirationRequest,
        OrderType,
        TimeInForce,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        CancelAndReplaceRequest,
        OrderExpirationRequest,
        OrderType,
        TimeInForce,
    )


def _build_expiration(time_in_force, expiration_time):
    if time_in_force == "GTD":
        if not expiration_time:
            raise ValueError("--expiration-time YYYY-MM-DD is required when --time-in-force is GTD")
        exp = datetime.fromisoformat(expiration_time)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return OrderExpirationRequest(time_in_force=TimeInForce.GTD, expiration_time=exp)
    return OrderExpirationRequest(time_in_force=TimeInForce.DAY)


def cancel_and_replace(
    order_id,
    order_type,
    quantity=None,
    limit_price=None,
    stop_price=None,
    time_in_force="DAY",
    expiration_time=None,
    account_id=None,
):
    """
    Atomically cancel an existing order and replace it with one that has
    new parameters (e.g. updated limit price or quantity).
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    if order_type in ("LIMIT", "STOP_LIMIT") and limit_price is None:
        print(f"Error: --limit-price is required for {order_type} orders.")
        sys.exit(1)
    if order_type in ("STOP", "STOP_LIMIT") and stop_price is None:
        print(f"Error: --stop-price is required for {order_type} orders.")
        sys.exit(1)

    order_type_map = {
        "LIMIT": OrderType.LIMIT,
        "MARKET": OrderType.MARKET,
        "STOP": OrderType.STOP,
        "STOP_LIMIT": OrderType.STOP_LIMIT,
    }

    try:
        expiration = _build_expiration(time_in_force, expiration_time)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        client = create_client(secret, account_id)

        req_kwargs = {
            "order_id": order_id,
            "request_id": str(uuid.uuid4()),
            "order_type": order_type_map[order_type],
            "expiration": expiration,
        }
        if quantity is not None:
            req_kwargs["quantity"] = Decimal(str(quantity))
        if limit_price is not None:
            req_kwargs["limit_price"] = Decimal(str(limit_price))
        if stop_price is not None:
            req_kwargs["stop_price"] = Decimal(str(stop_price))

        request = CancelAndReplaceRequest(**req_kwargs)
        new_order = client.cancel_and_replace_order(request=request, account_id=account_id)

        print("=" * 60)
        print("CANCEL & REPLACE SUBMITTED")
        print("=" * 60)
        print(f"\n  Original Order ID: {order_id}")
        print(f"  Replacement Order ID: {new_order.order_id}")
        print(f"  Order Type:    {order_type}")
        print(f"  Time in Force: {time_in_force}")
        if quantity is not None:
            print(f"  Quantity:      {quantity}")
        if limit_price is not None:
            print(f"  Limit Price:   ${limit_price}")
        if stop_price is not None:
            print(f"  Stop Price:    ${stop_price}")
        print("\n  Use get_order.py --order-id <id> to check the replacement's status.")
        print("\n" + "=" * 60)

        client.close()
    except Exception as e:
        print(f"Error cancelling and replacing order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cancel an existing order and replace it with one that has new parameters",
        epilog="Example:\n"
               "  python3 cancel_and_replace.py --order-id 345d3e58-5ba3-401a-ac89-1b756332cc94 \\\n"
               "    --order-type LIMIT --quantity 10 --limit-price 230.00",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--order-id", required=True, help="UUID of the existing order to cancel and replace")
    parser.add_argument(
        "--order-type",
        required=True,
        choices=["LIMIT", "MARKET", "STOP", "STOP_LIMIT"],
        help="Type of the replacement order",
    )
    parser.add_argument("--quantity", type=float, help="New quantity (omit to keep original)")
    parser.add_argument("--limit-price", type=float, help="New limit price (required for LIMIT/STOP_LIMIT)")
    parser.add_argument("--stop-price", type=float, help="New stop price (required for STOP/STOP_LIMIT)")
    parser.add_argument("--time-in-force", choices=["DAY", "GTD"], default="DAY")
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. Format: YYYY-MM-DD or ISO 8601 timestamp. Max 90 days out.",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()
    cancel_and_replace(
        order_id=args.order_id,
        order_type=args.order_type,
        quantity=args.quantity,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        account_id=args.account_id,
    )

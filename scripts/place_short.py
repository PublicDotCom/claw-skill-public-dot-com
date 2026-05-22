import argparse
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        OrderType,
        TimeInForce,
        EquityMarketSession,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        OrderType,
        TimeInForce,
        EquityMarketSession,
    )


def place_short(
    symbol,
    quantity,
    order_type="MARKET",
    limit_price=None,
    stop_price=None,
    time_in_force="DAY",
    expiration_time=None,
    session=None,
    account_id=None,
):
    """
    Place a quantity-based equity short-sale order using the helper added in
    publicdotcom-py 0.1.11. Short intent is SELL + openCloseIndicator=OPEN.
    The SDK generates the idempotency key.
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    order_type_map = {
        "MARKET": OrderType.MARKET,
        "LIMIT": OrderType.LIMIT,
        "STOP": OrderType.STOP,
        "STOP_LIMIT": OrderType.STOP_LIMIT,
    }
    time_in_force_map = {"DAY": TimeInForce.DAY, "GTD": TimeInForce.GTD}
    session_map = {"CORE": EquityMarketSession.CORE, "EXTENDED": EquityMarketSession.EXTENDED}

    if order_type in ("LIMIT", "STOP_LIMIT") and limit_price is None:
        print(f"Error: --limit-price is required for {order_type} orders.")
        sys.exit(1)
    if order_type in ("STOP", "STOP_LIMIT") and stop_price is None:
        print(f"Error: --stop-price is required for {order_type} orders.")
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

        kwargs = {
            "symbol": symbol,
            "quantity": Decimal(str(quantity)),
            "order_type": order_type_map[order_type],
            "time_in_force": time_in_force_map[time_in_force],
        }
        if expiration_time_dt is not None:
            kwargs["expiration_time"] = expiration_time_dt
        if limit_price is not None:
            kwargs["limit_price"] = Decimal(str(limit_price))
        if stop_price is not None:
            kwargs["stop_price"] = Decimal(str(stop_price))
        if session is not None:
            kwargs["equity_market_session"] = session_map[session]

        new_order = client.place_short_order(**kwargs)

        print("Short-Sale Order Placed Successfully!")
        print("-" * 40)
        print(f"Order ID:      {new_order.order_id}")
        print(f"Symbol:        {symbol}")
        print(f"Quantity:      {quantity} shares (SHORT)")
        print(f"Order Type:    {order_type}")
        if limit_price is not None:
            print(f"Limit Price:   ${limit_price}")
        if stop_price is not None:
            print(f"Stop Price:    ${stop_price}")
        print(f"Time In Force: {time_in_force}")
        if session is not None:
            print(f"Session:       {session}")
        print("-" * 40)

        client.close()
    except Exception as e:
        print(f"Error placing short order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Place an equity short-sale order (helper from SDK 0.1.11)",
        epilog="Examples:\n"
               "  python3 place_short.py --symbol TSLA --quantity 10\n"
               "  python3 place_short.py --symbol TSLA --quantity 10 --order-type LIMIT --limit-price 245.00",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--symbol", required=True, help="Equity symbol to short")
    parser.add_argument("--quantity", type=float, required=True, help="Number of shares to short")
    parser.add_argument(
        "--order-type",
        choices=["MARKET", "LIMIT", "STOP", "STOP_LIMIT"],
        default="MARKET",
    )
    parser.add_argument("--limit-price", type=float, help="Required for LIMIT/STOP_LIMIT")
    parser.add_argument("--stop-price", type=float, help="Required for STOP/STOP_LIMIT")
    parser.add_argument("--time-in-force", choices=["DAY", "GTD"], default="DAY")
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. YYYY-MM-DD or ISO 8601. Max 90 days out.",
    )
    parser.add_argument("--session", choices=["CORE", "EXTENDED"])
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()

    place_short(
        symbol=args.symbol,
        quantity=args.quantity,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        session=args.session,
        account_id=args.account_id,
    )

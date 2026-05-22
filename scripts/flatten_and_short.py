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


def flatten_and_short(
    symbol,
    short_quantity,
    order_type="MARKET",
    limit_price=None,
    stop_price=None,
    time_in_force="DAY",
    expiration_time=None,
    session=None,
    flatten_timeout=60.0,
    account_id=None,
):
    """
    If the account is long `symbol`, flatten that position first, then open
    a short. Two-order workflow — not atomic. New in publicdotcom-py 0.1.15
    (marked experimental in the SDK).
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
    if time_in_force not in time_in_force_map:
        print(f"Error: Invalid --time-in-force '{time_in_force}'. Must be DAY or GTD.")
        sys.exit(1)
    if time_in_force == "GTD" and not expiration_time:
        print("Error: --expiration-time YYYY-MM-DD is required when --time-in-force is GTD")
        sys.exit(1)

    expiration_time_dt = None
    if expiration_time:
        expiration_time_dt = datetime.fromisoformat(expiration_time)
        if expiration_time_dt.tzinfo is None:
            expiration_time_dt = expiration_time_dt.replace(tzinfo=timezone.utc)

    session_map = {"CORE": EquityMarketSession.CORE, "EXTENDED": EquityMarketSession.EXTENDED}

    if order_type in ("LIMIT", "STOP_LIMIT") and limit_price is None:
        print(f"Error: --limit-price is required for {order_type} orders.")
        sys.exit(1)
    if order_type in ("STOP", "STOP_LIMIT") and stop_price is None:
        print(f"Error: --stop-price is required for {order_type} orders.")
        sys.exit(1)

    try:
        client = create_client(secret, account_id)

        kwargs = {
            "symbol": symbol,
            "short_quantity": Decimal(str(short_quantity)),
            "order_type": order_type_map[order_type],
            "time_in_force": time_in_force_map[time_in_force],
            "flatten_timeout": flatten_timeout,
            "account_id": account_id,
        }
        if expiration_time_dt is not None:
            kwargs["expiration_time"] = expiration_time_dt
        if limit_price is not None:
            kwargs["limit_price"] = Decimal(str(limit_price))
        if stop_price is not None:
            kwargs["stop_price"] = Decimal(str(stop_price))
        if session:
            kwargs["equity_market_session"] = session_map[session]

        result = client.flatten_and_go_short(**kwargs)

        print("=" * 70)
        print("FLATTEN-AND-GO-SHORT")
        print("=" * 70)
        print(f"\n  Symbol:                     {symbol}")
        print(f"  Initial Long Quantity:      {result.initial_position_quantity}")
        if result.flatten_order is not None:
            print(f"  Flatten Order ID:           {result.flatten_order.order_id}")
            if result.flatten_filled_order is not None:
                print(f"  Flatten Status:             {result.flatten_filled_order.status.value}")
                if result.flatten_filled_order.average_price is not None:
                    print(f"  Flatten Avg Price:          ${result.flatten_filled_order.average_price}")
        else:
            print("  Flatten Order:              none (already flat or short)")
        print(f"\n  Short Order ID:             {result.short_order.order_id}")
        print(f"  Short Quantity:             {short_quantity}")
        print(f"  Short Order Type:           {order_type}")
        if limit_price is not None:
            print(f"  Short Limit Price:          ${limit_price}")
        if stop_price is not None:
            print(f"  Short Stop Price:           ${stop_price}")
        print(f"  Time in Force:              {time_in_force}")
        print("\n" + "=" * 70)

        client.close()
    except Exception as e:
        print(f"Error running flatten-and-go-short: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Flatten an existing long equity position (if any), then open a short. EXPERIMENTAL — not atomic.",
        epilog="Example:\n"
               "  python3 flatten_and_short.py --symbol TSLA --short-quantity 10\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--symbol", required=True, help="Equity symbol")
    parser.add_argument("--short-quantity", type=float, required=True, help="Number of shares to short")
    parser.add_argument(
        "--order-type",
        choices=["MARKET", "LIMIT", "STOP", "STOP_LIMIT"],
        default="MARKET",
        help="Short order type (default MARKET)",
    )
    parser.add_argument("--limit-price", type=float, help="Limit price (required for LIMIT/STOP_LIMIT)")
    parser.add_argument("--stop-price", type=float, help="Stop price (required for STOP/STOP_LIMIT)")
    parser.add_argument("--time-in-force", choices=["DAY", "GTD"], default="DAY")
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. YYYY-MM-DD or ISO 8601. Max 90 days out.",
    )
    parser.add_argument("--session", choices=["CORE", "EXTENDED"], help="Equity market session")
    parser.add_argument(
        "--flatten-timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for the flatten order to fill before aborting (default 60)",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()
    flatten_and_short(
        symbol=args.symbol,
        short_quantity=args.short_quantity,
        order_type=args.order_type,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        session=args.session,
        flatten_timeout=args.flatten_timeout,
        account_id=args.account_id,
    )

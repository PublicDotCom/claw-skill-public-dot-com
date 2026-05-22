import argparse
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        MultilegOrderRequest,
        OrderLegRequest,
        LegInstrument,
        LegInstrumentType,
        OrderSide,
        OrderType,
        OpenCloseIndicator,
        OrderExpirationRequest,
        TimeInForce,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        MultilegOrderRequest,
        OrderLegRequest,
        LegInstrument,
        LegInstrumentType,
        OrderSide,
        OrderType,
        OpenCloseIndicator,
        OrderExpirationRequest,
        TimeInForce,
    )


def parse_leg(spec):
    """SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO] — see preflight_multileg.py for details."""
    parts = spec.split(":")
    if len(parts) < 3:
        raise ValueError(f"Leg '{spec}' missing fields. Expected SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO]")
    symbol, leg_type_str, side_str = parts[0], parts[1].upper(), parts[2].upper()
    open_close_str = parts[3].upper() if len(parts) >= 4 and parts[3] else None
    ratio_str = parts[4] if len(parts) >= 5 and parts[4] else None

    if leg_type_str not in ("EQUITY", "OPTION"):
        raise ValueError(f"Leg type must be EQUITY or OPTION, got '{leg_type_str}'")
    if side_str not in ("BUY", "SELL"):
        raise ValueError(f"Leg side must be BUY or SELL, got '{side_str}'")

    leg_type = LegInstrumentType[leg_type_str]
    side = OrderSide[side_str]
    kwargs = {
        "instrument": LegInstrument(symbol=symbol, type=leg_type),
        "side": side,
    }
    if leg_type == LegInstrumentType.OPTION:
        if not open_close_str:
            raise ValueError(f"Leg '{spec}': OPEN_CLOSE is required for OPTION legs")
        if open_close_str not in ("OPEN", "CLOSE"):
            raise ValueError(f"OPEN_CLOSE must be OPEN or CLOSE, got '{open_close_str}'")
        kwargs["open_close_indicator"] = OpenCloseIndicator[open_close_str]
    if ratio_str:
        kwargs["ratio_quantity"] = int(ratio_str)
    return OrderLegRequest(**kwargs)


def _build_expiration(time_in_force, expiration_time):
    if time_in_force == "GTD":
        if not expiration_time:
            raise ValueError("--expiration-time YYYY-MM-DD is required when --time-in-force is GTD")
        exp = datetime.fromisoformat(expiration_time)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return OrderExpirationRequest(time_in_force=TimeInForce.GTD, expiration_time=exp)
    return OrderExpirationRequest(time_in_force=TimeInForce.DAY)


def place_multileg(legs, quantity, limit_price, time_in_force="DAY", expiration_time=None, account_id=None):
    """
    Place a generic 2-6 leg options order (iron condor, butterfly, straddle, etc.).

    limit_price convention: positive for net debit, negative for net credit.
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)
    if not (2 <= len(legs) <= 6):
        print(f"Error: multi-leg orders require 2-6 legs (got {len(legs)}).")
        sys.exit(1)

    try:
        expiration = _build_expiration(time_in_force, expiration_time)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    try:
        client = create_client(secret, account_id)

        request = MultilegOrderRequest(
            order_id=str(uuid.uuid4()),
            type=OrderType.LIMIT,
            expiration=expiration,
            quantity=int(quantity),
            limit_price=Decimal(str(limit_price)),
            legs=legs,
        )
        new_order = client.place_multileg_order(request, account_id=account_id)

        print("Multi-Leg Order Placed!")
        print("-" * 40)
        print(f"Order ID:      {new_order.order_id}")
        print(f"Quantity:      {quantity}")
        print(f"Limit Price:   ${limit_price}  ({'debit' if Decimal(str(limit_price)) >= 0 else 'credit'})")
        print(f"Time in Force: {time_in_force}")
        print(f"Legs ({len(legs)}):")
        for i, leg in enumerate(legs, 1):
            oc = f" {leg.open_close_indicator.value}" if leg.open_close_indicator else ""
            ratio = f" x{leg.ratio_quantity}" if leg.ratio_quantity else ""
            print(f"  [{i}] {leg.side.value} {leg.instrument.symbol} ({leg.instrument.type.value}){oc}{ratio}")
        print("-" * 40)
        print("Use get_order.py --order-id ... to check status, or wait_for_fill.py to block on fill.")

        client.close()
    except Exception as e:
        print(f"Error placing multi-leg order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Place a generic 2-6 leg options order",
        epilog=(
            "See preflight_multileg.py --help for leg format details.\n"
            "Always run preflight_multileg.py with the same legs first to verify pricing.\n\n"
            "Example: Iron Condor on AAPL (net credit of $1.50)\n"
            "  python3 place_multileg.py --quantity 1 --limit-price -1.50 \\\n"
            "    --leg AAPL251219P00190000:OPTION:SELL:OPEN \\\n"
            "    --leg AAPL251219P00185000:OPTION:BUY:OPEN \\\n"
            "    --leg AAPL251219C00210000:OPTION:SELL:OPEN \\\n"
            "    --leg AAPL251219C00215000:OPTION:BUY:OPEN\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--leg",
        action="append",
        required=True,
        help="Leg spec SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO]. Repeat 2-6 times.",
    )
    parser.add_argument("--quantity", type=int, required=True)
    parser.add_argument(
        "--limit-price",
        type=float,
        required=True,
        help="Net limit price (positive = debit, negative = credit)",
    )
    parser.add_argument("--time-in-force", choices=["DAY", "GTD"], default="DAY")
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. YYYY-MM-DD or ISO 8601. Max 90 days out.",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()
    try:
        legs = [parse_leg(s) for s in args.leg]
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    place_multileg(
        legs=legs,
        quantity=args.quantity,
        limit_price=args.limit_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        account_id=args.account_id,
    )

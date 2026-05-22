import argparse
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        PreflightMultiLegRequest,
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
        PreflightMultiLegRequest,
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
    """
    Parse a leg spec of the form SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO].

    TYPE is EQUITY or OPTION. OPEN_CLOSE is required for OPTION legs (OPEN/CLOSE).
    RATIO is an integer (defaults: 1 for OPTION legs; 100 is typical for EQUITY).
    """
    parts = spec.split(":")
    if len(parts) < 3:
        raise ValueError(f"Leg '{spec}' missing fields. Expected SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO]")

    symbol = parts[0]
    leg_type_str = parts[1].upper()
    side_str = parts[2].upper()
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


def preflight_multileg(legs, quantity, limit_price, time_in_force="DAY", expiration_time=None, account_id=None):
    """
    Preflight a generic 2-6 leg options strategy (iron condor, butterfly,
    straddle, strangle, calendar, diagonal, ratio spread, etc.).

    Only LIMIT orders are supported by the API for multi-leg orders.

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

        request = PreflightMultiLegRequest(
            order_type=OrderType.LIMIT,
            expiration=expiration,
            quantity=int(quantity),
            limit_price=Decimal(str(limit_price)),
            legs=legs,
        )
        response = client.perform_multi_leg_preflight_calculation(request, account_id=account_id)

        print("=" * 70)
        print("MULTI-LEG PREFLIGHT")
        print("=" * 70)
        print(f"\n  Base Symbol:    {response.base_symbol}")
        if response.strategy_name:
            print(f"  Strategy:       {response.strategy_name}")
        print(f"  Quantity:       {quantity}")
        print(f"  Limit Price:    ${limit_price}  ({'debit' if Decimal(str(limit_price)) >= 0 else 'credit'})")
        print(f"  Time in Force:  {time_in_force}")
        print(f"  Legs:           {len(legs)}")
        for i, leg in enumerate(legs, 1):
            oc = f" {leg.open_close_indicator.value}" if leg.open_close_indicator else ""
            ratio = f" x{leg.ratio_quantity}" if leg.ratio_quantity else ""
            print(f"    [{i}] {leg.side.value} {leg.instrument.symbol} ({leg.instrument.type.value}){oc}{ratio}")

        print("\n  ESTIMATED IMPACT:")
        if response.estimated_cost is not None:
            print(f"    Estimated Cost:        ${response.estimated_cost}")
        if response.estimated_proceeds is not None:
            print(f"    Estimated Proceeds:    ${response.estimated_proceeds}")
        if response.order_value is not None:
            print(f"    Order Value:           ${response.order_value}")
        if response.buying_power_requirement is not None:
            print(f"    Buying Power Required: ${response.buying_power_requirement}")
        if response.estimated_commission is not None:
            print(f"    Est. Commission:       ${response.estimated_commission}")
        if response.estimated_index_option_fee is not None:
            print(f"    Index Option Fee:      ${response.estimated_index_option_fee}")
        if response.margin_requirement is not None:
            print(f"    Margin Requirement:    {response.margin_requirement}")
        if response.margin_impact is not None:
            print(f"    Margin Impact:         {response.margin_impact}")

        print("\n  PER-LEG DETAILS:")
        for i, leg_resp in enumerate(response.legs, 1):
            print(f"    [{i}] {leg_resp}")

        print("\n" + "=" * 70)
        client.close()
    except Exception as e:
        print(f"Error performing multi-leg preflight: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preflight a generic 2-6 leg options strategy",
        epilog=(
            "Leg format: SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO]\n"
            "  TYPE        = EQUITY | OPTION\n"
            "  SIDE        = BUY | SELL\n"
            "  OPEN_CLOSE  = OPEN | CLOSE  (required for OPTION legs)\n"
            "  RATIO       = optional integer ratio between legs\n\n"
            "limit-price convention: positive = net debit, negative = net credit.\n\n"
            "Examples:\n"
            "  Iron Condor on AAPL (sell put spread + sell call spread):\n"
            "    python3 preflight_multileg.py --quantity 1 --limit-price -1.50 \\\n"
            "      --leg AAPL251219P00190000:OPTION:SELL:OPEN \\\n"
            "      --leg AAPL251219P00185000:OPTION:BUY:OPEN \\\n"
            "      --leg AAPL251219C00210000:OPTION:SELL:OPEN \\\n"
            "      --leg AAPL251219C00215000:OPTION:BUY:OPEN\n\n"
            "  Long Straddle on AAPL:\n"
            "    python3 preflight_multileg.py --quantity 1 --limit-price 5.00 \\\n"
            "      --leg AAPL251219C00200000:OPTION:BUY:OPEN \\\n"
            "      --leg AAPL251219P00200000:OPTION:BUY:OPEN\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--leg",
        action="append",
        required=True,
        help="Leg spec SYMBOL:TYPE:SIDE[:OPEN_CLOSE][:RATIO]. Repeat 2-6 times.",
    )
    parser.add_argument("--quantity", type=int, required=True, help="Number of spread units")
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

    preflight_multileg(
        legs=legs,
        quantity=args.quantity,
        limit_price=args.limit_price,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        account_id=args.account_id,
    )

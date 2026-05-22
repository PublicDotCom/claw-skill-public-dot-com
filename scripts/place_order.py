import argparse
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal

try:
    from public_api_sdk import (
        OrderRequest,
        OrderInstrument,
        InstrumentType,
        OrderSide,
        OrderType,
        OrderExpirationRequest,
        TimeInForce,
        EquityMarketSession,
        OpenCloseIndicator,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        OrderRequest,
        OrderInstrument,
        InstrumentType,
        OrderSide,
        OrderType,
        OrderExpirationRequest,
        TimeInForce,
        EquityMarketSession,
        OpenCloseIndicator,
    )
from config import get_api_secret, get_account_id, create_client


def place_order(
    symbol,
    instrument_type,
    side,
    order_type,
    quantity=None,
    amount=None,
    limit_price=None,
    stop_price=None,
    session=None,
    open_close=None,
    time_in_force=None,
    expiration_time=None,
    account_id=None,
):
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)

    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    # Validate quantity/amount
    if quantity is None and amount is None:
        print("Error: Either --quantity or --amount must be provided.")
        sys.exit(1)

    # Validate limit price for LIMIT/STOP_LIMIT orders
    if order_type in ["LIMIT", "STOP_LIMIT"] and limit_price is None:
        print(f"Error: --limit-price is required for {order_type} orders.")
        sys.exit(1)

    # Validate stop price for STOP/STOP_LIMIT orders
    if order_type in ["STOP", "STOP_LIMIT"] and stop_price is None:
        print(f"Error: --stop-price is required for {order_type} orders.")
        sys.exit(1)

    # Map string values to enums
    instrument_type_map = {
        "EQUITY": InstrumentType.EQUITY,
        "OPTION": InstrumentType.OPTION,
        "CRYPTO": InstrumentType.CRYPTO,
    }
    side_map = {
        "BUY": OrderSide.BUY,
        "SELL": OrderSide.SELL,
    }
    order_type_map = {
        "LIMIT": OrderType.LIMIT,
        "MARKET": OrderType.MARKET,
        "STOP": OrderType.STOP,
        "STOP_LIMIT": OrderType.STOP_LIMIT,
    }
    session_map = {
        "CORE": EquityMarketSession.CORE,
        "EXTENDED": EquityMarketSession.EXTENDED,
    }
    open_close_map = {
        "OPEN": OpenCloseIndicator.OPEN,
        "CLOSE": OpenCloseIndicator.CLOSE,
    }
    time_in_force_map = {
        "DAY": TimeInForce.DAY,
        "GTD": TimeInForce.GTD,
    }
    if time_in_force and time_in_force not in time_in_force_map:
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

    try:
        client = create_client(secret, account_id)

        # Build order request
        order_kwargs = {
            "order_id": str(uuid.uuid4()),
            "instrument": OrderInstrument(
                symbol=symbol,
                type=instrument_type_map[instrument_type],
            ),
            "order_side": side_map[side],
            "order_type": order_type_map[order_type],
            "expiration": OrderExpirationRequest(
                time_in_force=time_in_force_map.get(time_in_force, TimeInForce.DAY),
                expiration_time=expiration_time_dt,
            ),
        }

        # Add quantity or amount
        if quantity is not None:
            order_kwargs["quantity"] = quantity
        if amount is not None:
            order_kwargs["amount"] = Decimal(str(amount))

        # Add limit price if applicable
        if limit_price is not None:
            order_kwargs["limit_price"] = Decimal(str(limit_price))

        # Add stop price if applicable
        if stop_price is not None:
            order_kwargs["stop_price"] = Decimal(str(stop_price))

        # Add session for equity orders
        if session and instrument_type == "EQUITY":
            order_kwargs["equity_market_session"] = session_map[session]

        # Add open/close indicator for options
        if open_close and instrument_type == "OPTION":
            order_kwargs["open_close_indicator"] = open_close_map[open_close]

        order_request = OrderRequest(**order_kwargs)
        order_response = client.place_order(order_request)

        print("Order Placed Successfully!")
        print("-" * 40)
        print(f"Order ID: {order_response.order_id}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Type: {order_type}")
        print(f"Time In Force: {time_in_force or 'DAY'}")
        if quantity is not None:
            print(f"Quantity: {quantity} shares")
        if amount is not None:
            print(f"Amount: ${amount}")
        if limit_price is not None:
            print(f"Limit Price: ${limit_price}")
        if stop_price is not None:
            print(f"Stop Price: ${stop_price}")
        print("-" * 40)

        client.close()
    except Exception as e:
        print(f"Error placing order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Place an order on Public.com")
    parser.add_argument("--symbol", required=True, help="Stock/crypto/option symbol")
    parser.add_argument(
        "--type",
        required=True,
        choices=["EQUITY", "OPTION", "CRYPTO"],
        help="Instrument type",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL"],
        help="Order side",
    )
    parser.add_argument(
        "--order-type",
        required=True,
        choices=["LIMIT", "MARKET", "STOP", "STOP_LIMIT"],
        help="Order type",
    )
    parser.add_argument("--quantity", type=float, help="Number of shares")
    parser.add_argument("--amount", type=float, help="Notional dollar amount")
    parser.add_argument("--limit-price", type=float, help="Limit price (required for LIMIT/STOP_LIMIT)")
    parser.add_argument("--stop-price", type=float, help="Stop price (required for STOP/STOP_LIMIT)")
    parser.add_argument(
        "--session",
        choices=["CORE", "EXTENDED"],
        default="CORE",
        help="Market session (CORE or EXTENDED)",
    )
    parser.add_argument(
        "--open-close",
        choices=["OPEN", "CLOSE"],
        help="Open/Close indicator for options",
    )
    parser.add_argument(
        "--time-in-force",
        choices=["DAY", "GTD"],
        default="DAY",
        help="Time in force: DAY (default) or GTD (Good Till Date — requires --expiration-time)",
    )
    parser.add_argument(
        "--expiration-time",
        help="Required when --time-in-force=GTD. YYYY-MM-DD or ISO 8601. Max 90 days out.",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()

    place_order(
        symbol=args.symbol,
        instrument_type=args.type,
        side=args.side,
        order_type=args.order_type,
        quantity=args.quantity,
        amount=args.amount,
        limit_price=args.limit_price,
        stop_price=args.stop_price,
        session=args.session,
        open_close=args.open_close,
        time_in_force=args.time_in_force,
        expiration_time=args.expiration_time,
        account_id=args.account_id,
    )

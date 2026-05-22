import argparse
import signal
import subprocess
import sys
import time
from datetime import datetime

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        OrderInstrument,
        InstrumentType,
        SubscriptionConfig,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        OrderInstrument,
        InstrumentType,
        SubscriptionConfig,
    )


def parse_instrument(spec):
    """SYMBOL or SYMBOL:TYPE — TYPE defaults to EQUITY."""
    parts = spec.split(":")
    symbol = parts[0]
    type_str = parts[1].upper() if len(parts) > 1 else "EQUITY"
    type_map = {
        "EQUITY": InstrumentType.EQUITY,
        "OPTION": InstrumentType.OPTION,
        "CRYPTO": InstrumentType.CRYPTO,
    }
    if type_str not in type_map:
        raise ValueError(f"Invalid instrument type '{type_str}'. Must be EQUITY, OPTION, or CRYPTO.")
    return OrderInstrument(symbol=symbol, type=type_map[type_str])


def watch_prices(instrument_specs, poll_seconds=2.0, max_updates=None, account_id=None):
    """
    Stream price changes for one or more instruments via the SDK's PriceStream
    (which polls under the hood and emits a callback only on price changes).
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    try:
        instruments = [parse_instrument(s) for s in instrument_specs]
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    client = create_client(secret, account_id)

    update_count = {"n": 0}
    stop = {"requested": False}

    def on_price_change(price_change):
        update_count["n"] += 1
        ts = datetime.now().strftime("%H:%M:%S")
        sym = price_change.instrument.symbol
        old = price_change.old_quote
        new = price_change.new_quote
        old_last = f"${old.last}" if old is not None and old.last is not None else "—"
        new_last = f"${new.last}" if new.last is not None else "—"
        bid = f"${new.bid}" if new.bid is not None else "—"
        ask = f"${new.ask}" if new.ask is not None else "—"
        changed = ",".join(price_change.changed_fields) if price_change.changed_fields else "—"
        print(f"[{ts}] {sym:<12} last {old_last} -> {new_last}  bid {bid}  ask {ask}  ({changed})")
        sys.stdout.flush()

        if max_updates and update_count["n"] >= max_updates:
            stop["requested"] = True

    def handle_sigint(signum, frame):
        stop["requested"] = True

    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    sub_id = None
    try:
        config = SubscriptionConfig(polling_frequency_seconds=poll_seconds)
        sub_id = client.price_stream.subscribe(
            instruments=instruments,
            callback=on_price_change,
            config=config,
        )

        symbols = ", ".join(f"{i.symbol} ({i.type.value})" for i in instruments)
        print(f"Watching {symbols}  (poll every {poll_seconds}s, Ctrl-C to stop)")
        if max_updates:
            print(f"Will stop after {max_updates} price changes.")
        print("-" * 70)
        sys.stdout.flush()

        while not stop["requested"]:
            time.sleep(0.2)
    finally:
        if sub_id:
            client.price_stream.unsubscribe(sub_id)
        client.close()
        print(f"\nStopped. Total price changes observed: {update_count['n']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Stream real-time price changes for one or more instruments",
        epilog=(
            "Instrument format: SYMBOL or SYMBOL:TYPE (TYPE = EQUITY|OPTION|CRYPTO, default EQUITY)\n\n"
            "Examples:\n"
            "  python3 watch_prices.py AAPL\n"
            "  python3 watch_prices.py AAPL GOOGL MSFT\n"
            "  python3 watch_prices.py BTC:CRYPTO --poll-seconds 5\n"
            "  python3 watch_prices.py AAPL --max-updates 10\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("instruments", nargs="+", help="Instruments to watch (SYMBOL or SYMBOL:TYPE)")
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=2.0,
        help="How often the SDK polls quotes (0.1-60, default 2.0)",
    )
    parser.add_argument(
        "--max-updates",
        type=int,
        help="Stop after this many price changes (useful for one-shot agent use)",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()
    watch_prices(
        instrument_specs=args.instruments,
        poll_seconds=args.poll_seconds,
        max_updates=args.max_updates,
        account_id=args.account_id,
    )

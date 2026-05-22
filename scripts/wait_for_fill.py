import argparse
import subprocess
import sys
import time
from datetime import datetime

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        OrderStatus,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        OrderStatus,
    )


TERMINAL_STATUSES = {
    OrderStatus.FILLED,
    OrderStatus.CANCELLED,
    OrderStatus.REJECTED,
    OrderStatus.EXPIRED,
    OrderStatus.REPLACED,
}


def wait_for_fill(order_id, timeout=120.0, poll_seconds=1.0, fill_only=False, account_id=None):
    """
    Poll get_order until the order reaches a terminal status (FILLED, CANCELLED,
    REJECTED, EXPIRED, REPLACED), or `--fill-only` mode reaches FILLED, or the
    timeout elapses.
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)
    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    client = create_client(secret, account_id)

    target = {OrderStatus.FILLED} if fill_only else TERMINAL_STATUSES
    start = time.monotonic()
    last_status = None

    try:
        print(f"Polling order {order_id} every {poll_seconds}s (timeout {timeout}s)...")
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                print(f"\nTimeout after {elapsed:.1f}s. Last status: {last_status.value if last_status else 'unknown'}")
                sys.exit(2)

            try:
                order = client.get_order(order_id=order_id, account_id=account_id)
            except Exception as e:
                # eventual consistency: order may not be retrievable immediately
                print(f"  ... not yet visible ({type(e).__name__})")
                time.sleep(poll_seconds)
                continue

            status = order.status
            if status != last_status:
                ts = datetime.now().strftime("%H:%M:%S")
                filled = f"  filled={order.filled_quantity}" if order.filled_quantity else ""
                avg = f"  avg=${order.average_price}" if order.average_price else ""
                print(f"  [{ts}] status={status.value}{filled}{avg}")
                last_status = status

            if status in target:
                print("\n" + "=" * 60)
                print(f"ORDER REACHED TERMINAL STATUS: {status.value}")
                print("=" * 60)
                inst = order.instrument
                print(f"  Order ID:     {order.order_id}")
                print(f"  Symbol:       {inst.symbol} ({inst.type.value})")
                print(f"  Side:         {order.side.value}")
                print(f"  Type:         {order.type.value}")
                if order.quantity is not None:
                    print(f"  Quantity:     {order.quantity}")
                if order.filled_quantity is not None:
                    print(f"  Filled:       {order.filled_quantity}")
                if order.average_price is not None:
                    print(f"  Avg Price:    ${order.average_price}")
                if order.reject_reason:
                    print(f"  Reject:       {order.reject_reason}")
                if order.closed_at is not None:
                    print(f"  Closed At:    {order.closed_at}")
                print("=" * 60)

                # Exit code: 0 if filled, 1 otherwise (so callers can react)
                sys.exit(0 if status == OrderStatus.FILLED else 1)

            time.sleep(poll_seconds)
    finally:
        client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Poll an order until it reaches a terminal status (FILLED/CANCELLED/REJECTED/EXPIRED/REPLACED)",
        epilog=(
            "Exit codes:\n"
            "  0  order reached FILLED\n"
            "  1  order reached a terminal non-fill status (CANCELLED/REJECTED/EXPIRED/REPLACED)\n"
            "  2  timed out waiting\n\n"
            "Examples:\n"
            "  python3 wait_for_fill.py --order-id <uuid>\n"
            "  python3 wait_for_fill.py --order-id <uuid> --fill-only --timeout 300\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--order-id", required=True, help="UUID of the order to track")
    parser.add_argument("--timeout", type=float, default=120.0, help="Max seconds to wait (default 120)")
    parser.add_argument("--poll-seconds", type=float, default=1.0, help="Polling interval (default 1.0)")
    parser.add_argument(
        "--fill-only",
        action="store_true",
        help="Only return success on FILLED. Otherwise any terminal status returns.",
    )
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")

    args = parser.parse_args()
    wait_for_fill(
        order_id=args.order_id,
        timeout=args.timeout,
        poll_seconds=args.poll_seconds,
        fill_only=args.fill_only,
        account_id=args.account_id,
    )

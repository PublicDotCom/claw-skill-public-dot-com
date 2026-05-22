import argparse
import sys

from config import get_api_secret, get_account_id, create_client


def get_order(order_id, account_id=None):
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)

    if not account_id:
        print("Error: No account ID provided. Either pass --account-id or set PUBLIC_COM_ACCOUNT_ID.")
        sys.exit(1)

    try:
        client = create_client(secret, account_id)

        order = client.get_order(order_id=order_id, account_id=account_id)

        print("=" * 70)
        print(f"ORDER {order.order_id}")
        print("=" * 70)

        inst = order.instrument
        print(f"\n  Status:        {order.status.value}")
        print(f"  Symbol:        {inst.symbol} ({inst.type.value})")
        print(f"  Side:          {order.side.value}")
        print(f"  Order Type:    {order.type.value}")

        if order.quantity is not None:
            print(f"  Quantity:      {order.quantity}")
        if order.notional_value is not None:
            print(f"  Notional:      ${order.notional_value:,.2f}")
        if order.filled_quantity is not None:
            print(f"  Filled:        {order.filled_quantity}")
        if order.average_price is not None:
            print(f"  Avg Price:     ${order.average_price}")
        if order.limit_price is not None:
            print(f"  Limit Price:   ${order.limit_price}")
        if order.stop_price is not None:
            print(f"  Stop Price:    ${order.stop_price}")
        if order.open_close_indicator is not None:
            print(f"  Open/Close:    {order.open_close_indicator.value}")
        if order.expiration is not None and order.expiration.time_in_force is not None:
            print(f"  Time in Force: {order.expiration.time_in_force.value}")
        if order.created_at is not None:
            print(f"  Created:       {order.created_at}")
        if order.closed_at is not None:
            print(f"  Closed:        {order.closed_at}")
        if order.reject_reason:
            print(f"  Reject Reason: {order.reject_reason}")

        if order.legs:
            print("\n  Legs:")
            for i, leg in enumerate(order.legs, 1):
                oc = f" ({leg.open_close_indicator.value})" if leg.open_close_indicator else ""
                ratio = f" x{leg.ratio_quantity}" if leg.ratio_quantity else ""
                print(f"    [{i}] {leg.side.value} {leg.instrument.symbol}{oc}{ratio}")

        print("\n" + "=" * 70)

        client.close()
    except Exception as e:
        print(f"Error fetching order: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get the status and details of a specific order")
    parser.add_argument("--order-id", required=True, help="The order ID to look up")
    parser.add_argument("--account-id", help="Account ID (uses PUBLIC_COM_ACCOUNT_ID if not provided)")
    args = parser.parse_args()
    get_order(order_id=args.order_id, account_id=args.account_id)

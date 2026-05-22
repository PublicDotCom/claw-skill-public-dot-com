import argparse
import subprocess
import sys

from config import get_api_secret, get_account_id, create_client

try:
    from public_api_sdk import (
        BarPeriod,
        BarAggregation,
        InstrumentType,
    )
except ImportError:
    print("Installing required dependency: publicdotcom-py...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "publicdotcom-py==0.1.15"])
    from public_api_sdk import (
        BarPeriod,
        BarAggregation,
        InstrumentType,
    )


def get_bars(
    symbol,
    period,
    instrument_type="EQUITY",
    aggregation=None,
    purchase_date=None,
    account_id=None,
):
    """
    Fetch historical OHLCV bar data for a symbol.

    Args:
        symbol: Ticker symbol (e.g. "AAPL", "BTC", "AAPL260320C00280000")
        period: One of BarPeriod values (DAY, WEEK, MONTH, QUARTER, HALF_YEAR,
                YEAR, FIVE_YEARS, YTD, SINCE_PURCHASE)
        instrument_type: EQUITY, CRYPTO, OPTION, or INDEX. Defaults to EQUITY.
        aggregation: Optional bar size override (ONE_MINUTE, FIVE_MINUTES, ...)
        purchase_date: Required when period=SINCE_PURCHASE. Format YYYY-MM-DD.
        account_id: Account ID (optional; uses PUBLIC_COM_ACCOUNT_ID env var if unset)
    """
    secret = get_api_secret()
    account_id = account_id or get_account_id()

    if not secret:
        print("Error: PUBLIC_COM_SECRET is not set.")
        sys.exit(1)

    period_map = {p.name: p for p in BarPeriod}
    aggregation_map = {a.name: a for a in BarAggregation}
    instrument_type_map = {
        "EQUITY": InstrumentType.EQUITY,
        "CRYPTO": InstrumentType.CRYPTO,
        "OPTION": InstrumentType.OPTION,
        "INDEX": InstrumentType.INDEX,
    }

    if period not in period_map:
        print(f"Error: Invalid period '{period}'. Must be one of: {', '.join(period_map.keys())}")
        sys.exit(1)

    if aggregation is not None and aggregation not in aggregation_map:
        print(f"Error: Invalid aggregation '{aggregation}'. Must be one of: {', '.join(aggregation_map.keys())}")
        sys.exit(1)

    if instrument_type not in instrument_type_map:
        print(f"Error: Invalid instrument type '{instrument_type}'. Must be EQUITY, CRYPTO, OPTION, or INDEX.")
        sys.exit(1)

    if period == "SINCE_PURCHASE" and not purchase_date:
        print("Error: --purchase-date is required when --period SINCE_PURCHASE.")
        sys.exit(1)

    try:
        client = create_client(secret, account_id)

        kwargs = {
            "symbol": symbol,
            "period": period_map[period],
            "instrument_type": instrument_type_map[instrument_type],
        }
        if aggregation is not None:
            kwargs["aggregation"] = aggregation_map[aggregation]
        if purchase_date is not None:
            kwargs["purchase_date"] = purchase_date

        response = client.get_bars(**kwargs)

        print("=" * 60)
        print(f"HISTORICAL BARS: {response.symbol} ({instrument_type})")
        print(f"  Period: {response.period}")
        print(f"  Total Expected Bars: {response.total_expected_bars}")
        if response.previous_close_price is not None:
            print(f"  Previous Close: ${response.previous_close_price}")
        if response.total_gain_loss is not None:
            print(f"  Total Gain/Loss: ${response.total_gain_loss}")
        if response.total_gain_loss_percentage is not None:
            print(f"  Total Gain/Loss %: {response.total_gain_loss_percentage}%")

        if response.last_regular_trading_session_close is not None:
            last = response.last_regular_trading_session_close
            print(f"\n  Last Regular Session Close ({last.close_date}): ${last.close}")
            if last.change is not None:
                print(f"    Change: ${last.change}")
            if last.percent_change is not None:
                print(f"    Percent Change: {last.percent_change}%")

        for label, session in (
            ("PRE-MARKET", response.pre_market),
            ("REGULAR MARKET", response.regular_market),
            ("AFTER-HOURS", response.after_market),
        ):
            print("\n" + "-" * 60)
            print(f"{label}  (expected: {session.expected_bars}, returned: {len(session.bars)})")
            print("-" * 60)
            for bar in session.bars:
                print(
                    f"  {bar.timestamp}  "
                    f"O={bar.open}  H={bar.high}  L={bar.low}  C={bar.close}  V={bar.volume}"
                )

        print("\n" + "=" * 60)

        client.close()
    except Exception as e:
        print(f"Error fetching bars: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch historical OHLCV bar data for a symbol",
        epilog="Examples:\n"
               "  python3 get_bars.py --symbol AAPL --period YEAR\n"
               "  python3 get_bars.py --symbol AAPL --period MONTH --aggregation ONE_DAY\n"
               "  python3 get_bars.py --symbol BTC --type CRYPTO --period WEEK\n"
               "  python3 get_bars.py --symbol AAPL --period SINCE_PURCHASE --purchase-date 2024-01-15",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--symbol", required=True, help="Symbol (e.g. AAPL, BTC, OSI option symbol)")
    parser.add_argument(
        "--period",
        required=True,
        choices=[p.name for p in BarPeriod],
        help="Time window for bars",
    )
    parser.add_argument(
        "--type",
        default="EQUITY",
        choices=["EQUITY", "CRYPTO", "OPTION", "INDEX"],
        help="Instrument type (default: EQUITY)",
    )
    parser.add_argument(
        "--aggregation",
        choices=[a.name for a in BarAggregation],
        help="Optional bar size override; server picks a sensible default if omitted",
    )
    parser.add_argument(
        "--purchase-date",
        help="Required for --period SINCE_PURCHASE. Format: YYYY-MM-DD",
    )
    parser.add_argument(
        "--account-id",
        help="Account ID (uses PUBLIC_COM_ACCOUNT_ID env var if not provided)",
    )

    args = parser.parse_args()

    get_bars(
        symbol=args.symbol,
        period=args.period,
        instrument_type=args.type,
        aggregation=args.aggregation,
        purchase_date=args.purchase_date,
        account_id=args.account_id,
    )

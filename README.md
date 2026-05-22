# Public.com OpenClaw Skill

## Overview

This is the repo for the OpenClaw skill to interact with your Public.com brokerage account. You can:

- View accounts, portfolio, orders, and transaction history
- Get live quotes and historical bars; stream real-time price changes
- List option chains, expirations, and greeks
- Preflight and place equity, crypto, and options orders (including shorts)
- Preflight and place vertical spreads and arbitrary 2-6 leg options strategies (iron condors, butterflies, straddles, etc.)
- Modify open orders (cancel-and-replace), cancel orders, wait for fills, and check order status

## Disclaimer

For illustrative and informational purposes only. Not investment advice or recommendations.

We recommend running this skill in as isolated of an environment as possible. If possible, test the integration on a new Public account as well.

## Before You Get Started

There are a few prerequisites needed to get started:

- **Python 3.9+** and **pip** — Required to run this skill. The skill's scripts use the `publicdotcom-py` SDK (pinned to `0.1.15`), which will be auto-installed on first run.
- **Public.com account** — Create one at https://public.com/signup
- **Public.com API key** — Once you create your Public.com brokerage account, get an API key at https://public.com/settings/v2/api

## Configuration

This skill uses two environment variables:

| Variable | Required | Description |
|---|---|---|
| `PUBLIC_COM_SECRET` | Yes | Your Public.com API secret key |
| `PUBLIC_COM_ACCOUNT_ID` | No | Default account ID for all requests |

### Setting your API key

Set the environment variable before running your agent:

```bash
export PUBLIC_COM_SECRET=<YOUR_API_SECRET>
```

You can find your API secret at https://public.com/settings/v2/api. Alternatively, the skill will prompt you for it on first use (e.g. "How is my Public portfolio doing today?").

### Setting a default account ID

Some requests require an account ID. You can list your accounts first, then set a default:

```bash
export PUBLIC_COM_ACCOUNT_ID=<YOUR_ACCOUNT_ID>
```

This eliminates the need to specify `--account-id` on each command.

## Commands

Each capability is implemented as a script under `scripts/`. The agent picks the right one based on your request — you generally don't need to invoke these directly.

| Script | Purpose |
|---|---|
| `check_setup.py` | Verify env vars are set and the API key works (run on first interaction) |
| `get_accounts.py` | List accounts on the API key |
| `get_portfolio.py` | Equity, buying power, positions |
| `get_orders.py` | Active orders on an account |
| `get_order.py` | Status and details of a specific order |
| `get_history.py` | Transaction history (paginated; filter by TRADE / MONEY_MOVEMENT / POSITION_ADJUSTMENT) |
| `get_quotes.py` | Live quotes for one or more instruments |
| `get_bars.py` | Historical OHLCV bars |
| `watch_prices.py` | Stream real-time price changes |
| `get_instruments.py` | List tradeable instruments |
| `get_instrument.py` | Details for a single instrument |
| `get_option_expirations.py` | Available option expiration dates |
| `get_option_chain.py` | Option chain for an expiration |
| `get_option_greeks.py` | Greeks for one or more option contracts |
| `preflight.py` / `place_order.py` | Preflight + place a single-leg equity/option/crypto order |
| `preflight_spread.py` / `place_spread.py` | Preflight + place a vertical spread (CALL/PUT × CREDIT/DEBIT) |
| `preflight_multileg.py` / `place_multileg.py` | Preflight + place any 2-6 leg options strategy |
| `preflight_short.py` / `place_short.py` | Preflight + place an equity short sale |
| `flatten_and_short.py` | Close an existing long and immediately open a short (experimental) |
| `cancel_order.py` | Cancel an open order |
| `cancel_and_replace.py` | Modify an open order's type/quantity/price atomically |
| `wait_for_fill.py` | Block until an order reaches a terminal status (FILLED/CANCELLED/REJECTED/EXPIRED/REPLACED) |

For per-command argument details, see [SKILL.md](SKILL.md) or run any script with `--help`.

## Example Prompts

- How is my portfolio doing today?
- Can you get me the options chain for Nvidia for options expiring tomorrow?
- Can you get me the current quotes for Apple, Google, and Microsoft?
- Can you get my account history and list out the deposits I've made?
- Watch Apple's price and tell me when it moves. Stop after 10 changes.
- I placed order `<id>` — wait until it fills and then summarize the fill price.
- Change order `<id>` to a limit of $230 with 20 shares.
- Set up an iron condor on AAPL for the December 19 expiration: short the 190 put / long the 185 put, short the 210 call / long the 215 call. Preflight first.
- I'm long 50 shares of TSLA but my thesis has flipped. Flatten the long and open a short for 50 shares.
- Set up a job to monitor the price of Bitcoin every 30 minutes. If the price is below $75K, buy $100 worth of it. If you are in a position and the price goes above $80K, sell it. All orders are market orders and only be in one position at a time. Run indefinitely.
- Get the options chain for Apple option contracts expiring Feb 18th. I want to open a call credit spread. Determine the best options contracts to do this with based on contract liquidity and max premium for cost.

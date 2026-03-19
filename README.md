# Stock Research Assistant

A lightweight Python tool that reads a watchlist, downloads recent market data, generates rule-based research summaries, and writes Markdown reports.

## Features

- Reads stock symbols from `watchlist.csv`
- Pulls price history and company metadata with `yfinance`
- Saves raw snapshots into `data/`
- Produces per-stock and combined reports in `reports/`
- Exports a refreshed Excel workbook and appends history on each run
- Can generate conservative paper-trading buy/sell/hold signals
- Can submit paper orders to Alpaca when explicitly enabled
- Works without any paid API keys
- Can upgrade to AI-written summaries with the OpenAI API

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

If you want AI-written summaries, add your key to `.env`:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-5-mini
OPENAI_REASONING_EFFORT=low
```

Without a key, the app falls back to deterministic rule-based summaries.

If you want paper trading, add your Alpaca paper credentials to `.env` and explicitly enable it:

```env
ALPACA_PAPER_API_KEY=your_paper_key
ALPACA_PAPER_API_SECRET=your_paper_secret
PAPER_TRADING_ENABLED=true
PAPER_TRADE_NOTIONAL_USD=100
```

The app is paper-only and uses the Alpaca paper endpoint by default. It also keeps a local trade log in `data/trade_log.csv` and skips duplicate same-day orders for the same symbol and action.

Position management settings are also available:

```env
MAX_POSITION_NOTIONAL_USD=300
STOP_LOSS_PCT=8
TAKE_PROFIT_PCT=15
```

These limits prevent repeated buying beyond the position cap and allow the system to exit paper positions when unrealized loss or gain breaches the configured thresholds.

To restrict order submission to regular U.S. market hours only, keep this enabled:

```env
TRADE_DURING_MARKET_HOURS_ONLY=true
```

The app will still refresh research, reports, and Excel output outside market hours, but it will skip placing paper orders when Alpaca reports the market is closed.

If a buy or sell signal is generated while the market is closed, the app will queue it in `data/pending_orders.csv` and attempt submission automatically on the next run when the market is open.

## Watchlist format

`watchlist.csv` should contain at least a `symbol` column.

Example:

```csv
symbol,company,notes
AAPL,Apple,Consumer devices and services
MSFT,Microsoft,Cloud and enterprise software
NVDA,NVIDIA,AI infrastructure leader
```

## Outputs

- Raw data snapshots: `data/<symbol>.json`
- Trade log: `data/trade_log.csv`
- Pending orders queue: `data/pending_orders.csv`
- Per-stock reports: `reports/<symbol>.md`
- Combined report: `reports/watchlist_summary.md`
- Excel workbook: `reports/watchlist.xlsx`
- Workbook sheets:
- `Overview`: latest snapshot per symbol
- `News`: latest headlines from the current run
- `History`: appended stock history across runs
- `NewsHistory`: appended headline history across runs

## 24/7 Deployment

For true unattended operation, deploy the app to an always-on Linux VPS and schedule it with `systemd`.

Files included for deployment:

- `.env.example`: safe environment template
- `deploy/setup_server.sh`: installs Python, creates `.venv`, and installs dependencies
- `deploy/systemd/stock-research.service`: runs the app once
- `deploy/systemd/stock-research.timer`: runs the app every 5 minutes

Suggested flow on Ubuntu:

```bash
git clone <your-repo-url> ~/stock-research-assistant
cd ~/stock-research-assistant
bash deploy/setup_server.sh ~/stock-research-assistant
cp .env.example .env
```

Then edit `.env` with rotated credentials and install the systemd units:

```bash
sudo cp deploy/systemd/stock-research.service /etc/systemd/system/
sudo cp deploy/systemd/stock-research.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now stock-research.timer
```

Useful checks:

```bash
systemctl list-timers --all | grep stock-research
journalctl -u stock-research.service -f
```

The included service assumes the Linux username is `ubuntu` and the app path is `/home/ubuntu/stock-research-assistant`. Adjust those two paths in the service file if your server uses a different username or location.

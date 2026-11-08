# Crypto Data Engineering Project

Fetches CoinGecko market data in USD and uploads the JSON response to an Amazon S3 bucket.

## Setup

Requires Python 3.12 or newer, a CoinGecko Demo API key, and AWS credentials with permission to write to the target S3 bucket.

In PowerShell, from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your own credentials and bucket details. Do not commit `.env`.

## Run

```powershell
python src\extraction\ingest_coingecko.py
```

The script writes to `raw/market_data/date=<YYYY-MM-DD>/market_data.json` in the configured bucket.
# Crypto Data Engineering Project

Fetches CoinGecko market data in USD and uploads the JSON response to an Amazon S3 bucket.

## Setup

Requires Python 3.12 or newer, a CoinGecko Demo API key, and AWS credentials with permission to write to the target S3 bucket.

In PowerShell, from the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project directory with your own credentials and bucket details:

```text
COINGECKO_API_KEY=your_coingecko_demo_key
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_REGION=your_aws_region
S3_BUCKET_NAME=your_s3_bucket_name
```

Do not commit `.env`.

## Run

```powershell
python src\extraction\ingest_coingecko.py
```

The script writes to `raw/market_data/date=<YYYY-MM-DD>/market_data.json` in the configured bucket.
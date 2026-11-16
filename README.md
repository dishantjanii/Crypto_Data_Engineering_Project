# PulseCrypto: End to End Crypto Data Lakehouse & Market Intelligence

**Live Dashboard:** `[Add your deployed Streamlit URL here]`

PulseCrypto is an automated data engineering pipeline and market analytics terminal built on AWS S3, Databricks Delta Lake, PySpark, Groq, and Streamlit. Every day, it pulls live market metrics for the top 250 cryptocurrencies from CoinGecko, stores raw snapshots in Amazon S3, processes them through a three tier Medallion architecture (Bronze, Silver, and Gold) in Databricks, and serves technical indicators and AI driven market analysis through an interactive dark theme dashboard.

---

## System Architecture

```text
+-------------------+       +---------------------------------------+
|  CoinGecko API    | ----> | GitHub Actions (Daily Cron 02:00 UTC) |
| (/coins/markets)  |       +-------------------+-------------------+
+-------------------+                           |
                                                v
                            +---------------------------------------+
                            | Amazon S3 Raw Zone                    |
                            | s3://crypto-lakehouse-raw/raw/        |
                            |   └── date=YYYY-MM-DD/market_data.json|
                            +-------------------+-------------------+
                                                |
                                                v  (Databricks Auto Loader)
+---------------------------------------------------------------------------+
| Databricks Lakehouse (Medallion Architecture)                             |
|                                                                           |
|  [Bronze Layer]  crypto_project.crypto.bronze_crypto_market               |
|                  Append only raw ingestion with schema evolution          |
|                                      |                                    |
|                                      v  (PySpark Cleaning & Dedup)        |
|  [Silver Layer]  crypto_project.crypto.silver_crypto_market               |
|                  Filtered (market_cap > 0) + Idempotent Delta MERGE       |
|                                      |                                    |
|                                      v  (Window Functions & Star Schema)  |
|  [Gold Layer]    dim_coins & fact_crypto_daily (Top 200 Ranked Coins)     |
|                  7 Day Rolling SMA, 7 Day Volatility, Volume/Mcap Ratio   |
+--------------------------------------+------------------------------------+
                                       |
                                       v  (databricks-sql-connector)
+---------------------------------------------------------------------------+
| Streamlit Serving Layer (src/dashboard/app.py)                            |
|  * Executive KPI Cards & Animated SVG Charts (Breadth Gauge & Donut)      |
|  * Deterministic Market Regime Outlook (Groq API, temperature=0, seed=42) |
|  * Interactive Market Analyst Q&A grounded in Top 200 Gold metrics        |
+---------------------------------------------------------------------------+
```

---

## Why I Built This This Way

* **Incremental Ingestion Instead of Full Reloads:** Rather than overwriting historical files, raw JSON snapshots land in date partitioned S3 folders (`date=YYYY-MM-DD/`). Databricks Auto Loader (`cloudFiles`) tracks processed files using checkpoints on S3 and runs in batch mode (`availableNow=True`), keeping compute costs low while building a multi day historical archive.
* **Duplicate Safe Silver Layer:** API retries or manual re runs can easily create duplicate rows for the same day. The Silver script uses a PySpark `row_number()` window partitioned by `(coin_id, market_date)` and ordered by ingestion timestamp, followed by a Delta `MERGE INTO` operation so existing rows update cleanly and new dates append without duplicates.
* **Progressive Data Filtering:** Bronze keeps all 250 raw records from CoinGecko for auditability. Silver removes dead or untracked tokens by enforcing `market_cap > 0` and `price_usd > 0`. Gold narrows the scope to the Top 200 coins by market cap rank so downstream charts and AI prompts stay focused on liquid assets.
* **Token Efficient, Deterministic AI Analysis:** Sending 200 raw JSON objects to an LLM wastes tokens and risks hitting rate limits. The dashboard compresses the Gold snapshot into a compact pipe delimited table (under 1,800 tokens) containing overall market breadth, the top 20 assets, top gainers and losers, and any specific ticker mentioned in the user's question. Setting `temperature=0.0` and `seed=42` ensures the model produces consistent, repeatable answers on the same dataset.

---

## Tech Stack

| Layer | Tools & Services |
| :--- | :--- |
| **Data Source** | CoinGecko REST API (`/api/v3/coins/markets`) |
| **Cloud Storage** | Amazon S3 (Hive style date partitioning) |
| **Data Processing** | Databricks, PySpark, Delta Lake, Auto Loader (`cloudFiles`) |
| **Orchestration** | GitHub Actions (Daily Extraction) & Databricks Workflows (ETL) |
| **AI Inference** | Groq API (`openai/gpt-oss-120b` with fallback to `openai/gpt-oss-20b`) |
| **Frontend & Serving** | Streamlit, `databricks-sql-connector`, Pandas, Custom HTML/SVG |

---

## Project Structure

```text
Crypto_Data_Engineering_Project/
├── .github/
│   └── workflows/
│       └── daily_ingest.yml          # Automated daily extraction schedule
├── .streamlit/
│   └── config.toml                   # Dark terminal theme configuration
├── src/
│   ├── extraction/
│   │   └── ingest_coingecko.py       # Fetches top 250 coins and uploads to S3
│   ├── transformation/
│   │   ├── 01_bronze_crypto.py       # Auto Loader incremental stream to Bronze
│   │   ├── 02_silver_crypto.py       # Data quality checks, deduplication, MERGE
│   │   └── 03_gold_crypto.py         # Star schema & 7 day rolling window metrics
│   └── dashboard/
│       └── app.py                    # Streamlit UI, SVG charts, and Groq analyst
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Gold Layer Data Model

The Gold layer follows a clean star schema optimized for analytical queries and dashboard rendering:

1. **`crypto_project.crypto.dim_coins`**
   * Stores the latest descriptive metadata for the Top 200 universe: `coin_id`, `symbol`, `name`, and `market_cap_rank`.
2. **`crypto_project.crypto.fact_crypto_daily`**
   * Stores daily price, volume, and engineered technical indicators per coin:
     * `sma_7d_price`: 7 day rolling simple moving average computed via PySpark window functions (`rowsBetween(-6, 0)`).
     * `volatility_7d`: 7 day rolling standard deviation of closing prices.
     * `volume_to_mcap_ratio`: 24 hour trading volume divided by market capitalization to spot unusual liquidity spikes.
     * `trend_signal`: Classifies each asset as `ABOVE_7D_SMA`, `BELOW_7D_SMA`, or `NEUTRAL`.

---

## Local Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git](https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git)
cd Crypto_Data_Engineering_Project
```

### 2. Create a Virtual Environment & Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory and add your credentials:
```ini
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=crypto-lakehouse-raw

DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_TOKEN=your_databricks_pat_token

GROQ_API_KEY=your_groq_api_key
```

### 4. Run the Pipeline & Dashboard
```bash
# Run daily extraction to S3
python src/extraction/ingest_coingecko.py

# After running the Bronze, Silver, and Gold notebooks in Databricks, launch the UI:
streamlit run src/dashboard/app.py
```

---

## Future Improvements

* Add multi timeframe technical indicators (14 day RSI and 30 day moving averages) once 30+ days of daily snapshots accumulate in Silver.
* Configure automated data quality alerts via SNS or email if CoinGecko API ingestion fails or returns fewer than 200 valid coins.
* Add historical backtesting views in Streamlit to compare AI market regime calls against subsequent 7 day market returns.

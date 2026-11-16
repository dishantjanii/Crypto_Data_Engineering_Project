# PulseCrypto: End to End Crypto Data Lakehouse & Market Intelligence

**Live Application:** [https://crypto-market-analysis-chatbot.streamlit.app/](https://crypto-market-analysis-chatbot.streamlit.app/)

PulseCrypto is an end to end data engineering pipeline and interactive market analytics platform built using Python, Amazon S3, Databricks Delta Lake, PySpark, Groq, and Streamlit. The project automates daily ingestion of market data for the top 250 cryptocurrencies, transforms raw JSON payloads through a three tier Medallion architecture (Bronze, Silver, and Gold), computes rolling technical indicators, and powers a dark mode analytics dashboard with an AI market analyst grounded in the Gold tables.

---

## System Architecture

```text
+-------------------+       +---------------------------------------+
|  CoinGecko API    | ----> | GitHub Actions (Daily Cron 02:00 UTC) |
| (/coins/markets)  |       +-------------------+-------------------+
+-------------------+                           |
                                                v
                            +---------------------------------------+
                            | Amazon S3 Raw Data Lake               |
                            | s3://crypto-lakehouse-raw/raw/        |
                            |   └── date=YYYY-MM-DD/market_data.json|
                            +-------------------+-------------------+
                                                |
                                                v  (Databricks Auto Loader)
+---------------------------------------------------------------------------+
| Databricks Lakehouse (Medallion Architecture)                             |
|                                                                           |
|  [Bronze Layer]  crypto_project.crypto.bronze_crypto_market               |
|                  Append only raw ingestion with automatic schema tracking |
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
| Streamlit Serving Layer ([https://crypto-market-analysis-chatbot.streamlit.app/](https://crypto-market-analysis-chatbot.streamlit.app/))
|  * Executive KPI Cards & Animated SVG Charts (Breadth Gauge & Donut)      |
|  * Deterministic Market Regime Outlook (Groq API, temperature=0, seed=42) |
|  * Interactive Market Analyst Q&A grounded in Top 200 Gold metrics        |
+---------------------------------------------------------------------------+
```

---

## Step by Step Pipeline Walkthrough

### Step 1: Automated Data Extraction (`src/extraction/ingest_coingecko.py`)
* **What it does:** Sends a GET request to the CoinGecko `/coins/markets` endpoint (`vs_currency=usd`, `order=market_cap_desc`, `per_page=250`, `page=1`) to capture live prices, 24 hour percentage changes, market capitalizations, trading volumes, and rankings for the top 250 digital assets.
* **Storage format:** Wraps the response with extraction metadata (`extracted_at_utc` and `source`) and uploads it as `market_data.json` into a Hive partitioned Amazon S3 path (`raw/date=YYYY-MM-DD/market_data.json`) using `boto3`.
* **Scheduling:** A GitHub Actions workflow (`.github/workflows/daily_ingest.yml`) triggers this script automatically every day at `02:00 UTC` (`07:30 AM IST`) using encrypted repository secrets for AWS credentials.

### Step 2: Bronze Ingestion via Auto Loader (`src/transformation/01_bronze_crypto.py`)
* **What it does:** Uses Databricks Auto Loader (`cloudFiles`) to incrementally detect and ingest newly landed JSON files from Amazon S3 into the `crypto_project.crypto.bronze_crypto_market` Delta table.
* **Why Auto Loader:** Configured with `trigger(availableNow=True)` and S3 checkpointing (`_checkpoints/bronze_crypto`), it processes only unread files in batch mode and shuts down, avoiding continuous streaming cluster costs while maintaining full schema evolution (`schemaEvolutionMode = addNewColumns`).

### Step 3: Silver Cleaning & Idempotent Upserts (`src/transformation/02_silver_crypto.py`)
* **What it does:** Reads new records from Bronze, flattens nested JSON fields, casts numeric columns to strict `double` and `long` types, and filters out invalid or untracked assets (`market_cap > 0` and `price_usd > 0`).
* **Deduplication & MERGE:** Applies a PySpark `row_number()` window partitioned by `(coin_id, market_date)` and ordered by `ingestion_timestamp DESC` so only the latest record per coin per day survives. It then executes a Delta `MERGE INTO crypto_project.crypto.silver_crypto_market` statement, updating existing records if a day is re run and inserting new records cleanly without duplicates.

### Step 4: Gold Star Schema & Feature Engineering (`src/transformation/03_gold_crypto.py`)
* **What it does:** Filters the cleaned Silver dataset down to the Top 200 cryptocurrencies by `market_cap_rank` and builds two production tables:
  1. **`crypto_project.crypto.dim_coins`:** Dimension table holding descriptive metadata (`coin_id`, `symbol`, `name`, and current `market_cap_rank`).
  2. **`crypto_project.crypto.fact_crypto_daily`:** Fact table storing daily prices alongside engineered technical indicators computed via PySpark window functions (`partitionBy("coin_id").orderBy("market_date")`):
     * `prev_price_usd`: Prior day closing price via `lag("price_usd", 1)`.
     * `sma_7d_price`: 7 day rolling simple moving average via `avg("price_usd").over(rowsBetween(-6, 0))`.
     * `volatility_7d`: 7 day rolling price standard deviation via `stddev("price_usd").over(rowsBetween(-6, 0))`.
     * `volume_to_mcap_ratio`: Liquidity turnover ratio (`total_volume / market_cap`).
     * `trend_signal`: Momentum flag classifying each asset as `ABOVE_7D_SMA`, `BELOW_7D_SMA`, or `NEUTRAL`.

### Step 5: Serving Layer & AI Market Analyst (`src/dashboard/app.py`)
* **Live Warehouse Queries:** Connects directly to the Databricks SQL Warehouse via `databricks-sql-connector` with `@st.cache_data(ttl=300)` caching so dashboard interactions remain fast.
* **Visual Analytics:** Renders 8 executive KPI cards, an animated radial gauge showing 7 day SMA market breadth, a donut ring breaking down capitalization across Large Caps (Rank 1 to 10), Mid Caps (Rank 11 to 50), and Altcoins (Rank 51 to 200), an animated Top 5 Gainers/Losers bar chart, and a Price vs. 7D SMA trend chart.
* **Deterministic Groq AI Engine:** Compresses the Top 200 snapshot into a compact pipe delimited context block (under 1,800 tokens) containing market breadth metrics, the top 20 assets, top movers, and any ticker mentioned in the user's prompt. Calls the Groq API (`openai/gpt-oss-120b` with fallback to `openai/gpt-oss-20b`) with `temperature=0.0` and `seed=42` so both the Quantitative Market Brief and interactive Q&A produce grounded, repeatable answers without hallucinating external news.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Extraction & API** | Python 3.12, `requests`, `boto3`, CoinGecko REST API |
| **Cloud Storage** | Amazon S3 (Hive style date partitioned raw zone) |
| **Lakehouse & ETL** | Databricks, PySpark, Delta Lake, Auto Loader (`cloudFiles`) |
| **Automation** | GitHub Actions (Daily Cron) & Databricks Workflows |
| **AI & LLM Layer** | Groq API (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) |
| **Frontend & Cloud Host** | Streamlit Community Cloud, `databricks-sql-connector`, Pandas, Custom HTML/SVG |

---

## Repository Structure

```text
Crypto_Data_Engineering_Project/
├── .github/
│   └── workflows/
│       └── daily_ingest.yml          # GitHub Actions daily S3 extraction workflow
├── .streamlit/
│   └── config.toml                   # Custom dark theme styling for Streamlit
├── src/
│   ├── extraction/
│   │   └── ingest_coingecko.py       # CoinGecko API extractor and S3 uploader
│   ├── transformation/
│   │   ├── 01_bronze_crypto.py       # Auto Loader incremental Bronze ingestion
│   │   ├── 02_silver_crypto.py       # Cleaning, deduplication, and Delta MERGE
│   │   └── 03_gold_crypto.py         # Star schema and rolling window indicators
│   └── dashboard/
│       └── app.py                    # Streamlit UI, SVG charts, and Groq analyst
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Local Setup & Deployment Guide

### 1. Clone the Repository
```bash
git clone [https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git](https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git)
cd Crypto_Data_Engineering_Project
```

### 2. Create a Virtual Environment & Install Packages
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Local Environment Variables
Create a `.env` file in the root directory (excluded from Git via `.gitignore`):
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

### 4. Run Locally
```bash
# 1. Extract today's snapshot to S3
python src/extraction/ingest_coingecko.py

# 2. Execute 01_bronze_crypto.py, 02_silver_crypto.py, and 03_gold_crypto.py in Databricks

# 3. Start the Streamlit dashboard
streamlit run src/dashboard/app.py
```

### 5. Cloud Deployment (Streamlit Community Cloud)
1. Connect the GitHub repository (`dishantjanii/Crypto_Data_Engineering_Project`) on [share.streamlit.io](https://share.streamlit.io/) with main file path `src/dashboard/app.py`.
2. Add `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN`, and `GROQ_API_KEY` under **App Settings > Secrets** in TOML format.
3. Add `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, and `S3_BUCKET_NAME` under **GitHub Repository Settings > Secrets and variables > Actions** to enable daily automated ingestion.

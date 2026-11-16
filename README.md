# PulseCrypto: End to End Crypto Data Lakehouse & Market Intelligence

**Live Application:** [https://crypto-market-analysis-chatbot.streamlit.app/](https://crypto-market-analysis-chatbot.streamlit.app/)

PulseCrypto is an end to end data engineering pipeline and interactive market analytics platform built with Python, Amazon S3, Databricks Delta Lake, PySpark, Groq, and Streamlit. The system extracts daily market snapshots for the top 250 cryptocurrencies from the CoinGecko API, lands raw JSON files in Amazon S3, processes the data through a three tier Medallion architecture (Bronze, Silver, and Gold) in Databricks, computes rolling 7 day technical indicators, and powers a dark mode analytics terminal with an interactive AI market analyst.

---

## System Architecture

```text
+-------------------+       +---------------------------------------+
|  CoinGecko API    | ----> | Python Extraction Script              |
| (/coins/markets)  |       | (src/extraction/ingest_coingecko.py)  |
+-------------------+       +-------------------+-------------------+
                                                |
                                                v  (boto3 upload)
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
|  * 8 Executive KPI Cards & Animated SVG Charts (Breadth Gauge & Donut)    |
|  * Deterministic Market Regime Outlook (Groq API, temperature=0, seed=42) |
|  * Interactive Market Analyst Q&A grounded in Top 200 Gold metrics        |
+---------------------------------------------------------------------------+
```

---

## End to End Pipeline Breakdown

### 1. Data Extraction (`src/extraction/ingest_coingecko.py`)
* **API Ingestion:** Queries the CoinGecko REST API (`/api/v3/coins/markets`) with `vs_currency=usd`, `order=market_cap_desc`, `per_page=250`, and `page=1` to pull live prices, 24 hour percentage price changes, total market capitalization, 24 hour trading volume, circulating supply, and rank metadata for the top 250 coins.
* **Payload Envelope:** Wraps the raw coin list inside a structured JSON envelope containing `extracted_at_utc` and `source` metadata so downstream layers can audit when each snapshot was captured.
* **Hive Style S3 Partitioning:** Uploads the file via `boto3` into `s3://crypto-lakehouse-raw/raw/date=YYYY-MM-DD/market_data.json`. Organizing files by `date=YYYY-MM-DD/` allows Databricks to discover new partitions automatically and avoids overwriting prior days of market history.

### 2. Bronze Layer (`src/transformation/01_bronze_crypto.py`)
* **Incremental Streaming with Auto Loader:** Uses Databricks Auto Loader (`spark.readStream.format("cloudFiles")`) with `cloudFiles.format = "json"` to detect newly uploaded JSON files in S3 without scanning the entire bucket on every run.
* **Batch Trigger & Checkpointing:** Configured with `.trigger(availableNow=True)` and `.option("checkpointLocation", "s3://crypto-lakehouse-raw/_checkpoints/bronze_crypto")`. Auto Loader tracks every processed S3 object in the checkpoint directory, ingests only new files in a single batch pass, and terminates cleanly to avoid idle compute costs.
* **Schema Evolution:** Uses `cloudFiles.schemaEvolutionMode = "addNewColumns"` so any new fields introduced by the CoinGecko API are captured automatically in `crypto_project.crypto.bronze_crypto_market`.

### 3. Silver Layer (`src/transformation/02_silver_crypto.py`)
* **Schema Enforcement & Filtering:** Flattens the nested Bronze JSON records, casts price, volume, and market cap columns into strict `double` and `long` data types, parses `market_date`, and drops invalid or dead tokens (`market_cap > 0` and `price_usd > 0`).
* **Window Based Deduplication:** If the extraction script runs multiple times on the same day, duplicate rows can enter Bronze. The Silver transformation applies `row_number().over(Window.partitionBy("coin_id", "market_date").orderBy(col("ingestion_timestamp").desc()))` and filters to `row_num == 1` so only the latest snapshot per coin per day is retained.
* **Idempotent Delta MERGE:** Executes a Delta Lake `MERGE INTO crypto_project.crypto.silver_crypto_market` keyed on `(target.coin_id = source.coin_id AND target.market_date = source.market_date)`. Matching rows are updated in place and new dates are inserted, making the Silver layer completely idempotent across re runs.

### 4. Gold Layer (`src/transformation/03_gold_crypto.py`)
* **Universe Filtering:** Narrows the cleaned Silver dataset to the Top 200 cryptocurrencies by `market_cap_rank` so downstream analytics and AI prompts focus on liquid, actively traded assets.
* **Dimensional Modeling (Star Schema):**
  1. **`crypto_project.crypto.dim_coins`:** Stores slowly changing descriptive attributes (`coin_id`, `symbol`, `name`, and current `market_cap_rank`).
  2. **`crypto_project.crypto.fact_crypto_daily`:** Stores daily quantitative measurements and engineered technical indicators computed over a rolling window (`Window.partitionBy("coin_id").orderBy("market_date").rowsBetween(-6, 0)`):
     * `prev_price_usd`: Previous day price retrieved via `lag("price_usd", 1)`.
     * `sma_7d_price`: 7 day rolling simple moving average of closing prices.
     * `volatility_7d`: 7 day rolling standard deviation of closing prices.
     * `volume_to_mcap_ratio`: 24 hour trading volume divided by market capitalization to highlight high turnover assets.
     * `trend_signal`: Momentum classification (`ABOVE_7D_SMA`, `BELOW_7D_SMA`, or `NEUTRAL`) comparing current price against the 7 day moving average.

### 5. Serving Layer & AI Quantitative Terminal (`src/dashboard/app.py`)
* **Direct Warehouse Connectivity:** Queries `fact_crypto_daily` joined with `dim_coins` over HTTPS using `databricks-sql-connector`, caching results for 5 minutes via `@st.cache_data(ttl=300)` for instant UI responsiveness.
* **Custom Glassmorphism UI & Animated SVG Visuals:**
  * **8 Executive KPI Cards:** Displays Top 200 Market Cap, 24h Global Volume, BTC Dominance %, 7D SMA Bullish Breadth %, 24h Top Gainer, 24h Top Loser, Median 24h Return %, and Highest Liquidity Ratio (`Vol/Mcap`).
  * **Animated SVG Charts:** Built with custom HTML/SVG animations (`stroke-dashoffset` spline drawing and staggered bar transitions), including a Semi Circle Market Breadth Gauge, a Market Cap Tier Concentration Donut (Top 10 vs Rank 11 to 50 vs Rank 51 to 200), a Top 5 Gainers/Losers Bar Chart, and a Price vs. 7D SMA Trend Line.
* **Token Optimized, Deterministic Groq AI Engine:**
  * Sending 200 verbose JSON records to an LLM consumes over 25,000 tokens and exceeds free tier rate limits. The dashboard includes a dynamic context builder that compresses the snapshot into a compact pipe delimited table (under 1,800 tokens) containing overall breadth statistics, the top 20 assets, top gainers and losers, and any specific ticker matched in the user's question.
  * Inference runs against Groq (`openai/gpt-oss-120b` with automatic fallback to `openai/gpt-oss-20b`) using `temperature=0.0`, `top_p=1.0`, `seed=42`, and `reasoning_effort="low"` paired with SHA 256 response caching so identical queries on the same snapshot always return consistent, data grounded answers.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Data Extraction** | Python 3.12, `requests`, `boto3`, CoinGecko REST API |
| **Cloud Storage** | Amazon S3 (Hive partitioned raw data lake) |
| **Data Engineering & ETL** | Databricks, PySpark, Delta Lake, Auto Loader (`cloudFiles`) |
| **Data Modeling** | Star Schema (`dim_coins`, `fact_crypto_daily`), PySpark Window Functions |
| **AI & LLM Engine** | Groq API (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`) |
| **Frontend & Deployment** | Streamlit Community Cloud, `databricks-sql-connector`, Pandas, Custom HTML/SVG/CSS |

---

## Project Structure

```text
Crypto_Data_Engineering_Project/
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

## Local Setup & Execution Guide

### 1. Clone the Repository
```bash
git clone [https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git](https://github.com/dishantjanii/Crypto_Data_Engineering_Project.git)
cd Crypto_Data_Engineering_Project
```

### 2. Create a Virtual Environment & Install Dependencies
```bash
python -m venv .venv

# Activate on Windows PowerShell:
.venv\Scripts\Activate.ps1

# Activate on macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory (ignored by Git via `.gitignore`) and populate your credentials:
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

### 4. Run the Pipeline End to End
1. **Extract Raw Market Data to S3:**
   ```bash
   python src/extraction/ingest_coingecko.py
   ```
2. **Run Databricks Medallion Transformations:**
   Execute `01_bronze_crypto.py`, `02_silver_crypto.py`, and `03_gold_crypto.py` sequentially in your Databricks workspace (or trigger your Databricks Workflow job) to update the Delta tables.
3. **Launch the Local Streamlit Dashboard:**
   ```bash
   streamlit run src/dashboard/app.py
   ```

---

## Cloud Deployment (Streamlit Community Cloud)

1. Push the repository to GitHub (`main` branch).
2. Open [share.streamlit.io](https://share.streamlit.io/), select `dishantjanii/Crypto_Data_Engineering_Project`, and set the main file path to `src/dashboard/app.py`.
3. Open **App Settings > Secrets** and add your Databricks and Groq credentials in TOML format:
   ```toml
   DATABRICKS_SERVER_HOSTNAME = "your-workspace.cloud.databricks.com"
   DATABRICKS_HTTP_PATH = "/sql/1.0/warehouses/your-warehouse-id"
   DATABRICKS_TOKEN = "dapi..."
   GROQ_API_KEY = "gsk_..."
   ```
4. Deploy the app to publish your live public URL.

---

## Future Enhancements

* Add 14 day Relative Strength Index (RSI) and 30 day moving averages to `fact_crypto_daily` as historical snapshots accumulate.
* Implement automated data quality checks to validate record counts, null thresholds, and schema integrity before promoting data from Silver to Gold.
* Add historical regime backtesting in the Streamlit UI to compare AI market outlook calls against subsequent 7 day returns.

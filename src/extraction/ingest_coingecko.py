import os
import json
import time
import boto3
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

COINGECKO_API_KEY=os.getenv("COINGECKO_API_KEY")


AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION=os.getenv("AWS_REGION")
S3_BUCKET_NAME=os.getenv("S3_BUCKET_NAME")

s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


BASE_URL ="https://api.coingecko.com/api/v3"
HEADERS = {"accept": "application/json", "x-cg-demo-api-key": COINGECKO_API_KEY}

def fetch_data():
    all_coin=[]
    page=1
    per_page=200

    print("Fetching data from CoinGecko API...")
    while True:
        url  = f"{BASE_URL}/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": per_page,
            "page": page,
            "sparkline": "false"
        }
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 429:
            print("rate limit reached, paused for 60 seconds")
            time.sleep(60)
            continue
        elif response.status_code!=200:
            print(f"Error fetching page {page}, status code: {response.status_code}")

        data = response.json()

        if not data:
            print(f"Finished pulling data, total pages: {page - 1}")
            break

        all_coin.extend(data)
        print(f"Successfully added {page} page -  {len(data)} coins added")

        page+=1
    return all_coin


def upload_to_s3(data, file_name):
    today = datetime.now().strftime("%Y-%m-%d")
    s3_key = f"raw/date={today}/{file_name}"
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=s3_key,
        Body=json.dumps(data,indent=2),
        ContentType="application/json"
    )
    print(f"Successfully uploaded: s3://{S3_BUCKET_NAME}/{s3_key}")

def main():
    print("starting CoinGecko data Extraction...")

    #1. Extract market data
    market_data = fetch_data()
    upload_to_s3(market_data, "market_data.json")

    print("Extraction completed successfully.")

if __name__ == "__main__":
    main()
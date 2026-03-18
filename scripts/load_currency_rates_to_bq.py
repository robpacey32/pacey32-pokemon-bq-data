import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from io import StringIO

import pandas as pd
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
import json

PROJECT_ID = "pokemon-pacey32-github"
DATASET_ID = "pokemondatafromapi"
TABLE_ID = "currency_rates"
ECB_XML_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"

def get_bq_client():
    creds_info = json.loads(os.environ["GCP_SA_KEY"])
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    return bigquery.Client(project=PROJECT_ID, credentials=credentials)

def fetch_ecb_rates():
    resp = requests.get(ECB_XML_URL, timeout=60)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)

    ns = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }

    cube_time = root.find(".//def:Cube/def:Cube", ns)
    rate_date = cube_time.attrib["time"]

    raw_rates = {}
    for cube in cube_time.findall("def:Cube", ns):
        currency = cube.attrib["currency"]
        rate = float(cube.attrib["rate"])
        raw_rates[currency] = rate

    return rate_date, raw_rates

def build_rows(rate_date, raw_rates):
    load_ts = datetime.now(timezone.utc)

    eur_gbp = raw_rates["GBP"]
    eur_usd = raw_rates["USD"]

    rows = [
        {
            "rate_date": rate_date,
            "base_currency": "EUR",
            "target_currency": "GBP",
            "exchange_rate": eur_gbp,
            "source": "ECB",
            "load_timestamp": load_ts,
        },
        {
            "rate_date": rate_date,
            "base_currency": "EUR",
            "target_currency": "USD",
            "exchange_rate": eur_usd,
            "source": "ECB",
            "load_timestamp": load_ts,
        },
        {
            "rate_date": rate_date,
            "base_currency": "GBP",
            "target_currency": "EUR",
            "exchange_rate": 1 / eur_gbp,
            "source": "ECB_DERIVED",
            "load_timestamp": load_ts,
        },
        {
            "rate_date": rate_date,
            "base_currency": "USD",
            "target_currency": "EUR",
            "exchange_rate": 1 / eur_usd,
            "source": "ECB_DERIVED",
            "load_timestamp": load_ts,
        },
        {
            "rate_date": rate_date,
            "base_currency": "GBP",
            "target_currency": "USD",
            "exchange_rate": eur_usd / eur_gbp,
            "source": "ECB_DERIVED",
            "load_timestamp": load_ts,
        },
        {
            "rate_date": rate_date,
            "base_currency": "USD",
            "target_currency": "GBP",
            "exchange_rate": eur_gbp / eur_usd,
            "source": "ECB_DERIVED",
            "load_timestamp": load_ts,
        },
    ]

    return pd.DataFrame(rows)

def load_to_bigquery(df):
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("rate_date", "DATE"),
            bigquery.SchemaField("base_currency", "STRING"),
            bigquery.SchemaField("target_currency", "STRING"),
            bigquery.SchemaField("exchange_rate", "FLOAT64"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("load_timestamp", "TIMESTAMP"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Loaded {len(df)} rows to {table_ref}", flush=True)

def main():
    rate_date, raw_rates = fetch_ecb_rates()
    df = build_rows(rate_date, raw_rates)
    print(df, flush=True)
    load_to_bigquery(df)

if __name__ == "__main__":
    main()

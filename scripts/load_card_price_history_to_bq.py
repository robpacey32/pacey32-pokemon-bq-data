import json
import time
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import requests
from google.cloud import bigquery

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ID = "pokemon-pacey32-github"
DATASET_ID = "pokemondatafromapi"
TABLE_ID = "card_price_history"
LANGUAGE = "en"

BASE_URL = f"https://api.tcgdex.net/v2/{LANGUAGE}"
CARDS_LIST_URL = f"{BASE_URL}/cards"


def safe_get(d, *keys):
    cur = d
    for key in keys:
        if cur is None:
            return None
        cur = cur.get(key)
    return cur


def to_json(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def get_card_list():
    resp = requests.get(CARDS_LIST_URL, timeout=60)
    resp.raise_for_status()
    return resp.json()


def get_full_card(card_id):
    encoded_id = quote(card_id, safe="")
    url = f"{BASE_URL}/cards/{encoded_id}"

    resp = requests.get(url, timeout=60)

    if resp.status_code == 404:
        print(f"Detail endpoint missing for {card_id}, using list data", flush=True)
        return None

    resp.raise_for_status()
    return resp.json()


def extract_price_row(card, snapshot_ts):
    pricing = card.get("pricing") or {}

    cardmarket = pricing.get("cardmarket") or {}
    tcgplayer = pricing.get("tcgplayer") or {}

    return {
        "card_id": card.get("id"),
        "set_id": safe_get(card, "set", "id"),
        "set_name": safe_get(card, "set", "name"),
        "local_id": card.get("localId"),
        "name": card.get("name"),
        "snapshot_timestamp": snapshot_ts,
        "source_language": LANGUAGE,

        # top-level raw pricing JSON
        "pricing_json": to_json(pricing),

        # cardmarket block
        "cardmarket_updated_at": cardmarket.get("updatedAt"),
        "cardmarket_url": cardmarket.get("url"),
        "cardmarket_avg_sell_price": cardmarket.get("avgSellPrice"),
        "cardmarket_low_price": cardmarket.get("lowPrice"),
        "cardmarket_trend_price": cardmarket.get("trendPrice"),
        "cardmarket_reverse_holo_sell": cardmarket.get("reverseHoloSell"),
        "cardmarket_reverse_holo_low": cardmarket.get("reverseHoloLow"),
        "cardmarket_reverse_holo_trend": cardmarket.get("reverseHoloTrend"),
        "cardmarket_holo_sell": cardmarket.get("holoSell"),
        "cardmarket_holo_low": cardmarket.get("holoLow"),
        "cardmarket_holo_trend": cardmarket.get("holoTrend"),

        # tcgplayer block as raw JSON because nested shapes can vary
        "tcgplayer_updated_at": tcgplayer.get("updatedAt"),
        "tcgplayer_url": tcgplayer.get("url"),
        "tcgplayer_prices_json": to_json(tcgplayer.get("prices")),

        # provenance
        "load_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def build_price_rows(cards_brief, limit=None):
    rows = []
    cards_to_pull = cards_brief[:limit] if limit else cards_brief
    total = len(cards_to_pull)
    snapshot_ts = datetime.now(timezone.utc).isoformat()

    for i, brief in enumerate(cards_to_pull, start=1):
        card_id = brief["id"]
        card = get_full_card(card_id)

        if card is None:
            card = brief

        row = extract_price_row(card, snapshot_ts)
        rows.append(row)

        if i % 100 == 0 or i == total:
            print(f"Fetched pricing for {i}/{total} cards", flush=True)

        time.sleep(0.03)

    return rows


def get_card_price_df(limit=None):
    print("Getting card list...", flush=True)
    cards_brief = get_card_list()
    print(f"Found {len(cards_brief)} cards", flush=True)

    print("Building price rows...", flush=True)
    rows = build_price_rows(cards_brief, limit=limit)

    df = pd.DataFrame(rows)
    return df


def load_to_bigquery(df):
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        schema=[
            bigquery.SchemaField("card_id", "STRING"),
            bigquery.SchemaField("set_id", "STRING"),
            bigquery.SchemaField("set_name", "STRING"),
            bigquery.SchemaField("local_id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("snapshot_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("source_language", "STRING"),

            bigquery.SchemaField("pricing_json", "STRING"),

            bigquery.SchemaField("cardmarket_updated_at", "STRING"),
            bigquery.SchemaField("cardmarket_url", "STRING"),
            bigquery.SchemaField("cardmarket_avg_sell_price", "FLOAT"),
            bigquery.SchemaField("cardmarket_low_price", "FLOAT"),
            bigquery.SchemaField("cardmarket_trend_price", "FLOAT"),
            bigquery.SchemaField("cardmarket_reverse_holo_sell", "FLOAT"),
            bigquery.SchemaField("cardmarket_reverse_holo_low", "FLOAT"),
            bigquery.SchemaField("cardmarket_reverse_holo_trend", "FLOAT"),
            bigquery.SchemaField("cardmarket_holo_sell", "FLOAT"),
            bigquery.SchemaField("cardmarket_holo_low", "FLOAT"),
            bigquery.SchemaField("cardmarket_holo_trend", "FLOAT"),

            bigquery.SchemaField("tcgplayer_updated_at", "STRING"),
            bigquery.SchemaField("tcgplayer_url", "STRING"),
            bigquery.SchemaField("tcgplayer_prices_json", "STRING"),

            bigquery.SchemaField("load_timestamp", "TIMESTAMP"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Loaded {len(df)} pricing rows to {table_ref}", flush=True)

def align_price_dataframe_types(df):
    string_cols = [
        "card_id",
        "set_id",
        "set_name",
        "local_id",
        "name",
        "source_language",
        "pricing_json",
        "cardmarket_updated_at",
        "cardmarket_url",
        "tcgplayer_updated_at",
        "tcgplayer_url",
        "tcgplayer_prices_json",
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    float_cols = [
        "cardmarket_avg_sell_price",
        "cardmarket_low_price",
        "cardmarket_trend_price",
        "cardmarket_reverse_holo_sell",
        "cardmarket_reverse_holo_low",
        "cardmarket_reverse_holo_trend",
        "cardmarket_holo_sell",
        "cardmarket_holo_low",
        "cardmarket_holo_trend",
    ]

    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    timestamp_cols = [
        "snapshot_timestamp",
        "load_timestamp",
    ]

    for col in timestamp_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")

    return df

def main():
def main():
    df = get_card_price_df(limit=100)

    df = align_price_dataframe_types(df)

    print("Dtypes after alignment:", flush=True)
    print(df.dtypes, flush=True)

    load_to_bigquery(df)


if __name__ == "__main__":
    main()

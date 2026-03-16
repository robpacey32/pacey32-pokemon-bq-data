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
TABLE_ID = "card_detail"
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
        print(f"Detail endpoint missing for {card_id}, using list data")
        return None

    resp.raise_for_status()
    return resp.json()


def build_card_rows(cards_brief, limit=None):
    rows = []
    cards_to_pull = cards_brief[:limit] if limit else cards_brief
    total = len(cards_to_pull)

    for i, brief in enumerate(cards_to_pull, start=1):
        card_id = brief["id"]
        card = get_full_card(card_id)

        if card is None:
            card = brief

        row = {
            "card_id": card.get("id"),
            "local_id": card.get("localId"),
            "name": card.get("name"),
            "image_url": card.get("image"),
            "category": card.get("category"),
            "illustrator": card.get("illustrator"),
            "rarity": card.get("rarity"),
            "hp": card.get("hp"),
            "set_id": safe_get(card, "set", "id"),
            "set_name": safe_get(card, "set", "name"),
            "set_logo": safe_get(card, "set", "logo"),
            "set_symbol": safe_get(card, "set", "symbol"),
            "series_id": safe_get(card, "set", "serie", "id"),
            "series_name": safe_get(card, "set", "serie", "name"),
            "cardmarket_id": safe_get(card, "thirdParty", "cardmarket"),
            "tcgplayer_id": safe_get(card, "thirdParty", "tcgplayer"),
            "types_json": to_json(card.get("types")),
            "supertypes_json": to_json(card.get("supertypes")),
            "subtypes_json": to_json(card.get("subtypes")),
            "abilities_json": to_json(card.get("abilities")),
            "attacks_json": to_json(card.get("attacks")),
            "weaknesses_json": to_json(card.get("weaknesses")),
            "resistances_json": to_json(card.get("resistances")),
            "retreat": card.get("retreat"),
            "description": card.get("description"),
            "dex_id_json": to_json(card.get("dexId")),
            "stage": card.get("stage"),
            "level": card.get("level"),
            "suffix": card.get("suffix"),
            "trainer_type": card.get("trainerType"),
            "regulation_mark": card.get("regulationMark"),
            "variants_json": to_json(card.get("variants")),
            "legal_json": to_json(card.get("legal")),
            "third_party_json": to_json(card.get("thirdParty")),
            "pricing_json": to_json(card.get("pricing")),
            "raw_json": to_json(card),
            "source_language": LANGUAGE,
            "load_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        rows.append(row)

        if i % 100 == 0 or i == total:
            print(f"Fetched {i}/{total} cards", flush=True)

        time.sleep(0.03)

    return rows


def get_card_detail_df(limit=None):
    cards_brief = get_card_list()
    rows = build_card_rows(cards_brief, limit=limit)
    return pd.DataFrame(rows)


def load_to_bigquery(df):
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("card_id", "STRING"),
            bigquery.SchemaField("local_id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("image_url", "STRING"),
            bigquery.SchemaField("category", "STRING"),
            bigquery.SchemaField("illustrator", "STRING"),
            bigquery.SchemaField("rarity", "STRING"),
            bigquery.SchemaField("hp", "STRING"),
            bigquery.SchemaField("set_id", "STRING"),
            bigquery.SchemaField("set_name", "STRING"),
            bigquery.SchemaField("set_logo", "STRING"),
            bigquery.SchemaField("set_symbol", "STRING"),
            bigquery.SchemaField("series_id", "STRING"),
            bigquery.SchemaField("series_name", "STRING"),
            bigquery.SchemaField("cardmarket_id", "INT64"),
            bigquery.SchemaField("tcgplayer_id", "INT64"),
            bigquery.SchemaField("types_json", "STRING"),
            bigquery.SchemaField("supertypes_json", "STRING"),
            bigquery.SchemaField("subtypes_json", "STRING"),
            bigquery.SchemaField("abilities_json", "STRING"),
            bigquery.SchemaField("attacks_json", "STRING"),
            bigquery.SchemaField("weaknesses_json", "STRING"),
            bigquery.SchemaField("resistances_json", "STRING"),
            bigquery.SchemaField("retreat", "INT64"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("dex_id_json", "STRING"),
            bigquery.SchemaField("stage", "STRING"),
            bigquery.SchemaField("level", "STRING"),
            bigquery.SchemaField("suffix", "STRING"),
            bigquery.SchemaField("trainer_type", "STRING"),
            bigquery.SchemaField("regulation_mark", "STRING"),
            bigquery.SchemaField("variants_json", "STRING"),
            bigquery.SchemaField("legal_json", "STRING"),
            bigquery.SchemaField("third_party_json", "STRING"),
            bigquery.SchemaField("pricing_json", "STRING"),
            bigquery.SchemaField("raw_json", "STRING"),
            bigquery.SchemaField("source_language", "STRING"),
            bigquery.SchemaField("load_timestamp", "TIMESTAMP"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Loaded {len(df)} rows to {table_ref}", flush=True)

def align_dataframe_types(df):
    # columns that BigQuery schema expects as STRING
    string_cols = [
        "card_id", "local_id", "name", "image_url", "category",
        "illustrator", "rarity", "hp", "set_id", "set_name",
        "set_logo", "set_symbol", "series_id", "series_name",
        "types_json", "supertypes_json", "subtypes_json",
        "abilities_json", "attacks_json", "weaknesses_json",
        "resistances_json", "description", "dex_id_json", "stage",
        "level", "suffix", "trainer_type", "regulation_mark",
        "variants_json", "legal_json", "third_party_json",
        "pricing_json", "raw_json", "source_language"
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    # columns that BigQuery schema expects as INT64
    int_cols = ["cardmarket_id", "tcgplayer_id", "retreat"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # columns that BigQuery schema expects as TIMESTAMP
    if "load_timestamp" in df.columns:
        df["load_timestamp"] = pd.to_datetime(df["load_timestamp"], utc=True)

    return df


def main():
    df = get_card_detail_df(limit=None)

    print(df.head(), flush=True)
    print(df.shape, flush=True)
    print(df.dtypes, flush=True)

    df = align_dataframe_types(df)

    print("Dtypes after alignment:", flush=True)
    print(df.dtypes, flush=True)

    load_to_bigquery(df)

if __name__ == "__main__":
    main()

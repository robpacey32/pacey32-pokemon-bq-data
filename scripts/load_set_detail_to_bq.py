import json
from datetime import datetime, timezone

import pandas as pd
import requests
from google.cloud import bigquery

PROJECT_ID = "pokemon-pacey32-github"
DATASET_ID = "pokemondatafromapi"
TABLE_ID = "set_detail"
LANGUAGE = "en"

SETS_URL = f"https://api.tcgdex.net/v2/{LANGUAGE}/sets"


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


def get_bq_client():
    return bigquery.Client(project=PROJECT_ID)


def fetch_sets():
    resp = requests.get(SETS_URL, timeout=60)
    resp.raise_for_status()
    return resp.json()


def build_rows(sets_data):
    load_ts = datetime.now(timezone.utc)

    rows = []
    for s in sets_data:
        row = {
            "set_id": s.get("id"),
            "set_name": s.get("name"),
            "series_id": safe_get(s, "serie", "id"),
            "series_name": safe_get(s, "serie", "name"),
            "release_date": s.get("releaseDate"),
            "symbol_url": s.get("symbol"),
            "logo_url": s.get("logo"),
            "card_count_total": safe_get(s, "cardCount", "total"),
            "card_count_official": safe_get(s, "cardCount", "official"),
            "raw_json": to_json(s),
            "source_language": LANGUAGE,
            "load_timestamp": load_ts,
        }
        rows.append(row)

    return pd.DataFrame(rows)


def align_dataframe_types(df):
    string_cols = [
        "set_id",
        "set_name",
        "series_id",
        "series_name",
        "symbol_url",
        "logo_url",
        "raw_json",
        "source_language",
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    int_cols = [
        "card_count_total",
        "card_count_official",
    ]

    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    if "release_date" in df.columns:
        df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce").dt.date

    if "load_timestamp" in df.columns:
        df["load_timestamp"] = pd.to_datetime(df["load_timestamp"], utc=True, errors="coerce")

    return df


def load_to_bigquery(df):
    client = get_bq_client()
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        schema=[
            bigquery.SchemaField("set_id", "STRING"),
            bigquery.SchemaField("set_name", "STRING"),
            bigquery.SchemaField("series_id", "STRING"),
            bigquery.SchemaField("series_name", "STRING"),
            bigquery.SchemaField("release_date", "DATE"),
            bigquery.SchemaField("symbol_url", "STRING"),
            bigquery.SchemaField("logo_url", "STRING"),
            bigquery.SchemaField("card_count_total", "INT64"),
            bigquery.SchemaField("card_count_official", "INT64"),
            bigquery.SchemaField("raw_json", "STRING"),
            bigquery.SchemaField("source_language", "STRING"),
            bigquery.SchemaField("load_timestamp", "TIMESTAMP"),
        ],
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()
    print(f"Loaded {len(df)} rows to {table_ref}", flush=True)


def main():
    sets_data = fetch_sets()
    df = build_rows(sets_data)
    df = align_dataframe_types(df)

    print(df.head(), flush=True)
    print(df.shape, flush=True)
    print(df.dtypes, flush=True)

    load_to_bigquery(df)


if __name__ == "__main__":
    main()

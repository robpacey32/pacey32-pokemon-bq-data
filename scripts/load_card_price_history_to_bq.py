import json
import time
from datetime import datetime, timezone
from urllib.parse import quote

import pandas as pd
import requests
from google.cloud import bigquery
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -----------------------------
# CONFIG
# -----------------------------
PROJECT_ID = "pokemon-pacey32-github"
DATASET_ID = "pokemondatafromapi"
TABLE_ID = "card_price_history"
FAILED_TABLE_ID = "card_price_failed"
LANGUAGE = "en"
RUN_TYPE = "weekly_full"

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


def get_retry_session():
    session = requests.Session()

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def get_card_list(session):
    resp = session.get(CARDS_LIST_URL, timeout=(10, 60))
    resp.raise_for_status()
    return resp.json()


def get_full_card(card_id, session):
    encoded_id = quote(card_id, safe="")
    url = f"{BASE_URL}/cards/{encoded_id}"

    try:
        resp = session.get(url, timeout=(10, 60))

        if resp.status_code == 404:
            print(f"Detail endpoint missing for {card_id}, using list data", flush=True)
            return None, None

        resp.raise_for_status()
        return resp.json(), None

    except requests.exceptions.ReadTimeout as e:
        return None, {
            "card_id": card_id,
            "error_type": "ReadTimeout",
            "error_message": str(e),
        }

    except requests.exceptions.RequestException as e:
        return None, {
            "card_id": card_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
        }


def extract_price_row(card, snapshot_ts):
    pricing = card.get("pricing") or {}

    cardmarket = pricing.get("cardmarket") or {}
    tcgplayer = pricing.get("tcgplayer") or {}

    holofoil = tcgplayer.get("holofoil") or {}
    normal = tcgplayer.get("normal") or {}
    reverse_holofoil = tcgplayer.get("reverseHolofoil") or {}

    return {
        "card_id": card.get("id"),
        "set_id": safe_get(card, "set", "id"),
        "set_name": safe_get(card, "set", "name"),
        "local_id": card.get("localId"),
        "name": card.get("name"),
        "snapshot_timestamp": snapshot_ts,
        "source_language": LANGUAGE,
        "pricing_json": to_json(pricing),

        # Cardmarket
        "cardmarket_updated_at": cardmarket.get("updated"),
        "cardmarket_id_product": cardmarket.get("idProduct"),
        "cardmarket_unit": cardmarket.get("unit"),
        "cardmarket_avg": cardmarket.get("avg"),
        "cardmarket_low": cardmarket.get("low"),
        "cardmarket_trend": cardmarket.get("trend"),
        "cardmarket_avg_1": cardmarket.get("avg1"),
        "cardmarket_avg_7": cardmarket.get("avg7"),
        "cardmarket_avg_30": cardmarket.get("avg30"),
        "cardmarket_avg_holo": cardmarket.get("avg-holo"),
        "cardmarket_low_holo": cardmarket.get("low-holo"),
        "cardmarket_trend_holo": cardmarket.get("trend-holo"),
        "cardmarket_avg_1_holo": cardmarket.get("avg1-holo"),
        "cardmarket_avg_7_holo": cardmarket.get("avg7-holo"),
        "cardmarket_avg_30_holo": cardmarket.get("avg30-holo"),

        # TCGplayer
        "tcgplayer_updated_at": tcgplayer.get("updated"),
        "tcgplayer_unit": tcgplayer.get("unit"),
        "tcgplayer_normal_market_price": normal.get("marketPrice"),
        "tcgplayer_normal_low_price": normal.get("lowPrice"),
        "tcgplayer_normal_mid_price": normal.get("midPrice"),
        "tcgplayer_normal_high_price": normal.get("highPrice"),
        "tcgplayer_normal_direct_low_price": normal.get("directLowPrice"),
        "tcgplayer_holofoil_market_price": holofoil.get("marketPrice"),
        "tcgplayer_holofoil_low_price": holofoil.get("lowPrice"),
        "tcgplayer_holofoil_mid_price": holofoil.get("midPrice"),
        "tcgplayer_holofoil_high_price": holofoil.get("highPrice"),
        "tcgplayer_holofoil_direct_low_price": holofoil.get("directLowPrice"),
        "tcgplayer_reverse_holofoil_market_price": reverse_holofoil.get("marketPrice"),
        "tcgplayer_reverse_holofoil_low_price": reverse_holofoil.get("lowPrice"),
        "tcgplayer_reverse_holofoil_mid_price": reverse_holofoil.get("midPrice"),
        "tcgplayer_reverse_holofoil_high_price": reverse_holofoil.get("highPrice"),
        "tcgplayer_reverse_holofoil_direct_low_price": reverse_holofoil.get("directLowPrice"),

        "load_timestamp": pd.Timestamp.now(tz="UTC"),
    }


def build_price_rows(cards_brief, limit=None):
    rows = []
    failed_cards = []
    session = get_retry_session()

    cards_to_pull = cards_brief[:limit] if limit else cards_brief
    total = len(cards_to_pull)
    snapshot_ts = datetime.now(timezone.utc).isoformat()

    for i, brief in enumerate(cards_to_pull, start=1):
        card_id = brief["id"]
        card, error = get_full_card(card_id, session)

        if error:
            failed_cards.append(error)
            print(f"FAILED: {card_id} -> {error['error_type']}", flush=True)
            continue

        if card is None:
            card = brief

        row = extract_price_row(card, snapshot_ts)
        rows.append(row)

        if i % 100 == 0 or i == total:
            print(
                f"Fetched pricing for {i}/{total} cards | Success: {len(rows)} | Failed: {len(failed_cards)}",
                flush=True,
            )
            time.sleep(1)

        time.sleep(0.03)

    return rows, failed_cards


def get_card_price_df(limit=None):
    session = get_retry_session()

    print("Getting card list...", flush=True)
    cards_brief = get_card_list(session)
    print(f"Found {len(cards_brief)} cards", flush=True)

    print("Building price rows...", flush=True)
    rows, failed_cards = build_price_rows(cards_brief, limit=limit)

    df = pd.DataFrame(rows)
    return df, failed_cards


def save_failed_cards_to_bigquery(failed_cards):
    if not failed_cards:
        print("No failed cards to save.", flush=True)
        return

    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{FAILED_TABLE_ID}"
    failed_at = datetime.now(timezone.utc).isoformat()

    rows = []
    for item in failed_cards:
        rows.append(
            {
                "card_id": item.get("card_id"),
                "error_type": item.get("error_type"),
                "error_message": item.get("error_message"),
                "failed_at": failed_at,
                "run_type": RUN_TYPE,
            }
        )

    errors = client.insert_rows_json(table_ref, rows)

    if errors:
        print("Failed to insert some failed-card rows:", flush=True)
        print(errors, flush=True)
    else:
        print(f"Saved {len(rows)} failed card(s) to {table_ref}", flush=True)


def load_to_bigquery(df):
    if df.empty:
        print("No successful pricing rows to load.", flush=True)
        return

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
            bigquery.SchemaField("cardmarket_id_product", "INT64"),
            bigquery.SchemaField("cardmarket_unit", "STRING"),
            bigquery.SchemaField("cardmarket_avg", "FLOAT"),
            bigquery.SchemaField("cardmarket_low", "FLOAT"),
            bigquery.SchemaField("cardmarket_trend", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_1", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_7", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_30", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_holo", "FLOAT"),
            bigquery.SchemaField("cardmarket_low_holo", "FLOAT"),
            bigquery.SchemaField("cardmarket_trend_holo", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_1_holo", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_7_holo", "FLOAT"),
            bigquery.SchemaField("cardmarket_avg_30_holo", "FLOAT"),
            bigquery.SchemaField("tcgplayer_updated_at", "STRING"),
            bigquery.SchemaField("tcgplayer_unit", "STRING"),
            bigquery.SchemaField("tcgplayer_normal_market_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_normal_low_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_normal_mid_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_normal_high_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_normal_direct_low_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_holofoil_market_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_holofoil_low_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_holofoil_mid_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_holofoil_high_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_holofoil_direct_low_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_reverse_holofoil_market_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_reverse_holofoil_low_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_reverse_holofoil_mid_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_reverse_holofoil_high_price", "FLOAT"),
            bigquery.SchemaField("tcgplayer_reverse_holofoil_direct_low_price", "FLOAT"),
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
        "cardmarket_unit",
        "tcgplayer_updated_at",
        "tcgplayer_unit",
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string")

    int_cols = [
        "cardmarket_id_product",
    ]

    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    float_cols = [
        "cardmarket_avg",
        "cardmarket_low",
        "cardmarket_trend",
        "cardmarket_avg_1",
        "cardmarket_avg_7",
        "cardmarket_avg_30",
        "cardmarket_avg_holo",
        "cardmarket_low_holo",
        "cardmarket_trend_holo",
        "cardmarket_avg_1_holo",
        "cardmarket_avg_7_holo",
        "cardmarket_avg_30_holo",
        "tcgplayer_normal_market_price",
        "tcgplayer_normal_low_price",
        "tcgplayer_normal_mid_price",
        "tcgplayer_normal_high_price",
        "tcgplayer_normal_direct_low_price",
        "tcgplayer_holofoil_market_price",
        "tcgplayer_holofoil_low_price",
        "tcgplayer_holofoil_mid_price",
        "tcgplayer_holofoil_high_price",
        "tcgplayer_holofoil_direct_low_price",
        "tcgplayer_reverse_holofoil_market_price",
        "tcgplayer_reverse_holofoil_low_price",
        "tcgplayer_reverse_holofoil_mid_price",
        "tcgplayer_reverse_holofoil_high_price",
        "tcgplayer_reverse_holofoil_direct_low_price",
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
    df, failed_cards = get_card_price_df(limit=None)

    df = align_price_dataframe_types(df)

    print("Dtypes after alignment:", flush=True)
    print(df.dtypes, flush=True)

    load_to_bigquery(df)
    save_failed_cards_to_bigquery(failed_cards)

    print(
        f"Run complete. Successful cards: {len(df)} | Failed cards: {len(failed_cards)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
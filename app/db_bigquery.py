import os
import json
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "pokemon-pacey32-github"

creds_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
credentials = service_account.Credentials.from_service_account_info(creds_info)

client = bigquery.Client(
    project=PROJECT_ID,
    credentials=credentials
)


def run_query(sql: str) -> pd.DataFrame:
    query_job = client.query(sql)
    return query_job.to_dataframe()


def get_fx_rate(base_currency: str, target_currency: str) -> float:
    if base_currency == target_currency:
        return 1.0

    sql = f"""
    SELECT exchange_rate
    FROM `pokemon-pacey32-github.pokemonApp.currency_rates_latest_vw`
    WHERE base_currency = '{base_currency}'
      AND target_currency = '{target_currency}'
    LIMIT 1
    """
    df = run_query(sql)

    if df.empty:
        return 1.0

    return float(df.iloc[0]["exchange_rate"])


def get_series_list() -> list:
    sql = """
    SELECT
        series_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    WHERE series_name IS NOT NULL
    GROUP BY series_name
    ORDER BY MIN(release_date) IS NULL, MIN(release_date), series_name
    """
    df = run_query(sql)
    return df["series_name"].dropna().tolist()


def get_set_list(series_name: str | None = None) -> list:
    filters = ["set_name IS NOT NULL"]

    if series_name and series_name != "All":
        safe_series = series_name.replace("'", "\\'")
        filters.append(f"series_name = '{safe_series}'")

    where_clause = "WHERE " + " AND ".join(filters)

    sql = f"""
    SELECT
        set_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    GROUP BY set_name
    ORDER BY MIN(release_date) IS NULL, MIN(release_date), set_name
    """
    df = run_query(sql)
    return df["set_name"].dropna().tolist()


def get_card_master(
    series_name: str | None = None,
    set_name: str | None = None,
    card_name_search: str | None = None,
    limit: int = 500,
) -> pd.DataFrame:

    filters = []

    if series_name and series_name != "All":
        safe_series = series_name.replace("'", "\\'")
        filters.append(f"series_name = '{safe_series}'")

    if set_name and set_name != "All":
        safe_set = set_name.replace("'", "\\'")
        filters.append(f"set_name = '{safe_set}'")

    if card_name_search:
        safe_name = card_name_search.replace("'", "\\'")
        filters.append(f"LOWER(name) LIKE LOWER('%{safe_name}%')")

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    sql = f"""
    SELECT
        card_id,
        name,
        local_id,
        set_id,
        set_name,
        series_id,
        series_name,
        release_date,
        rarity,
        image_url,
        symbol_url,
        logo_url,
        cardmarket_avg,
        cardmarket_low,
        cardmarket_trend,
        snapshot_timestamp
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    ORDER BY release_date, set_name, local_id
    LIMIT {limit}
    """

    return run_query(sql)
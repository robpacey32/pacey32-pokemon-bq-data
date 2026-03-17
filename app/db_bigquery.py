import pandas as pd
from google.cloud import bigquery

PROJECT_ID = "pokemon-pacey32-github"

client = bigquery.Client(project=PROJECT_ID)


def run_query(sql: str) -> pd.DataFrame:
    query_job = client.query(sql)
    return query_job.to_dataframe()


def get_series_list() -> list:
    sql = """
    SELECT DISTINCT series_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    WHERE series_name IS NOT NULL
    ORDER BY series_name
    """
    df = run_query(sql)
    return df["series_name"].dropna().tolist()


def get_set_list(series_name: str | None = None) -> list:
    where_clause = ""
    if series_name and series_name != "All":
        safe_series = series_name.replace("'", "\\'")
        where_clause = f"WHERE series_name = '{safe_series}'"

    sql = f"""
    SELECT DISTINCT set_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    AND set_name IS NOT NULL
    ORDER BY set_name
    """ if where_clause else """
    SELECT DISTINCT set_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    WHERE set_name IS NOT NULL
    ORDER BY set_name
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
        series_name,
        rarity,
        image_url,
        cardmarket_avg,
        cardmarket_low,
        cardmarket_trend,
        snapshot_timestamp
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    ORDER BY series_name, set_name, local_id
    LIMIT {limit}
    """

    return run_query(sql)
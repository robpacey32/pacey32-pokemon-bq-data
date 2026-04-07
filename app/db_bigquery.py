import os
import json
import re
import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

PROJECT_ID = "pokemon-pacey32-github"

if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
    creds_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    client = bigquery.Client(project=PROJECT_ID, credentials=credentials)
else:
    client = bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    return client.query(sql).to_dataframe()


def _escape_sql(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate(base_currency: str, target_currency: str) -> float:
    if base_currency == target_currency:
        return 1.0

    sql = f"""
    SELECT exchange_rate
    FROM `pokemon-pacey32-github.pokemonApp.currency_rates_latest_vw`
    WHERE base_currency = '{_escape_sql(base_currency)}'
      AND target_currency = '{_escape_sql(target_currency)}'
    LIMIT 1
    """
    df = run_query(sql)
    if df.empty:
        return 1.0
    return float(df.iloc[0]["exchange_rate"])


@st.cache_data(ttl=3600, show_spinner=False)
def get_series_list() -> list:
    sql = """
    SELECT series_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    WHERE series_name IS NOT NULL
    GROUP BY series_name
    ORDER BY MIN(release_date) IS NULL, MIN(release_date), series_name
    """
    df = run_query(sql)
    return df["series_name"].dropna().tolist()


@st.cache_data(ttl=3600, show_spinner=False)
def get_set_list(series_name: str | None = None) -> list:
    filters = ["set_name IS NOT NULL"]

    if series_name and series_name != "All":
        filters.append(f"series_name = '{_escape_sql(series_name)}'")

    where_clause = "WHERE " + " AND ".join(filters)

    sql = f"""
    SELECT set_name
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    GROUP BY set_name
    ORDER BY MIN(release_date) IS NULL, MIN(release_date), set_name
    """
    df = run_query(sql)
    return df["set_name"].dropna().tolist()


def parse_smart_search(search_text: str) -> dict:
    if not search_text:
        return {
            "exact_card_id": None,
            "set_text": None,
            "local_id": None,
            "name_text": None,
        }

    s = search_text.strip().lower()

    if re.fullmatch(r"[a-z0-9]+-\d+[a-z]?", s):
        return {
            "exact_card_id": s,
            "set_text": None,
            "local_id": None,
            "name_text": None,
        }

    m = re.fullmatch(r"(.+?)\s+(\d+[a-z]?)", s)
    if m:
        return {
            "exact_card_id": None,
            "set_text": m.group(1).strip(),
            "local_id": m.group(2).strip(),
            "name_text": None,
        }

    if re.fullmatch(r"\d+[a-z]?", s):
        return {
            "exact_card_id": None,
            "set_text": None,
            "local_id": s,
            "name_text": None,
        }

    return {
        "exact_card_id": None,
        "set_text": None,
        "local_id": None,
        "name_text": s,
    }


def _build_set_name_filter(set_text: str) -> str:
    safe_set_text = set_text.strip().lower()

    set_aliases = {
        "base": ["base", "base set"],
        "base set": ["base", "base set"],
        "jungle": ["jungle"],
        "fossil": ["fossil"],
        "rocket": ["rocket", "team rocket"],
        "team rocket": ["rocket", "team rocket"],
        "gym heroes": ["gym heroes"],
        "gym challenge": ["gym challenge"],
        "neo genesis": ["neo genesis"],
        "neo discovery": ["neo discovery"],
        "neo revelation": ["neo revelation"],
        "neo destiny": ["neo destiny"],
    }

    aliases = set_aliases.get(safe_set_text, [safe_set_text])

    alias_filters = []
    for alias in aliases:
        alias_filters.append(
            f"LOWER(set_name) LIKE LOWER('%{_escape_sql(alias)}%')"
        )

    return "(" + " OR ".join(alias_filters) + ")"


def _select_display_currency_columns(df: pd.DataFrame) -> pd.DataFrame:
    display_currency = st.session_state.get("display_currency", "GBP").lower()

    rename_map = {
        f"cardmarket_avg_display_{display_currency}": "cardmarket_avg_display",
        f"cardmarket_low_display_{display_currency}": "cardmarket_low_display",
        f"cardmarket_trend_display_{display_currency}": "cardmarket_trend_display",
        f"cardmarket_avg_holo_display_{display_currency}": "cardmarket_avg_holo_display",
        f"cardmarket_low_holo_display_{display_currency}": "cardmarket_low_holo_display",
        f"cardmarket_trend_holo_display_{display_currency}": "cardmarket_trend_holo_display",
        f"tcgplayer_normal_market_price_display_{display_currency}": "tcgplayer_normal_market_price_display",
        f"tcgplayer_holofoil_market_price_display_{display_currency}": "tcgplayer_holofoil_market_price_display",
        f"tcgplayer_reverse_holofoil_market_price_display_{display_currency}": "tcgplayer_reverse_holofoil_market_price_display",
        f"display_normal_price_display_{display_currency}": "display_normal_price_display",
        f"display_holofoil_price_display_{display_currency}": "display_holofoil_price_display",
        f"display_reverse_holofoil_price_display_{display_currency}": "display_reverse_holofoil_price_display",
    }

    existing = {k: v for k, v in rename_map.items() if k in df.columns}
    return df.rename(columns=existing)


def _display_price_case_sql(
    raw_col: str,
    source_col: str,
    target_currency: str,
    eur_to_gbp: float,
    eur_to_usd: float,
    usd_to_gbp: float,
    usd_to_eur: float,
) -> str:
    if target_currency == "EUR":
        cardmarket_expr = raw_col
        tcgplayer_expr = f"{raw_col} * {usd_to_eur}"
    elif target_currency == "USD":
        cardmarket_expr = f"{raw_col} * {eur_to_usd}"
        tcgplayer_expr = raw_col
    else:
        cardmarket_expr = f"{raw_col} * {eur_to_gbp}"
        tcgplayer_expr = f"{raw_col} * {usd_to_gbp}"

    return f"""
    CASE
      WHEN {source_col} LIKE 'Cardmarket%' THEN {cardmarket_expr}
      WHEN {source_col} LIKE 'Last Cardmarket%' THEN {cardmarket_expr}
      WHEN {source_col} LIKE 'TCGPlayer%' THEN {tcgplayer_expr}
      WHEN {source_col} LIKE 'Last TCGPlayer%' THEN {tcgplayer_expr}
      ELSE {raw_col}
    END
    """


@st.cache_data(ttl=300, show_spinner=False)
def get_card_master(
    series_name: str | None = None,
    set_name: str | None = None,
    card_name_search: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
    display_currency: str = "GBP",
) -> pd.DataFrame:
    filters = []

    if series_name and series_name != "All":
        filters.append(f"series_name = '{_escape_sql(series_name)}'")

    if set_name and set_name != "All":
        filters.append(f"set_name = '{_escape_sql(set_name)}'")

    parsed = parse_smart_search(card_name_search or "")

    if parsed["exact_card_id"]:
        filters.append(f"LOWER(card_id) = LOWER('{_escape_sql(parsed['exact_card_id'])}')")
    elif parsed["set_text"] and parsed["local_id"]:
        filters.append(_build_set_name_filter(parsed["set_text"]))
        filters.append(f"LOWER(local_id) = LOWER('{_escape_sql(parsed['local_id'])}')")
    elif parsed["local_id"]:
        filters.append(f"LOWER(local_id) = LOWER('{_escape_sql(parsed['local_id'])}')")
    elif parsed["name_text"]:
        filters.append(f"LOWER(name) LIKE LOWER('%{_escape_sql(parsed['name_text'])}%')")

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

    if display_currency == "EUR":
        cardmarket_trend_expr = "cardmarket_trend"
        cardmarket_trend_holo_expr = "cardmarket_trend_holo"
        tcgplayer_normal_expr = f"tcgplayer_normal_market_price * {usd_to_eur}"
        tcgplayer_holo_expr = f"tcgplayer_holofoil_market_price * {usd_to_eur}"
        tcgplayer_reverse_expr = f"tcgplayer_reverse_holofoil_market_price * {usd_to_eur}"
    elif display_currency == "USD":
        cardmarket_trend_expr = f"cardmarket_trend * {eur_to_usd}"
        cardmarket_trend_holo_expr = f"cardmarket_trend_holo * {eur_to_usd}"
        tcgplayer_normal_expr = "tcgplayer_normal_market_price"
        tcgplayer_holo_expr = "tcgplayer_holofoil_market_price"
        tcgplayer_reverse_expr = "tcgplayer_reverse_holofoil_market_price"
    else:
        cardmarket_trend_expr = f"cardmarket_trend * {eur_to_gbp}"
        cardmarket_trend_holo_expr = f"cardmarket_trend_holo * {eur_to_gbp}"
        tcgplayer_normal_expr = f"tcgplayer_normal_market_price * {usd_to_gbp}"
        tcgplayer_holo_expr = f"tcgplayer_holofoil_market_price * {usd_to_gbp}"
        tcgplayer_reverse_expr = f"tcgplayer_reverse_holofoil_market_price * {usd_to_gbp}"

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

        variant_first_edition,
        variant_holo,
        variant_normal,
        variant_reverse,
        variant_w_promo,

        {cardmarket_trend_expr} AS cardmarket_trend_display,
        {cardmarket_trend_holo_expr} AS cardmarket_trend_holo_display,
        {tcgplayer_normal_expr} AS tcgplayer_normal_market_price_display,
        {tcgplayer_holo_expr} AS tcgplayer_holofoil_market_price_display,
        {tcgplayer_reverse_expr} AS tcgplayer_reverse_holofoil_market_price_display,

        cardmarket_trend,
        cardmarket_trend_holo,
        tcgplayer_normal_market_price,
        tcgplayer_holofoil_market_price,
        tcgplayer_reverse_holofoil_market_price,
        snapshot_timestamp

    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw`
    {where_clause}
    ORDER BY
        release_date,
        set_name,
        CASE WHEN SAFE_CAST(local_id AS INT64) IS NULL THEN 1 ELSE 0 END,
        SAFE_CAST(local_id AS INT64),
        local_id
    """

    if limit is not None:
        sql += f" LIMIT {limit}"

    if offset is not None:
        sql += f" OFFSET {offset}"

    return run_query(sql)


@st.cache_data(ttl=300, show_spinner=False)
def get_card_detail_by_id(card_id: str) -> pd.DataFrame:
    safe_card_id = _escape_sql(card_id)

    sql = f"""
    SELECT
        m.card_id,
        m.name,
        m.local_id,
        m.set_id,
        m.set_name,
        m.series_id,
        m.series_name,
        m.release_date,
        m.rarity,
        m.image_url,
        m.symbol_url,
        m.logo_url,
        m.variant_first_edition,
        m.variant_holo,
        m.variant_normal,
        m.variant_reverse,
        m.variant_w_promo,
        d.category,
        d.hp,
        d.illustrator,
        d.description,
        d.stage,
        d.level,
        d.suffix,
        d.trainer_type,
        d.regulation_mark
    FROM `pokemon-pacey32-github.pokemonApp.card_master_vw` m
    LEFT JOIN `pokemon-pacey32-github.pokemonApp.card_detail_vw` d
      ON m.card_id = d.card_id
    WHERE m.card_id = '{safe_card_id}'
    LIMIT 1
    """
    return run_query(sql)


@st.cache_data(ttl=300, show_spinner=False)
def get_card_price_history(card_id: str) -> pd.DataFrame:
    safe_card_id = _escape_sql(card_id)
    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

    sql = f"""
    WITH base AS (
      SELECT
          snapshot_timestamp,

          cardmarket_avg,
          cardmarket_low,
          cardmarket_trend,
          cardmarket_avg_holo,
          cardmarket_low_holo,
          cardmarket_trend_holo,
          tcgplayer_normal_market_price,
          tcgplayer_holofoil_market_price,
          tcgplayer_reverse_holofoil_market_price,

          COALESCE(
              tcgplayer_normal_market_price,
              cardmarket_avg
          ) AS display_normal_price,

          CASE
              WHEN tcgplayer_normal_market_price IS NOT NULL THEN 'TCGPlayer Normal'
              WHEN cardmarket_avg IS NOT NULL THEN 'Cardmarket Normal'
              ELSE NULL
          END AS display_normal_source,

          COALESCE(
              tcgplayer_holofoil_market_price,
              cardmarket_avg_holo
          ) AS display_holofoil_price,

          CASE
              WHEN tcgplayer_holofoil_market_price IS NOT NULL THEN 'TCGPlayer Holofoil'
              WHEN cardmarket_avg_holo IS NOT NULL THEN 'Cardmarket Holofoil'
              ELSE NULL
          END AS display_holofoil_source,

          tcgplayer_reverse_holofoil_market_price AS display_reverse_holofoil_price,

          CASE
              WHEN tcgplayer_reverse_holofoil_market_price IS NOT NULL THEN 'TCGPlayer Reverse Holofoil'
              ELSE NULL
          END AS display_reverse_holofoil_source

      FROM `pokemon-pacey32-github.pokemonApp.card_price_history`
      WHERE card_id = '{safe_card_id}'
    )

    SELECT
        snapshot_timestamp,

        cardmarket_avg,
        cardmarket_low,
        cardmarket_trend,
        cardmarket_avg_holo,
        cardmarket_low_holo,
        cardmarket_trend_holo,
        tcgplayer_normal_market_price,
        tcgplayer_holofoil_market_price,
        tcgplayer_reverse_holofoil_market_price,

        display_normal_price,
        display_normal_source,
        display_holofoil_price,
        display_holofoil_source,
        display_reverse_holofoil_price,
        display_reverse_holofoil_source,

        cardmarket_avg AS cardmarket_avg_display_eur,
        cardmarket_low AS cardmarket_low_display_eur,
        cardmarket_trend AS cardmarket_trend_display_eur,
        cardmarket_avg_holo AS cardmarket_avg_holo_display_eur,
        cardmarket_low_holo AS cardmarket_low_holo_display_eur,
        cardmarket_trend_holo AS cardmarket_trend_holo_display_eur,
        tcgplayer_normal_market_price * {usd_to_eur} AS tcgplayer_normal_market_price_display_eur,
        tcgplayer_holofoil_market_price * {usd_to_eur} AS tcgplayer_holofoil_market_price_display_eur,
        tcgplayer_reverse_holofoil_market_price * {usd_to_eur} AS tcgplayer_reverse_holofoil_market_price_display_eur,

        CASE
            WHEN display_normal_source LIKE 'Cardmarket%' THEN display_normal_price
            WHEN display_normal_source LIKE 'TCGPlayer%' THEN display_normal_price * {usd_to_eur}
            ELSE display_normal_price
        END AS display_normal_price_display_eur,

        CASE
            WHEN display_holofoil_source LIKE 'Cardmarket%' THEN display_holofoil_price
            WHEN display_holofoil_source LIKE 'TCGPlayer%' THEN display_holofoil_price * {usd_to_eur}
            ELSE display_holofoil_price
        END AS display_holofoil_price_display_eur,

        CASE
            WHEN display_reverse_holofoil_source LIKE 'TCGPlayer%' THEN display_reverse_holofoil_price * {usd_to_eur}
            ELSE display_reverse_holofoil_price
        END AS display_reverse_holofoil_price_display_eur,

        cardmarket_avg * {eur_to_gbp} AS cardmarket_avg_display_gbp,
        cardmarket_low * {eur_to_gbp} AS cardmarket_low_display_gbp,
        cardmarket_trend * {eur_to_gbp} AS cardmarket_trend_display_gbp,
        cardmarket_avg_holo * {eur_to_gbp} AS cardmarket_avg_holo_display_gbp,
        cardmarket_low_holo * {eur_to_gbp} AS cardmarket_low_holo_display_gbp,
        cardmarket_trend_holo * {eur_to_gbp} AS cardmarket_trend_holo_display_gbp,
        tcgplayer_normal_market_price * {usd_to_gbp} AS tcgplayer_normal_market_price_display_gbp,
        tcgplayer_holofoil_market_price * {usd_to_gbp} AS tcgplayer_holofoil_market_price_display_gbp,
        tcgplayer_reverse_holofoil_market_price * {usd_to_gbp} AS tcgplayer_reverse_holofoil_market_price_display_gbp,

        CASE
            WHEN display_normal_source LIKE 'Cardmarket%' THEN display_normal_price * {eur_to_gbp}
            WHEN display_normal_source LIKE 'TCGPlayer%' THEN display_normal_price * {usd_to_gbp}
            ELSE display_normal_price
        END AS display_normal_price_display_gbp,

        CASE
            WHEN display_holofoil_source LIKE 'Cardmarket%' THEN display_holofoil_price * {eur_to_gbp}
            WHEN display_holofoil_source LIKE 'TCGPlayer%' THEN display_holofoil_price * {usd_to_gbp}
            ELSE display_holofoil_price
        END AS display_holofoil_price_display_gbp,

        CASE
            WHEN display_reverse_holofoil_source LIKE 'TCGPlayer%' THEN display_reverse_holofoil_price * {usd_to_gbp}
            ELSE display_reverse_holofoil_price
        END AS display_reverse_holofoil_price_display_gbp,

        cardmarket_avg * {eur_to_usd} AS cardmarket_avg_display_usd,
        cardmarket_low * {eur_to_usd} AS cardmarket_low_display_usd,
        cardmarket_trend * {eur_to_usd} AS cardmarket_trend_display_usd,
        cardmarket_avg_holo * {eur_to_usd} AS cardmarket_avg_holo_display_usd,
        cardmarket_low_holo * {eur_to_usd} AS cardmarket_low_holo_display_usd,
        cardmarket_trend_holo * {eur_to_usd} AS cardmarket_trend_holo_display_usd,
        tcgplayer_normal_market_price AS tcgplayer_normal_market_price_display_usd,
        tcgplayer_holofoil_market_price AS tcgplayer_holofoil_market_price_display_usd,
        tcgplayer_reverse_holofoil_market_price AS tcgplayer_reverse_holofoil_market_price_display_usd,

        CASE
            WHEN display_normal_source LIKE 'Cardmarket%' THEN display_normal_price * {eur_to_usd}
            WHEN display_normal_source LIKE 'TCGPlayer%' THEN display_normal_price
            ELSE display_normal_price
        END AS display_normal_price_display_usd,

        CASE
            WHEN display_holofoil_source LIKE 'Cardmarket%' THEN display_holofoil_price * {eur_to_usd}
            WHEN display_holofoil_source LIKE 'TCGPlayer%' THEN display_holofoil_price
            ELSE display_holofoil_price
        END AS display_holofoil_price_display_usd,

        CASE
            WHEN display_reverse_holofoil_source LIKE 'TCGPlayer%' THEN display_reverse_holofoil_price
            ELSE display_reverse_holofoil_price
        END AS display_reverse_holofoil_price_display_usd

    FROM base
    ORDER BY snapshot_timestamp
    """
    df = run_query(sql)
    if df.empty:
        return df
    return _select_display_currency_columns(df)


@st.cache_data(ttl=300, show_spinner=False)
def get_card_latest_variant_prices(card_id: str) -> pd.DataFrame:
    safe_card_id = _escape_sql(card_id)
    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

    display_normal_eur = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_normal_gbp = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_normal_usd = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    display_holo_eur = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_holo_gbp = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_holo_usd = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    display_reverse_eur = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_reverse_gbp = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_reverse_usd = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    sql = f"""
    SELECT
        card_id,
        snapshot_timestamp,

        cardmarket_avg,
        cardmarket_low,
        cardmarket_trend,
        cardmarket_avg_holo,
        cardmarket_low_holo,
        cardmarket_trend_holo,
        tcgplayer_normal_market_price,
        tcgplayer_holofoil_market_price,
        tcgplayer_reverse_holofoil_market_price,

        display_normal_price,
        display_normal_source,
        display_holofoil_price,
        display_holofoil_source,
        display_reverse_holofoil_price,
        display_reverse_holofoil_source,

        cardmarket_avg AS cardmarket_avg_display_eur,
        cardmarket_low AS cardmarket_low_display_eur,
        cardmarket_trend AS cardmarket_trend_display_eur,
        cardmarket_avg_holo AS cardmarket_avg_holo_display_eur,
        cardmarket_low_holo AS cardmarket_low_holo_display_eur,
        cardmarket_trend_holo AS cardmarket_trend_holo_display_eur,
        tcgplayer_normal_market_price * {usd_to_eur} AS tcgplayer_normal_market_price_display_eur,
        tcgplayer_holofoil_market_price * {usd_to_eur} AS tcgplayer_holofoil_market_price_display_eur,
        tcgplayer_reverse_holofoil_market_price * {usd_to_eur} AS tcgplayer_reverse_holofoil_market_price_display_eur,
        {display_normal_eur} AS display_normal_price_display_eur,
        {display_holo_eur} AS display_holofoil_price_display_eur,
        {display_reverse_eur} AS display_reverse_holofoil_price_display_eur,

        cardmarket_avg * {eur_to_gbp} AS cardmarket_avg_display_gbp,
        cardmarket_low * {eur_to_gbp} AS cardmarket_low_display_gbp,
        cardmarket_trend * {eur_to_gbp} AS cardmarket_trend_display_gbp,
        cardmarket_avg_holo * {eur_to_gbp} AS cardmarket_avg_holo_display_gbp,
        cardmarket_low_holo * {eur_to_gbp} AS cardmarket_low_holo_display_gbp,
        cardmarket_trend_holo * {eur_to_gbp} AS cardmarket_trend_holo_display_gbp,
        tcgplayer_normal_market_price * {usd_to_gbp} AS tcgplayer_normal_market_price_display_gbp,
        tcgplayer_holofoil_market_price * {usd_to_gbp} AS tcgplayer_holofoil_market_price_display_gbp,
        tcgplayer_reverse_holofoil_market_price * {usd_to_gbp} AS tcgplayer_reverse_holofoil_market_price_display_gbp,
        {display_normal_gbp} AS display_normal_price_display_gbp,
        {display_holo_gbp} AS display_holofoil_price_display_gbp,
        {display_reverse_gbp} AS display_reverse_holofoil_price_display_gbp,

        cardmarket_avg * {eur_to_usd} AS cardmarket_avg_display_usd,
        cardmarket_low * {eur_to_usd} AS cardmarket_low_display_usd,
        cardmarket_trend * {eur_to_usd} AS cardmarket_trend_display_usd,
        cardmarket_avg_holo * {eur_to_usd} AS cardmarket_avg_holo_display_usd,
        cardmarket_low_holo * {eur_to_usd} AS cardmarket_low_holo_display_usd,
        cardmarket_trend_holo * {eur_to_usd} AS cardmarket_trend_holo_display_usd,
        tcgplayer_normal_market_price AS tcgplayer_normal_market_price_display_usd,
        tcgplayer_holofoil_market_price AS tcgplayer_holofoil_market_price_display_usd,
        tcgplayer_reverse_holofoil_market_price AS tcgplayer_reverse_holofoil_market_price_display_usd,
        {display_normal_usd} AS display_normal_price_display_usd,
        {display_holo_usd} AS display_holofoil_price_display_usd,
        {display_reverse_usd} AS display_reverse_holofoil_price_display_usd

    FROM `pokemon-pacey32-github.pokemondatafromapi.card_latest_price_vw`
    WHERE card_id = '{safe_card_id}'
    LIMIT 1
    """
    df = run_query(sql)
    if df.empty:
        return df
    return _select_display_currency_columns(df)


@st.cache_data(ttl=300, show_spinner=False)
def get_card_latest_variant_prices_bulk(card_ids: list[str]) -> pd.DataFrame:
    if not card_ids:
        return pd.DataFrame()

    safe_ids = [f"'{_escape_sql(card_id)}'" for card_id in card_ids]
    ids_sql = ", ".join(safe_ids)

    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

    display_normal_eur = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_normal_gbp = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_normal_usd = _display_price_case_sql(
        "display_normal_price",
        "display_normal_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    display_holo_eur = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_holo_gbp = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_holo_usd = _display_price_case_sql(
        "display_holofoil_price",
        "display_holofoil_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    display_reverse_eur = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "EUR",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_reverse_gbp = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "GBP",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )
    display_reverse_usd = _display_price_case_sql(
        "display_reverse_holofoil_price",
        "display_reverse_holofoil_source",
        "USD",
        eur_to_gbp,
        eur_to_usd,
        usd_to_gbp,
        usd_to_eur,
    )

    sql = f"""
    SELECT
        card_id,
        snapshot_timestamp,
        display_normal_price,
        display_normal_source,
        display_holofoil_price,
        display_holofoil_source,
        display_reverse_holofoil_price,
        display_reverse_holofoil_source,
        {display_normal_eur} AS display_normal_price_display_eur,
        {display_holo_eur} AS display_holofoil_price_display_eur,
        {display_reverse_eur} AS display_reverse_holofoil_price_display_eur,
        {display_normal_gbp} AS display_normal_price_display_gbp,
        {display_holo_gbp} AS display_holofoil_price_display_gbp,
        {display_reverse_gbp} AS display_reverse_holofoil_price_display_gbp,
        {display_normal_usd} AS display_normal_price_display_usd,
        {display_holo_usd} AS display_holofoil_price_display_usd,
        {display_reverse_usd} AS display_reverse_holofoil_price_display_usd
    FROM `pokemon-pacey32-github.pokemondatafromapi.card_latest_price_vw`
    WHERE card_id IN ({ids_sql})
    """
    df = run_query(sql)
    if df.empty:
        return df
    return _select_display_currency_columns(df)
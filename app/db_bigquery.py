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


@st.cache_data(ttl=3600, show_spinner=False)
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
        safe_series = series_name.replace("'", "\\'")
        filters.append(f"series_name = '{safe_series}'")

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

    # exact card id like base1-1
    if re.fullmatch(r"[a-z0-9]+-\d+[a-z]?", s):
        return {
            "exact_card_id": s,
            "set_text": None,
            "local_id": None,
            "name_text": None,
        }

    # set + number like "base 1", "jungle 5", "neo discovery 12"
    m = re.fullmatch(r"(.+?)\s+(\d+[a-z]?)", s)
    if m:
        return {
            "exact_card_id": None,
            "set_text": m.group(1).strip(),
            "local_id": m.group(2).strip(),
            "name_text": None,
        }

    # number only like "123" or "12a"
    if re.fullmatch(r"\d+[a-z]?", s):
        return {
            "exact_card_id": None,
            "set_text": None,
            "local_id": s,
            "name_text": None,
        }

    # fallback = name search
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
        safe_alias = alias.replace("'", "\\'")
        alias_filters.append(f"LOWER(set_name) LIKE LOWER('%{safe_alias}%')")

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
    }

    existing = {k: v for k, v in rename_map.items() if k in df.columns}
    return df.rename(columns=existing)


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
        safe_series = series_name.replace("'", "\\'")
        filters.append(f"series_name = '{safe_series}'")

    if set_name and set_name != "All":
        safe_set = set_name.replace("'", "\\'")
        filters.append(f"set_name = '{safe_set}'")

    parsed = parse_smart_search(card_name_search or "")

    if parsed["exact_card_id"]:
        safe_card_id = parsed["exact_card_id"].replace("'", "\\'")
        filters.append(f"LOWER(card_id) = LOWER('{safe_card_id}')")

    elif parsed["set_text"] and parsed["local_id"]:
        set_filter = _build_set_name_filter(parsed["set_text"])
        safe_local_id = parsed["local_id"].replace("'", "\\'")
        filters.append(set_filter)
        filters.append(f"LOWER(local_id) = LOWER('{safe_local_id}')")

    elif parsed["local_id"]:
        safe_local_id = parsed["local_id"].replace("'", "\\'")
        filters.append(f"LOWER(local_id) = LOWER('{safe_local_id}')")

    elif parsed["name_text"]:
        safe_name = parsed["name_text"].replace("'", "\\'")
        filters.append(f"LOWER(name) LIKE LOWER('%{safe_name}%')")

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
    safe_card_id = card_id.replace("'", "\\'")

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
    safe_card_id = card_id.replace("'", "\\'")
    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

    sql = f"""
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

        cardmarket_avg AS cardmarket_avg_display_eur,
        cardmarket_low AS cardmarket_low_display_eur,
        cardmarket_trend AS cardmarket_trend_display_eur,
        cardmarket_avg_holo AS cardmarket_avg_holo_display_eur,
        cardmarket_low_holo AS cardmarket_low_holo_display_eur,
        cardmarket_trend_holo AS cardmarket_trend_holo_display_eur,
        tcgplayer_normal_market_price * {usd_to_eur} AS tcgplayer_normal_market_price_display_eur,
        tcgplayer_holofoil_market_price * {usd_to_eur} AS tcgplayer_holofoil_market_price_display_eur,
        tcgplayer_reverse_holofoil_market_price * {usd_to_eur} AS tcgplayer_reverse_holofoil_market_price_display_eur,

        cardmarket_avg * {eur_to_gbp} AS cardmarket_avg_display_gbp,
        cardmarket_low * {eur_to_gbp} AS cardmarket_low_display_gbp,
        cardmarket_trend * {eur_to_gbp} AS cardmarket_trend_display_gbp,
        cardmarket_avg_holo * {eur_to_gbp} AS cardmarket_avg_holo_display_gbp,
        cardmarket_low_holo * {eur_to_gbp} AS cardmarket_low_holo_display_gbp,
        cardmarket_trend_holo * {eur_to_gbp} AS cardmarket_trend_holo_display_gbp,
        tcgplayer_normal_market_price * {usd_to_gbp} AS tcgplayer_normal_market_price_display_gbp,
        tcgplayer_holofoil_market_price * {usd_to_gbp} AS tcgplayer_holofoil_market_price_display_gbp,
        tcgplayer_reverse_holofoil_market_price * {usd_to_gbp} AS tcgplayer_reverse_holofoil_market_price_display_gbp,

        cardmarket_avg * {eur_to_usd} AS cardmarket_avg_display_usd,
        cardmarket_low * {eur_to_usd} AS cardmarket_low_display_usd,
        cardmarket_trend * {eur_to_usd} AS cardmarket_trend_display_usd,
        cardmarket_avg_holo * {eur_to_usd} AS cardmarket_avg_holo_display_usd,
        cardmarket_low_holo * {eur_to_usd} AS cardmarket_low_holo_display_usd,
        cardmarket_trend_holo * {eur_to_usd} AS cardmarket_trend_holo_display_usd,
        tcgplayer_normal_market_price AS tcgplayer_normal_market_price_display_usd,
        tcgplayer_holofoil_market_price AS tcgplayer_holofoil_market_price_display_usd,
        tcgplayer_reverse_holofoil_market_price AS tcgplayer_reverse_holofoil_market_price_display_usd

    FROM `pokemon-pacey32-github.pokemonApp.card_price_history`
    WHERE card_id = '{safe_card_id}'
    ORDER BY snapshot_timestamp
    """
    df = run_query(sql)
    if df.empty:
        return df
    return _select_display_currency_columns(df)


@st.cache_data(ttl=300, show_spinner=False)
def get_card_latest_variant_prices(card_id: str) -> pd.DataFrame:
    safe_card_id = card_id.replace("'", "\\'")
    eur_to_gbp = get_fx_rate("EUR", "GBP")
    eur_to_usd = get_fx_rate("EUR", "USD")
    usd_to_gbp = get_fx_rate("USD", "GBP")
    usd_to_eur = get_fx_rate("USD", "EUR")

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

        cardmarket_avg AS cardmarket_avg_display_eur,
        cardmarket_low AS cardmarket_low_display_eur,
        cardmarket_trend AS cardmarket_trend_display_eur,
        cardmarket_avg_holo AS cardmarket_avg_holo_display_eur,
        cardmarket_low_holo AS cardmarket_low_holo_display_eur,
        cardmarket_trend_holo AS cardmarket_trend_holo_display_eur,
        tcgplayer_normal_market_price * {usd_to_eur} AS tcgplayer_normal_market_price_display_eur,
        tcgplayer_holofoil_market_price * {usd_to_eur} AS tcgplayer_holofoil_market_price_display_eur,
        tcgplayer_reverse_holofoil_market_price * {usd_to_eur} AS tcgplayer_reverse_holofoil_market_price_display_eur,

        cardmarket_avg * {eur_to_gbp} AS cardmarket_avg_display_gbp,
        cardmarket_low * {eur_to_gbp} AS cardmarket_low_display_gbp,
        cardmarket_trend * {eur_to_gbp} AS cardmarket_trend_display_gbp,
        cardmarket_avg_holo * {eur_to_gbp} AS cardmarket_avg_holo_display_gbp,
        cardmarket_low_holo * {eur_to_gbp} AS cardmarket_low_holo_display_gbp,
        cardmarket_trend_holo * {eur_to_gbp} AS cardmarket_trend_holo_display_gbp,
        tcgplayer_normal_market_price * {usd_to_gbp} AS tcgplayer_normal_market_price_display_gbp,
        tcgplayer_holofoil_market_price * {usd_to_gbp} AS tcgplayer_holofoil_market_price_display_gbp,
        tcgplayer_reverse_holofoil_market_price * {usd_to_gbp} AS tcgplayer_reverse_holofoil_market_price_display_gbp,

        cardmarket_avg * {eur_to_usd} AS cardmarket_avg_display_usd,
        cardmarket_low * {eur_to_usd} AS cardmarket_low_display_usd,
        cardmarket_trend * {eur_to_usd} AS cardmarket_trend_display_usd,
        cardmarket_avg_holo * {eur_to_usd} AS cardmarket_avg_holo_display_usd,
        cardmarket_low_holo * {eur_to_usd} AS cardmarket_low_holo_display_usd,
        cardmarket_trend_holo * {eur_to_usd} AS cardmarket_trend_holo_display_usd,
        tcgplayer_normal_market_price AS tcgplayer_normal_market_price_display_usd,
        tcgplayer_holofoil_market_price AS tcgplayer_holofoil_market_price_display_usd,
        tcgplayer_reverse_holofoil_market_price AS tcgplayer_reverse_holofoil_market_price_display_usd

    FROM `pokemon-pacey32-github.pokemonApp.card_price_history`
    WHERE card_id = '{safe_card_id}'
    ORDER BY snapshot_timestamp DESC
    LIMIT 1
    """
    df = run_query(sql)
    if df.empty:
        return df
    return _select_display_currency_columns(df)
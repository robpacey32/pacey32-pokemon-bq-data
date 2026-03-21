import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

from pymongo import MongoClient

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "pacey32PokemonApp"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
user_cards_col = db["user_cards"]
user_sessions_col = db["user_sessions"]

# Ensure indexes (safe to run multiple times)
users_col.create_index("username", unique=True)
user_cards_col.create_index([("user_id", 1), ("card_id", 1)], unique=True)
user_cards_col.create_index([("user_id", 1), ("owned_normal", 1)])
user_cards_col.create_index([("user_id", 1), ("owned_holo", 1)])
user_cards_col.create_index([("user_id", 1), ("owned_reverse", 1)])

# Session indexes
user_sessions_col.create_index("token_hash", unique=True)
user_sessions_col.create_index("expires_at", expireAfterSeconds=0)


def utc_now():
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user_session(username: str, days: int = 30) -> str:
    username = username.strip().lower()
    token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(token)
    now = utc_now()
    expires_at = now + timedelta(days=days)

    user_sessions_col.insert_one(
        {
            "token_hash": token_hash,
            "username": username,
            "created_at": now,
            "expires_at": expires_at,
        }
    )

    return token


def get_user_session_by_token(token: str):
    token_hash = hash_session_token(token)
    return user_sessions_col.find_one({"token_hash": token_hash})


def delete_user_session_by_token(token: str):
    token_hash = hash_session_token(token)
    user_sessions_col.delete_one({"token_hash": token_hash})


def extend_user_session(token: str, days: int = 30):
    token_hash = hash_session_token(token)
    user_sessions_col.update_one(
        {"token_hash": token_hash},
        {
            "$set": {
                "expires_at": utc_now() + timedelta(days=days),
            }
        }
    )


def get_user_card_variants(user_id: str) -> dict:
    docs = list(
        user_cards_col.find(
            {"user_id": user_id},
            {
                "_id": 0,
                "card_id": 1,
                "owned_normal": 1,
                "owned_holo": 1,
                "owned_reverse": 1,
                "owned_first_edition": 1,
                "owned_w_promo": 1,
            },
        )
    )

    out = {}
    for doc in docs:
        out[doc["card_id"]] = {
            "owned_normal": doc.get("owned_normal", False),
            "owned_holo": doc.get("owned_holo", False),
            "owned_reverse": doc.get("owned_reverse", False),
            "owned_first_edition": doc.get("owned_first_edition", False),
            "owned_w_promo": doc.get("owned_w_promo", False),
        }
    return out


def upsert_user_card_variants(user_id: str, card_id: str, variant_data: dict):
    user_cards_col.update_one(
        {"user_id": user_id, "card_id": card_id},
        {
            "$set": {
                "user_id": user_id,
                "card_id": card_id,
                "owned_normal": bool(variant_data.get("owned_normal", False)),
                "owned_holo": bool(variant_data.get("owned_holo", False)),
                "owned_reverse": bool(variant_data.get("owned_reverse", False)),
                "owned_first_edition": bool(variant_data.get("owned_first_edition", False)),
                "owned_w_promo": bool(variant_data.get("owned_w_promo", False)),
                "updated_at": utc_now(),
            }
        },
        upsert=True
    )


def get_user_cards_df(user_id: str):
    docs = list(
        user_cards_col.find(
            {"user_id": user_id},
            {"_id": 0}
        )
    )

    import pandas as pd
    return pd.DataFrame(docs)


def get_user_by_username(username: str):
    return users_col.find_one({"username": username.strip().lower()})


def update_last_login(username: str):
    users_col.update_one(
        {"username": username.strip().lower()},
        {"$set": {"last_login_at": utc_now()}}
    )


def update_user_password(username: str, password_hash: bytes):
    users_col.update_one(
        {"username": username.strip().lower()},
        {"$set": {"password_hash": password_hash}}
    )


def update_user_display_currency(username: str, display_currency: str):
    users_col.update_one(
        {"username": username.strip().lower()},
        {"$set": {"display_currency": display_currency}}
    )
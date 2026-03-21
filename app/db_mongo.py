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
email_verifications_col = db["email_verifications"]
password_resets_col = db["password_resets"]

# Ensure indexes (safe to run multiple times)
users_col.create_index("username", unique=True)
users_col.create_index("email", unique=True)

user_cards_col.create_index([("user_id", 1), ("card_id", 1)], unique=True)
user_cards_col.create_index([("user_id", 1), ("owned_normal", 1)])
user_cards_col.create_index([("user_id", 1), ("owned_holo", 1)])
user_cards_col.create_index([("user_id", 1), ("owned_reverse", 1)])

# Session indexes
user_sessions_col.create_index("token_hash", unique=True)
user_sessions_col.create_index("expires_at", expireAfterSeconds=0)

# Email verification indexes
email_verifications_col.create_index("token_hash", unique=True)
email_verifications_col.create_index("expires_at", expireAfterSeconds=0)

# Password reset indexes
password_resets_col.create_index("token_hash", unique=True)
password_resets_col.create_index("expires_at", expireAfterSeconds=0)


def utc_now():
    return datetime.now(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# -------------------------
# USER SESSIONS
# -------------------------
def create_user_session(username: str, days: int = 30) -> str:
    username = username.strip().lower()
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
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
    token_hash = hash_token(token)
    return user_sessions_col.find_one({"token_hash": token_hash})


def delete_user_session_by_token(token: str):
    token_hash = hash_token(token)
    user_sessions_col.delete_one({"token_hash": token_hash})


def extend_user_session(token: str, days: int = 30):
    token_hash = hash_token(token)
    user_sessions_col.update_one(
        {"token_hash": token_hash},
        {
            "$set": {
                "expires_at": utc_now() + timedelta(days=days),
            }
        }
    )


def delete_all_user_sessions(username: str):
    user_sessions_col.delete_many({"username": username.strip().lower()})


# -------------------------
# EMAIL VERIFICATION
# -------------------------
def get_user_by_email(email: str):
    return users_col.find_one({"email": email.strip().lower()})


def mark_user_email_verified(username: str):
    users_col.update_one(
        {"username": username.strip().lower()},
        {
            "$set": {
                "email_verified": True,
                "email_verified_at": utc_now(),
            }
        }
    )


def create_email_verification_token(username: str, email: str, hours: int = 24) -> str:
    username = username.strip().lower()
    email = email.strip().lower()
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    now = utc_now()
    expires_at = now + timedelta(hours=hours)

    email_verifications_col.insert_one(
        {
            "token_hash": token_hash,
            "username": username,
            "email": email,
            "created_at": now,
            "expires_at": expires_at,
        }
    )

    return token


def get_email_verification_by_token(token: str):
    token_hash = hash_token(token)
    return email_verifications_col.find_one({"token_hash": token_hash})


def delete_email_verification_by_token(token: str):
    token_hash = hash_token(token)
    email_verifications_col.delete_one({"token_hash": token_hash})


def delete_email_verifications_for_user(username: str):
    email_verifications_col.delete_many({"username": username.strip().lower()})


# -------------------------
# PASSWORD RESETS
# -------------------------
def create_password_reset_token(username: str, hours: int = 1) -> str:
    username = username.strip().lower()
    token = secrets.token_urlsafe(32)
    token_hash = hash_token(token)
    now = utc_now()
    expires_at = now + timedelta(hours=hours)

    password_resets_col.insert_one(
        {
            "token_hash": token_hash,
            "username": username,
            "created_at": now,
            "expires_at": expires_at,
        }
    )

    return token


def get_password_reset_by_token(token: str):
    token_hash = hash_token(token)
    return password_resets_col.find_one({"token_hash": token_hash})


def delete_password_reset_by_token(token: str):
    token_hash = hash_token(token)
    password_resets_col.delete_one({"token_hash": token_hash})


def delete_password_resets_for_user(username: str):
    password_resets_col.delete_many({"username": username.strip().lower()})


# -------------------------
# USER CARDS
# -------------------------
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


# -------------------------
# USERS
# -------------------------
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
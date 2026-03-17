import os
from pymongo import MongoClient

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "pacey32PokemonApp"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
user_cards_col = db["user_cards"]


def get_user_owned_card_ids(user_id: str) -> set:
    docs = user_cards_col.find(
        {"user_id": user_id, "owned": True},
        {"card_id": 1, "_id": 0}
    )
    return {doc["card_id"] for doc in docs}


def upsert_user_card(user_id: str, card_id: str, owned: bool):
    user_cards_col.update_one(
        {"user_id": user_id, "card_id": card_id},
        {
            "$set": {
                "user_id": user_id,
                "card_id": card_id,
                "owned": owned,
            }
        },
        upsert=True
    )

def get_user_cards_df(user_id: str):
    docs = list(user_cards_col.find(
        {"user_id": user_id},
        {"_id": 0}
    ))

    import pandas as pd
    return pd.DataFrame(docs)
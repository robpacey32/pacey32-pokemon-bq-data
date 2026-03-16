import os
from pymongo import MongoClient

MONGO_URI = os.environ["MONGO_URI"]
DB_NAME = "pacey32PokemonApp"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
user_cards_col = db["user_cards"]
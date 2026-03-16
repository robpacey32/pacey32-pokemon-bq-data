from pymongo import MongoClient

MONGO_URI = 'mongodb+srv://pacey32:Pikachu01!!@pacey32pokemonapp.xtuvqk0.mongodb.net/?appName=pacey32PokemonApp'
DB_NAME = "pacey32PokemonApp"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Create collections explicitly (optional, but tidy)
if "users" not in db.list_collection_names():
    db.create_collection("users")

if "user_cards" not in db.list_collection_names():
    db.create_collection("user_cards")

# Indexes / constraints
db.users.create_index("username", unique=True)
db.users.create_index("email", unique=True)

db.user_cards.create_index(
    [("user_id", 1), ("card_id", 1)],
    unique=True
)

print("MongoDB setup complete.")
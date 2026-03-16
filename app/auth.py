import bcrypt
from db_mongo import users_col

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def check_password(password: str, password_hash: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)

def register_user(username: str, email: str, password: str):
    existing = users_col.find_one({"$or": [{"username": username}, {"email": email}]})
    if existing:
        return False, "Username or email already exists"

    users_col.insert_one({
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
    })
    return True, "User created"

def login_user(username: str, password: str):
    user = users_col.find_one({"username": username})
    if not user:
        return None

    if check_password(password, user["password_hash"]):
        return user

    return None
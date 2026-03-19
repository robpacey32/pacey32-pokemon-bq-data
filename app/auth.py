import bcrypt
from db_mongo import users_col, update_last_login, update_user_password


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def check_password(password: str, password_hash) -> bool:
    if isinstance(password_hash, str):
        password_hash = password_hash.encode("utf-8")
    return bcrypt.checkpw(password.encode("utf-8"), password_hash)


def register_user(username: str, email: str, password: str):
    clean_username = username.strip().lower()
    clean_email = email.strip().lower()

    existing = users_col.find_one({
        "$or": [
            {"username": clean_username},
            {"email": clean_email}
        ]
    })

    if existing:
        return False, "Username or email already exists"

    users_col.insert_one({
        "username": clean_username,
        "email": clean_email,
        "password_hash": hash_password(password),
        "created_at": __import__("datetime").datetime.utcnow(),
        "last_login_at": None,
        "display_currency": "GBP",
    })

    return True, "User created successfully"


def login_user(username: str, password: str):
    clean_username = username.strip().lower()
    user = users_col.find_one({"username": clean_username})
    
    if not user:
        return None

    if check_password(password, user["password_hash"]):
        update_last_login(clean_username)
        return users_col.find_one({"username": clean_username})

    return None


def change_password(username: str, current_password: str, new_password: str):
    user = users_col.find_one({"username": username.strip().lower()})
    if not user:
        return False, "User not found"

    if not check_password(current_password, user["password_hash"]):
        return False, "Current password is incorrect"

    update_user_password(username, hash_password(new_password))
    return True, "Password updated successfully"
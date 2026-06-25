import hashlib
import os

from .db import db

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return f"{salt.hex()}${dk.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
    return dk.hex() == dk_hex

def create_user(username: str, password: str, email: str = None, is_admin: int = 0):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO user(username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), is_admin),
        )
        return cur.lastrowid

def get_user_by_name(username: str):
    with db() as conn:
        return conn.execute("SELECT * FROM user WHERE username = ?", (username,)).fetchone()

def get_user_by_email(email: str):
    with db() as conn:
        return conn.execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone()

def get_user(user_id: int):
    with db() as conn:
        return conn.execute("SELECT * FROM user WHERE id = ?", (user_id,)).fetchone()

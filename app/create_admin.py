import getpass
import re
import sys

from . import auth
from .db import init_db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def prompt_email():
    while True:
        email = input("Email: ").strip().lower()
        if not EMAIL_RE.match(email):
            print("That doesn't look like a valid email. Try again.")
            continue
        existing = auth.get_user_by_email(email)
        if existing:
            print(f"That email already belongs to {existing['username']}.")
            continue
        return email


def prompt_username():
    while True:
        username = input("Username: ").strip()
        if len(username) < 3:
            print("Username must be at least 3 characters.")
            continue
        if auth.get_user_by_name(username):
            print(f"The username {username} is taken. Pick another.")
            continue
        return username


def prompt_password():
    while True:
        pw = getpass.getpass("Password: ")
        if len(pw) < 6:
            print("Password must be at least 6 characters.")
            continue
        if pw != getpass.getpass("Confirm password: "):
            print("The passwords didn't match. Try again.")
            continue
        return pw


def main():
    init_db()
    print("Let's create an admin user.")
    email = prompt_email()
    username = prompt_username()
    password = prompt_password()
    auth.create_user(username, password, email=email, is_admin=1)
    print(f"\nAdmin user {username} created. Log in with it and you'll see the Admin panel.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(1)

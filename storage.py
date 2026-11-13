"""Accounts and saved profiles for FIRESight.

Two interchangeable backends:

* ``LocalStore`` (default) keeps users in a JSON file under ``.firesight/``.
  No setup, good for running the app on your own machine.
* ``DynamoStore`` keeps users in an AWS DynamoDB table. It is selected when
  ``FIRESIGHT_BACKEND=dynamodb`` is set, or automatically when
  ``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` are present in the
  environment or ``st.secrets``.

Demo profiles from ``examples/`` work with either backend. A demo session's
edits live only in that browser session and never touch the store.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXAMPLES_DIR = ROOT / "examples"
DEMO_PREFIX = "demo:"
PBKDF2_ITERATIONS = 240_000


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str, salt: str | None = None) -> str:
    """Salted PBKDF2-SHA256, stored as ``pbkdf2_sha256$iterations$salt$hash``."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        _, iterations, salt, expected = stored.split("$", 3)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
        return hmac.compare_digest(digest.hex(), expected)
    # Accounts created by the first version of the app used unsalted SHA-256.
    return hmac.compare_digest(hashlib.sha256(password.encode()).hexdigest(), stored)


# ---------------------------------------------------------------------------
# Demo profiles
# ---------------------------------------------------------------------------
def list_example_profiles() -> dict[str, dict]:
    """Return ``{slug: {"title": ..., "summary": ..., "profile": {...}}}`` for every example."""
    examples = {}
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        examples[path.stem] = data
    return examples


def load_example_profile(slug: str) -> dict:
    return json.loads((EXAMPLES_DIR / f"{slug}.json").read_text())["profile"]


def is_demo(user_id: str | None) -> bool:
    return bool(user_id) and user_id.startswith(DEMO_PREFIX)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class LocalStore:
    """Users in a single JSON file. Fine for one machine; not meant for many writers."""

    _lock = threading.Lock()

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or os.environ.get("FIRESIGHT_DATA", ROOT / ".firesight" / "users.json"))

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write(self, users: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(users, indent=2))
        tmp.replace(self.path)

    def find_by_email(self, email: str) -> dict | None:
        email = email.strip().lower()
        return next((u for u in self._read().values() if u["email"] == email), None)

    def create_user(self, email: str, password: str, profile: dict | None = None) -> str:
        with self._lock:
            users = self._read()
            user_id = str(uuid.uuid4())
            users[user_id] = {
                "userid": user_id,
                "email": email.strip().lower(),
                "password": hash_password(password),
                "profile": json.dumps(profile or {}),
            }
            self._write(users)
        return user_id

    def get_profile_json(self, user_id: str) -> str | None:
        user = self._read().get(user_id)
        return user["profile"] if user else None

    def put_profile_json(self, user_id: str, profile_json: str) -> None:
        with self._lock:
            users = self._read()
            users[user_id]["profile"] = profile_json
            self._write(users)


class DynamoStore:
    """Users in a DynamoDB table keyed by ``userid`` with an ``email-index`` GSI."""

    def __init__(self, table_name: str, region: str, credentials: dict | None = None):
        import boto3
        from boto3.dynamodb.conditions import Key

        self._key = Key
        resource = boto3.resource("dynamodb", region_name=region, **(credentials or {}))
        self.table = resource.Table(table_name)

    def find_by_email(self, email: str) -> dict | None:
        response = self.table.query(
            IndexName="email-index",
            KeyConditionExpression=self._key("email").eq(email.strip().lower()),
        )
        items = response.get("Items", [])
        return items[0] if items else None

    def create_user(self, email: str, password: str, profile: dict | None = None) -> str:
        user_id = str(uuid.uuid4())
        self.table.put_item(Item={
            "userid": user_id,
            "email": email.strip().lower(),
            "password": hash_password(password),
            "subscription_status": True,
            "profile": json.dumps(profile or {}),
        })
        return user_id

    def get_profile_json(self, user_id: str) -> str | None:
        return self.table.get_item(Key={"userid": user_id}).get("Item", {}).get("profile")

    def put_profile_json(self, user_id: str, profile_json: str) -> None:
        self.table.update_item(
            Key={"userid": user_id},
            UpdateExpression="SET profile = :val1",
            ExpressionAttributeValues={":val1": profile_json},
        )


# ---------------------------------------------------------------------------
# Streamlit-facing helpers
# ---------------------------------------------------------------------------
def _setting(name: str, default: str | None = None) -> str | None:
    if name in os.environ:
        return os.environ[name]
    try:
        import streamlit as st
        return st.secrets.get(name, default)
    except Exception:
        return default


_store = None


def get_store():
    """The configured backend (created once per process)."""
    global _store
    if _store is None:
        key_id, secret = _setting("AWS_ACCESS_KEY_ID"), _setting("AWS_SECRET_ACCESS_KEY")
        backend = _setting("FIRESIGHT_BACKEND") or ("dynamodb" if key_id and secret else "local")
        if backend.lower() == "dynamodb":
            creds = {}
            if key_id and secret:
                creds = {"aws_access_key_id": key_id, "aws_secret_access_key": secret}
            _store = DynamoStore(
                table_name=_setting("FIRESIGHT_TABLE", "firesight-users"),
                region=_setting("FIRESIGHT_AWS_REGION", "us-east-2"),
                credentials=creds,
            )
        else:
            _store = LocalStore()
    return _store


def signup_code() -> str | None:
    """Optional invite code required to create an account (``FIRESIGHT_SIGNUP_CODE``)."""
    return _setting("FIRESIGHT_SIGNUP_CODE")


def authenticate(email: str, password: str) -> str | None:
    user = get_store().find_by_email(email)
    if user and verify_password(password, user["password"]):
        return user["userid"]
    return None


def register(email: str, password: str) -> str:
    store = get_store()
    if store.find_by_email(email):
        raise ValueError("An account with that email already exists.")
    return store.create_user(email, password)


def start_demo(slug: str) -> str:
    """Log the current session into a demo profile and return its user id."""
    import streamlit as st

    user_id = f"{DEMO_PREFIX}{slug}"
    st.session_state[f"profile:{user_id}"] = load_example_profile(slug)
    st.session_state["user_id"] = user_id
    st.session_state["logged_in"] = True
    return user_id


def load_user_profile(user_id: str | None) -> dict | None:
    if not user_id:
        return None
    if is_demo(user_id):
        import streamlit as st

        key = f"profile:{user_id}"
        if key not in st.session_state:
            st.session_state[key] = load_example_profile(user_id[len(DEMO_PREFIX):])
        return json.loads(json.dumps(st.session_state[key]))  # hand out a copy
    profile_json = get_store().get_profile_json(user_id)
    return json.loads(profile_json) if profile_json else None


def save_user_profile(user_id: str, user_data: dict) -> None:
    profile_json = json.dumps(user_data, indent=4, default=str)
    if is_demo(user_id):
        import streamlit as st

        st.session_state[f"profile:{user_id}"] = json.loads(profile_json)
        return
    get_store().put_profile_json(user_id, profile_json)

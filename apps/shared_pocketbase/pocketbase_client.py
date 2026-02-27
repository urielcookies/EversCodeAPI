import os
import json
import time
import base64
from dotenv import load_dotenv
from pocketbase import PocketBase
from pocketbase.utils import ClientResponseError

load_dotenv()

POCKETBASE_API = os.getenv("POCKETBASE_API")
POCKETBASE_SUPERUSER_EMAIL = os.getenv("POCKETBASE_SUPERUSER_EMAIL")
POCKETBASE_SUPERUSER_PASSWORD = os.getenv("POCKETBASE_SUPERUSER_PASSWORD")

TOKEN_FILE = os.path.join(os.path.dirname(__file__), '..', '..', '.pb_token')

_pb_client_instance = PocketBase(POCKETBASE_API)


def _is_token_valid(token):
    """Decode JWT payload and check exp claim with a 60s buffer. No network call."""
    try:
        payload_part = token.split('.')[1]
        # JWT base64 padding
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += '=' * padding
        payload = json.loads(base64.b64decode(payload_part))
        exp = payload.get('exp', 0)
        return time.time() < (exp - 60)
    except Exception:
        return False


def _save_token(token):
    """Persist auth token to file."""
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
    except Exception as e:
        print(f"PocketBase Client: Failed to save token to file: {e}")


def _load_token():
    """Load auth token from file, returns None if file missing or empty."""
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip() or None
    except Exception as e:
        print(f"PocketBase Client: Failed to load token from file: {e}")
    return None


def get_pocketbase_client():
    global _pb_client_instance

    # 1. In-memory token still valid (same process, not yet expired)
    current_token = _pb_client_instance.auth_store.token
    if current_token and _is_token_valid(current_token):
        return _pb_client_instance

    # 2. Try restoring a cached token from file (survives hot-reloads)
    cached_token = _load_token()
    if cached_token and _is_token_valid(cached_token):
        print("PocketBase Client: Restored valid token from cache file.")
        _pb_client_instance.auth_store.save(cached_token, None)
        return _pb_client_instance

    # 3. No valid token anywhere — full re-authentication
    print("PocketBase Client: No valid token found. Authenticating...")
    try:
        _pb_client_instance.admins.auth_with_password(POCKETBASE_SUPERUSER_EMAIL, POCKETBASE_SUPERUSER_PASSWORD)
        _save_token(_pb_client_instance.auth_store.token)
        print("PocketBase Client: Authentication successful. Token cached to file.")
    except ClientResponseError as e:
        error_message = getattr(e, 'message', str(e))
        error_data = getattr(e, 'data', {})
        print(f"PocketBase Client: Authentication failed: Status {e.status}, Message: {error_message}, Data: {error_data}")
        raise
    except Exception as e:
        print(f"PocketBase Client: Unexpected error during authentication: {e}")
        raise

    return _pb_client_instance

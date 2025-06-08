import os
from dotenv import load_dotenv
from pocketbase import PocketBase
from pocketbase.utils import ClientResponseError

load_dotenv()

POCKETBASE_API = os.getenv("POCKETBASE_API")
POCKETBASE_SUPERUSER_EMAIL = os.getenv("POCKETBASE_SUPERUSER_EMAIL")
POCKETBASE_SUPERUSER_PASSWORD = os.getenv("POCKETBASE_SUPERUSER_PASSWORD")
COLLECTION_ID_SUPERUSERS = os.getenv("COLLECTION_ID_SUPERUSERS")

# Global client instance
pb_client = PocketBase(POCKETBASE_API)

def get_pocketbase_client():
    pb_client = PocketBase(os.getenv("POCKETBASE_API"))

    # Check if authenticated, fallback on token presence
    is_authenticated = False
    if hasattr(pb_client.auth_store, "is_valid"):
        is_authenticated = pb_client.auth_store.is_valid
    elif hasattr(pb_client.auth_store, "token"):
        is_authenticated = bool(pb_client.auth_store.token)

    if not is_authenticated:
        # perform login or raise error
        email = os.getenv("POCKETBASE_SUPERUSER_EMAIL")
        password = os.getenv("POCKETBASE_SUPERUSER_PASSWORD")
        pb_client.admins.auth_with_password(email, password)

    return pb_client

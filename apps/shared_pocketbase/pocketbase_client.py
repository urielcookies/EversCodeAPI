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
    if not pb_client.auth_store.is_valid:
        try:
            pb_client.collection(COLLECTION_ID_SUPERUSERS).auth_with_password(
                POCKETBASE_SUPERUSER_EMAIL,
                POCKETBASE_SUPERUSER_PASSWORD
            )
        except ClientResponseError as e:
            print(f"PocketBase auth failed: {e}")
            raise
    return pb_client

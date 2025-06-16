import os
from dotenv import load_dotenv
from pocketbase import PocketBase
from pocketbase.utils import ClientResponseError

load_dotenv()

POCKETBASE_API = os.getenv("POCKETBASE_API")
POCKETBASE_SUPERUSER_EMAIL = os.getenv("POCKETBASE_SUPERUSER_EMAIL")
POCKETBASE_SUPERUSER_PASSWORD = os.getenv("POCKETBASE_SUPERUSER_PASSWORD")

_pb_client_instance = PocketBase(POCKETBASE_API)

def get_pocketbase_client():
    global _pb_client_instance

    if not _pb_client_instance.auth_store.token:
        print("PocketBase Client: No token found. Attempting admin authentication...")
        try:
            _pb_client_instance.admins.auth_with_password(POCKETBASE_SUPERUSER_EMAIL, POCKETBASE_SUPERUSER_PASSWORD)
            print("PocketBase Client: Admin authentication successful.")
        except ClientResponseError as e:
            error_message = getattr(e, 'message', str(e))
            error_data = getattr(e, 'data', {})
            print(f"PocketBase Client: Admin authentication failed: Status {e.status}, Message: {error_message}, Data: {error_data}")
            raise
        except Exception as e:
            print(f"PocketBase Client: Unexpected error during admin authentication: {e}")
            raise
    else:
        print("PocketBase Client: Token found. Assuming client is authenticated.")

    return _pb_client_instance
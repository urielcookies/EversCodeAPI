import os # Keep if used for general purposes, e.g., os.getenv (though not directly in routes here)
import requests 
from apps.EversPass import everspass_bp
from apps.shared_pocketbase.pocketbase_client import get_pocketbase_client
from datetime import datetime, timedelta
from flask import request, jsonify
from pocketbase.utils import ClientResponseError
from datetime import datetime, timezone

# Initialize the PocketBase client globally. This handles SDK authentication.
pb_client = get_pocketbase_client()

@everspass_bp.route('/create-session', methods=['POST'])
def createSession():
    data = request.get_json()
    device_id = data.get('device_id')
    session_name = data.get('name')

    if not device_id or not session_name:
        return jsonify({"error": "Missing device_id or name"}), 400

    try:
        record = pb_client.collection("everspass_sessions").create({
            "device_id": device_id,
            "name": session_name,
            "expires_at": (datetime.utcnow() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S.%fZ'),
            "total_photos_bytes": 0
        })

        record_data = {
            'id': record.id,
            'created': record.created,
            'updated': record.updated,
            'device_id': record.device_id,
            'name': record.name,
            'expires_at': record.expires_at,
            'total_photos_bytes': record.total_photos_bytes
        }

        return jsonify(record_data)

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/load-session', methods=['GET'])
def loadSession():
    """
    Loads sessions for a given device_id.
    The device_id is expected as a URL query parameter.
    Example: GET /load-session?deviceId=some-unique-device-id
    """
    device_id = request.args.get('deviceId')

    if not device_id:
        return jsonify({"error": "The 'deviceId' query parameter is required."}), 400

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    try:
        records = pb_client.collection("everspass_sessions").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": f'device_id = "{device_id}"'
            }
        )

        sessions_data = []
        # Get current time in UTC, timezone-aware
        current_time_utc = datetime.now(timezone.utc)

        for record in records.items:
            expires_at_dt = record.expires_at
            if isinstance(expires_at_dt, str):
                expires_at_dt = datetime.fromisoformat(expires_at_dt)

            # Ensure expires_at_dt is also timezone-aware UTC for correct comparison
            if expires_at_dt.tzinfo is None:
                # If parsed as naive, assume UTC if that's its true meaning
                # (Common for databases if no explicit tz is stored/retrieved)
                expires_at_dt = expires_at_dt.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC if it's already aware but in a different timezone
                expires_at_dt = expires_at_dt.astimezone(timezone.utc)


            # Both are timezone-aware UTC and can be safely compared
            if expires_at_dt > current_time_utc:
                sessions_data.append({
                    'id': record.id,
                    'created': record.created,
                    'updated': record.updated,
                    'device_id': record.device_id,
                    'name': record.name,
                    'expires_at': record.expires_at,
                    'total_photos_bytes': record.total_photos_bytes,
                    'total_photos': record.total_photos
                })

        # return jsonify(sessions_data)
        return jsonify({
            "page": records.page,
            "per_page": records.per_page,
            "total_pages": records.total_pages,
            "total_items": records.total_items,
            "items": sessions_data
        })

    except ClientResponseError as e:
        print(f"PocketBase error: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/delete-session/<session_id>', methods=['DELETE'])
def deleteSession(session_id):
    """
    Deletes a specific session by its ID and all related photos.
    The session_id is expected as part of the URL path.
    Example: DELETE /delete-session/a1b2c3d4e5f6g7h
    """
    if not session_id:
        return jsonify({"error": "Session ID is required."}), 400

    try:
        # 1. Delete associated everspass_photos
        # Find all photos related to this session_id
        # Assuming 'session_id' is the field in 'everspass_photos' that links to 'everspass_sessions'
        photos_to_delete = pb_client.collection("everspass_photos").get_full_list(
            query_params={"filter": f'session_id = "{session_id}"'}
        )

        deleted_photos_count = 0
        for photo in photos_to_delete:
            try:
                pb_client.collection("everspass_photos").delete(photo.id)
                deleted_photos_count += 1
            except ClientResponseError as e:
                # Log or handle individual photo deletion errors if necessary
                print(f"Error deleting photo {photo.id}: {e}")
                # Decide whether to continue deleting other photos or stop

        # 2. Delete the everspass_sessions record
        pb_client.collection("everspass_sessions").delete(session_id)

        return jsonify({
            "message": f"Session with ID '{session_id}' and {deleted_photos_count} associated photo(s) deleted successfully."
        }), 200

    except ClientResponseError as e:
        if e.status == 404:
            return jsonify({"error": "Session not found."}), 404
        print(f"PocketBase error: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/check-deviceid-exists/<device_id>', methods=['GET'])
def checkSessionExists(device_id):
    """
    Checks if any sessions exist for a given device_id.
    Example: GET /sessions-exist-for-device/some-unique-device-id
    """
    if not device_id:
        return jsonify({"error": "Device ID is required."}), 400

    try:
        result = pb_client.collection("everspass_sessions").get_list(
            page=1,
            per_page=1,
            query_params={
                "filter": f'device_id = "{device_id}"'
            }
        )

        if result.total_items > 0:
            return jsonify({"exists": True, "device_id": device_id}), 200
        else:
            return jsonify({"exists": False, "device_id": device_id}), 200

    except ClientResponseError as e:
        print(f"PocketBase error: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/find-session/<session_id>', methods=['GET'])
def findSession(session_id):
    if not session_id:
        return jsonify({"error": "Session ID is required."}), 400
    try:
        record = pb_client.collection("everspass_sessions").get_one(session_id)

        if record:
            # Manually create a dict from the record fields
            session_data = {
                "id": record.id,
                "name": record.name,
                "device_id": record.device_id,
                "expires_at": record.expires_at,
                "total_photos": record.total_photos,
                "total_photos_bytes": record.total_photos_bytes,
                "created": record.created,
                "updated": record.updated,
                # add any other fields you want to return here
            }

            return jsonify({
                "exists": True,
                "record": session_data
            }), 200
        else:
            return jsonify({"exists": False, "session_id": session_id}), 200

    except ClientResponseError as e:
        if e.status == 404:
            return jsonify({"exists": False, "session_id": session_id}), 200
        return jsonify({"error": str(e), "status": e.status}), e.status

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/check-photosession-exists/<session_id>', methods=['GET'])
def checkPhotosForSession(session_id):
    """
    Checks if any photos exist for a given session_id in the 'everspass_photos' collection.
    Example: GET /check-photosession-exists/some-unique-session-id
    """
    if not session_id:
        return jsonify({"error": "Session ID is required."}), 400

    try:
        result = pb_client.collection("everspass_photos").get_list(
            page=1,
            per_page=1,
            query_params={
                "filter": f'session_id = "{session_id}"'
            }
        )

        if result.total_items > 0:
            return jsonify({"exists": True, "session_id": session_id}), 200
        else:
            return jsonify({"exists": False, "session_id": session_id}), 200

    except ClientResponseError as e:
        print(f"PocketBase error: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/photosession/<session_id>/photos', methods=['GET'])
def get_session_photos(session_id):
    """
    Loads all photos associated with a specific session ID.
    Supports pagination via query parameters.
    Also retrieves the total_photos_bytes across ALL sessions for the
    device associated with the given session_id.
    Example: GET /sessions/a1b2c3d4/photos?page=1&perPage=50
    """
    if not session_id:
        return jsonify({"error": "The 'session_id' parameter is required."}), 400

    device_id = None
    total_size_across_all_device_sessions = 0

    try:
        # Step 1: Fetch the specific session record to get its device_id
        current_session_record = pb_client.collection("everspass_sessions").get_one(session_id)
        device_id = current_session_record.device_id
        
        # Step 2: Now, fetch ALL sessions belonging to this device_id
        # Use get_full_list to ensure all matching sessions are retrieved,
        # regardless of default pagination, for accurate summation.
        all_device_sessions = pb_client.collection("everspass_sessions").get_full_list(
            query_params={"filter": f'device_id = "{device_id}"'}
        )

        # Step 3: Sum the total_photos_bytes for all sessions found for this device
        for session in all_device_sessions:
            session_size = getattr(session, 'total_photos_bytes', 0)
            total_size_across_all_device_sessions += session_size

    except ClientResponseError as e:
        if e.status == 404:
            # If the initial session_id is not found, or no sessions for device
            return jsonify({"error": "Session or associated device not found."}), 404
        print(f"PocketBase error while fetching session details or device sessions: {e}")
        return jsonify({"error": "Failed to retrieve session/device details for total size."}), 500
    except Exception as e:
        print(f"An unexpected error occurred while processing device total size: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

    # --- End of cross-session total size calculation ---

    try:
        # Get pagination parameters for photos from the request
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('perPage', 50, type=int)

        # Query the 'everspass_photos' collection for photos of the *specific* session
        photo_records = pb_client.collection("everspass_photos").get_list(
            page=page,
            per_page=per_page,
            query_params={
                "filter": f'session_id = "{session_id}"',
                "sort": "-created" # Sort by newest first
            }
        )
        
        # Serialize the photo data, creating a full URL for each photo
        photos_data = []
        session_size = 0
        for record in photo_records.items:
            file_url = pb_client.get_file_url(record, record.image_url)
            session_size += record.size

            photos_data.append({
                'id': record.id,
                'image_url': file_url,
                'likes': record.likes,
                'created': record.created,
                'session_id': record.session_id,
                'originalFilename': record.original_filename,
                'size': record.size
            })

        return jsonify({
            "page": photo_records.page,
            "perPage": photo_records.per_page,
            "totalPages": photo_records.total_pages,
            "totalItems": photo_records.total_items,
            "items": photos_data,
            "sessionSize": session_size,
            "totalDeviceSessionsSize": total_size_across_all_device_sessions,
            "deviceId": device_id
        })

    except ClientResponseError as e:
        if e.status == 404:
            return jsonify({"error": "No photos found for this session."}), 200 # Or 404 if "no photos" means "not found"
        print(f"PocketBase error while fetching photos: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred while fetching photos: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

# This route handles uploading photos, creating a new record for EACH file.
@everspass_bp.route('/upload-photos/<session_id>', methods=['POST'])
def upload_photos_to_session(session_id):
    uploaded_files = request.files.getlist('image')
    valid_files = [file for file in uploaded_files if file.filename]

    if not session_id:
        return jsonify({"error": "session Id is required."}), 400

    if not valid_files:
        return jsonify({"error": "No valid image files provided."}), 400

    successful_uploads = []
    failed_uploads = []
    skipped_uploads = []
    
    # Get the admin token once for the entire batch
    # This token is managed by the get_pocketbase_client() function.
    admin_token = pb_client.auth_store.token
    if not admin_token:
        try:
            pb_client.admins.auth_with_password(
                os.getenv("POCKETBASE_SUPERUSER_EMAIL"),
                os.getenv("POCKETBASE_SUPERUSER_PASSWORD")
            )
            admin_token = pb_client.auth_store.token
            if not admin_token:
                raise Exception("Failed to obtain admin token for file upload batch.")
        except Exception as e:
            return jsonify({"error": f"Authentication failed for upload batch: {str(e)}"}), 500


    # Process each file individually to create a new record per file
    for i, file in enumerate(valid_files):
        filename = file.filename

        # Get file size in bytes
        file.stream.seek(0, os.SEEK_END)
        file_size_bytes = file.stream.tell()
        file.stream.seek(0)  # Reset stream for upload

        file_size_kb = round(file_size_bytes / 1024, 2)
        file_size_mb = round(file_size_kb / 1024, 2)
        file_size_gb = round(file_size_mb / 1024, 2)

        try:
            existing_records = pb_client.collection("everspass_photos").get_list(
                page=1,
                per_page=1,
                query_params={
                    "filter": f'session_id = "{session_id}" && originalFilename = "{filename}"'
                }
            )

            if existing_records.total_items > 0:
                skipped_uploads.append({
                    "filename": filename,
                    "reason": "File already exists for this session.",
                    "record_id": existing_records.items[0].id
                })
                print(f"Flask: Skipped '{filename}' - already exists (ID: {existing_records.items[0].id})")
                continue

            upload_data = {
                'session_id': session_id,
                'originalFilename': filename,
                'size': file_size_bytes
            }

            upload_files_current = [('image_url', (file.filename, file.stream, file.content_type))]

            pb_upload_url = f"{os.getenv('POCKETBASE_API')}/api/collections/everspass_photos/records"
            response = requests.post(
                pb_upload_url,
                data=upload_data,
                files=upload_files_current,
                headers={'Authorization': f'Bearer {admin_token}'},
                timeout=60
            )
            response.raise_for_status()
            response_json = response.json()

            successful_uploads.append({
                "filename": filename,
                "record_id": response_json.get("id"),
                "record_data": response_json,
                "size": {
                    "bytes": file_size_bytes,
                    "kilobytes": file_size_kb,
                    "megabytes": file_size_mb,
                    "gigabytes": file_size_gb
                }
            })

            # --- DENORMALIZATION STEP: ADD SIZE TO SESSION ---
            update_session_photo_stats(session_id, file_size_bytes, 1)
            # --- END DENORMALIZATION STEP ---

        except requests.exceptions.HTTPError as errh:
            error_details = {}
            try:
                error_details = errh.response.json()
            except:
                error_details = errh.response.text
            failed_uploads.append({
                "filename": filename,
                "error": f"HTTP Error: {errh}",
                "details": error_details,
                "status_code": errh.response.status if hasattr(errh.response, 'status') else None
            })
            # Decide whether to continue on error or break. For now, continue to process other files.
            continue
        except requests.exceptions.RequestException as err:
            failed_uploads.append({
                "filename": filename,
                "error": f"Request Error: {err}",
                "details": str(err)
            })
            print(f"Flask: FAILED to upload '{filename}': {err}")
            continue
        except Exception as e:
            failed_uploads.append({
                "filename": filename,
                "error": f"Unexpected Error: {str(e)}",
                "details": str(e)
            })
            print(f"Flask: FAILED to upload '{filename}': {e}")
            continue
            
    response_payload = {
        "message": "",
        "total_files_processed": len(valid_files),
        "successful_uploads_count": len(successful_uploads),
        "successful_uploads": successful_uploads,
        "failed_uploads_count": len(failed_uploads),
        "failed_uploads": failed_uploads,
        "skipped_uploads_count": len(skipped_uploads), # NEW: count of skipped files
        "skipped_uploads": skipped_uploads # NEW: list of skipped files
    }

    if not successful_uploads and not failed_uploads and skipped_uploads:
        response_payload["message"] = "All files already existed and were skipped."
        return jsonify(response_payload), 200 # OK for all skipped
    elif not successful_uploads and failed_uploads:
        response_payload["message"] = "All *attempted* file uploads failed." # More specific for failed attempts
        return jsonify(response_payload), 500 # Return 500 if all attempted uploads failed
    elif failed_uploads or skipped_uploads:
        response_payload["message"] = f"Batch upload completed with {len(successful_uploads)} successful, {len(failed_uploads)} failed, and {len(skipped_uploads)} skipped files."
        return jsonify(response_payload), 207 # Multi-Status for mixed results
    else:
        response_payload["message"] = f"All {len(successful_uploads)} files uploaded successfully."
        return jsonify(response_payload), 201 # Created for all successful

@everspass_bp.route('/delete-photo/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """
    Deletes a specific photo record from the 'everspass_photos' collection by its ID.
    Example: DELETE /delete-photo/some_photo_id
    """
    if not photo_id:
        return jsonify({"error": "Photo ID is required."}), 400

    try:
        # --- DENORMALIZATION STEP: GET PHOTO INFO BEFORE DELETION ---
        # Fetch the photo record BEFORE deleting it to get its size and session_id
        photo_to_delete = pb_client.collection("everspass_photos").get_one(photo_id)
        photo_size_to_subtract = getattr(photo_to_delete, 'size', 0)
        session_id_to_update = getattr(photo_to_delete, 'session_id', None)
        # --- END DENORMALIZATION STEP ---

        # Use the pb_client instance to delete the record
        pb_client.collection("everspass_photos").delete(photo_id)
        
        # --- DENORMALIZATION STEP: SUBTRACT SIZE FROM SESSION ---
        if session_id_to_update: # Only update if we successfully got a session_id
            update_session_photo_stats(session_id_to_update, -photo_size_to_subtract, -1)
        # --- END DENORMALIZATION STEP ---

        return jsonify({
            "message": f"Photo with ID '{photo_id}' deleted successfully."
        }), 200

    except ClientResponseError as e:
        if e.status == 404:
            print(f"Flask: Photo not found for ID: {photo_id}")
            return jsonify({"error": "Photo not found."}), 404
        print(f"Flask: PocketBase error deleting photo: {e}")
        error_msg = getattr(e, 'message', str(e))
        error_data = getattr(e, 'data', {})
        return jsonify({"error": error_msg, "details": error_data}), e.status
    except Exception as e:
        print(f"Flask: An unexpected error occurred while deleting photo: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@everspass_bp.route('/toggle-like/<photo_id>', methods=['POST'])
def toggle_like(photo_id):
    """
    Toggles the like count for a specific photo.
    Expects a JSON body with 'action': "like" or "unlike".
    Example: POST /toggle-like/photo123
    Body: {"action": "like"} or {"action": "unlike"}
    """
    if not photo_id:
        return jsonify({"error": "Photo ID is required."}), 400

    data = request.get_json()
    action = data.get('action') # Expects "like" or "unlike"

    if action not in ["like", "unlike"]:
        return jsonify({"error": "Action must be 'like' or 'unlike'."}), 400

    try:
        # 1. Fetch the current photo record
        # PocketBase SDK's get_one returns a Record object.
        # Access its data using .collection_data or treat it like an object attribute.
        photo_record_obj = pb_client.collection("everspass_photos").get_one(photo_id)

        # Access the 'likes' attribute directly. If it might not exist, use getattr.
        # PocketBase number fields usually default to 0, but safety check is good.
        current_likes_count = getattr(photo_record_obj, 'likes', 0)

        # Ensure current_likes_count is an integer (PocketBase should ensure this if field is 'number')
        if not isinstance(current_likes_count, int):
            current_likes_count = 0 # Default to 0 if type is unexpectedly wrong

        new_likes_count = current_likes_count
        message = ""

        if action == "like":
            new_likes_count += 1
            message = "Photo liked successfully."
        elif action == "unlike":
            # Prevent likes from going below zero
            new_likes_count = max(0, new_likes_count - 1)
            message = "Photo unliked successfully."

        # 2. Update the photo record with the new likes count
        # When updating, you pass a dictionary for the data.
        pb_client.collection("everspass_photos").update(photo_id, {"likes": new_likes_count})

        # 3. Return the updated likes count
        return jsonify({
            "message": message,
            "action": action,
            "photo_id": photo_id,
            "new_likes_count": new_likes_count,
        }), 200

    except ClientResponseError as e:
        if e.status == 404:
            print(f"Flask: Photo not found for ID: {photo_id}")
            return jsonify({"error": "Photo not found."}), 404
        print(f"Flask: PocketBase error toggling like count: {e}")
        error_msg = getattr(e, 'message', str(e))
        error_data = getattr(e, 'data', {})
        return jsonify({"error": error_msg, "details": error_data}), e.status
    except Exception as e:
        print(f"Flask: An unexpected error occurred while toggling like count: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

def update_session_photo_stats(session_id: str, size_change: int, photo_count_change: int = 0):
    """
    Updates the 'total_photos_bytes' and 'total_photos' fields for a specific session.
    This function is intended to be called by PocketBase hooks
    (e.g., on photo creation, update, or deletion) to maintain
    data consistency.

    Args:
        session_id (str): The ID of the session to update.
        size_change (int): The amount to add to or subtract from the
                           session's total_photos_bytes.
                           (e.g., photo_size for add, -photo_size for delete).
        photo_count_change (int): The amount to increment/decrement total_photos.
                                  Use +1 for add, -1 for delete. Default is 0.
    """
    if not session_id:
        print("Warning: update_session_photo_stats called without a session_id.")
        return

    try:
        # Fetch the current session record
        session_record = pb_client.collection("everspass_sessions").get_one(session_id)

        # Get the current totals (default to 0 if not present or invalid)
        current_total_size = getattr(session_record, 'total_photos_bytes', 0)
        current_total_photos = getattr(session_record, 'total_photos', 0)

        if not isinstance(current_total_size, (int, float)):
            current_total_size = 0
        if not isinstance(current_total_photos, int):
            current_total_photos = 0

        # Calculate new values, ensuring no negatives
        new_total_size = max(0, current_total_size + size_change)
        new_total_photos = max(0, current_total_photos + photo_count_change)

        # Update the session record
        pb_client.collection("everspass_sessions").update(
            session_id,
            {
                "total_photos_bytes": new_total_size,
                "total_photos": new_total_photos
            }
        )
        print(f"Successfully updated session {session_id} - size: {new_total_size}, count: {new_total_photos}")

    except ClientResponseError as e:
        if e.status == 404:
            print(f"Error: Session {session_id} not found. Details: {e}")
        else:
            print(f"PocketBase ClientResponseError: Status {e.status}, Message: {e.message}, Data: {e.data}")
    except Exception as e:
        print(f"Unexpected error updating session {session_id}: {e}")

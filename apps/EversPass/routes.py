from apps.EversPass import everspass_bp
from apps.shared_pocketbase.pocketbase_client import get_pocketbase_client
from datetime import datetime, timedelta
from flask import request, jsonify
from pocketbase.utils import ClientResponseError


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
            "status": "active",
        })

        record_data = {
            'id': record.id,
            'created': record.created,
            'updated': record.updated,
            'device_id': record.device_id,
            'name': record.name,
            'expires_at': record.expires_at,
            'status': record.status,
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

    try:
        records = pb_client.collection("everspass_sessions").get_list(
            page=1,
            per_page=10,
            query_params={
                "filter": f'device_id = "{device_id}"'
            }
        )

        # The result from get_list is a ListResult object which contains items
        # We need to serialize each Record object in the items list
        sessions_data = []
        for record in records.items:
            sessions_data.append({
                'id': record.id,
                'created': record.created,
                'updated': record.updated,
                'device_id': record.device_id,
                'name': record.name,
                'expires_at': record.expires_at,
                'status': record.status,
            })

        return jsonify(sessions_data)

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

@everspass_bp.route('/sessions/<session_id>/photos', methods=['GET'])
def get_session_photos(session_id):
    """
    Loads all photos associated with a specific session ID.
    Supports pagination via query parameters.
    Example: GET /sessions/a1b2c3d4/photos?page=1&perPage=50
    """
    if not session_id:
        return jsonify({"error": "The 'session_id' parameter is required."}), 400

    try:
        # Get pagination parameters from the request, with sane defaults
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('perPage', 50, type=int)

        # Query the 'everspass_photos' collection
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
        for record in photo_records.items:
            file_url = pb_client.get_file_url(record, record.image_url)
            photos_data.append({
                'id': record.id,
                'url': file_url,
                'created': record.created,
                'session_id': record.session_id
            })

        # Return the list of photos and pagination details
        return jsonify({
            "page": photo_records.page,
            "perPage": photo_records.per_page,
            "totalPages": photo_records.total_pages,
            "totalItems": photo_records.total_items,
            "items": photos_data
        })

    except ClientResponseError as e:
        if e.status == 404:
            return jsonify({"error": "Session or photos not found."}), 404
        print(f"PocketBase error: {e}")
        return jsonify({"error": str(e), "status": e.status}), e.status
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500
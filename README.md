# EversAPIs

A modular Flask backend powering multiple personal projects. Each app is isolated as a Blueprint and deployed as a single service on Railway.

## Apps

### EversVozAPI
Language learning API for Spanish-English learners.

- `POST /transcribe` — Accepts audio or text input, detects language, then either translates (Spanish→English) or grammar-checks (English), and returns a phonetic explanation. Requires `transcribe-api-key` header.
- `POST /synthesize` — Text-to-speech synthesis via Google Cloud TTS.
- `GET /ping` — Health check.

**Services:** DeepSeek (LLM), Google Cloud Text-to-Speech

---

### EversPass
Session-based photo storage and management API.

- `POST /everspass/create-session` — Create a named session tied to a device ID.
- `GET /everspass/load-session` — Paginated session list for a device.
- `DELETE /everspass/delete-session/<session_id>` — Delete session and all associated photos.
- `GET /everspass/find-session/<session_id>` — Get single session details.
- `POST /everspass/upload-photos/<session_id>` — Batch upload photos with duplicate detection.
- `GET /everspass/photosession/<session_id>/photos` — Paginated photos with multiple thumbnail sizes.
- `DELETE /everspass/delete-photo/<photo_id>` — Delete a single photo.
- `POST /everspass/toggle-like/<photo_id>` — Toggle like on a photo.
- `POST /everspass/shorten-url` — Shorten a URL via is.gd.
- `GET /everspass/check-deviceid-exists/<device_id>` — Check if a device has any sessions.
- `GET /everspass/check-photosession-exists/<session_id>` — Check if a session has photos.
- `GET /everspass/hello-world` — Health check.

**Services:** PocketBase, is.gd

---

### PortfolioForm
Contact form handler for [everscode.com](https://everscode.com) with spam protection and email notifications.

- `POST /portfoliocontactform/` — Submit a contact form. Includes honeypot detection, gibberish filtering, suspicious email detection, and per-IP/per-email 24-hour rate limiting.

**Services:** PocketBase (stores submissions), Resend (email notifications)

---

### EverApply
Placeholder app, under development.

- `GET /everapply/hello-world` — Health check.

---

### Test
Debug/smoke test endpoint.

- `GET /test/` — Returns a hello message.

---

## Tech Stack

- **Framework:** Flask 2.3.2
- **Database:** PocketBase
- **AI/LLM:** DeepSeek API
- **TTS:** Google Cloud Text-to-Speech
- **Email:** Resend
- **Deployment:** Railway (`web: python app.py`)

## Environment Variables

| Variable | Purpose |
|---|---|
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins |
| `DEEPSEEK_API_KEY` | DeepSeek API key (EversVozAPI) |
| `TRANSCRIBE_API_KEY` | Auth key required on transcribe/synthesize requests |
| `GOOGLE_APPLICATION_CREDENTIALS_BASE64` | Base64-encoded Google Cloud service account JSON |
| `POCKETBASE_API` | PocketBase server URL |
| `POCKETBASE_SUPERUSER_EMAIL` | PocketBase admin email |
| `POCKETBASE_SUPERUSER_PASSWORD` | PocketBase admin password |
| `RESEND_API` | Resend API key |

## Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create a .env file with the variables listed above
python app.py
```

Server runs on `http://localhost:5001`.

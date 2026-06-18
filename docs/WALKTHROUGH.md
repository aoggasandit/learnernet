# LearnerNet — Quick Walkthrough

This document shows how to run the app locally, exercise core features, and prepare a short demo recording.

Prerequisites
- Python 3.10+ installed
- From the project root run:

```
python -m pip install -r requirements.txt
```

Initialize database and sample data

Open a Python REPL from the project root or run a tiny script:

```
python -c "from app import init_db, ensure_upload_dir, ensure_sample_data; init_db(); ensure_upload_dir(); ensure_sample_data()"
```

Run the app (Streamlit)

```
streamlit run app.py
```

Environment variables (set before running)
- `OPENAI_API_KEY` — optional (for AI features)
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` — for email (password reset)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_OAUTH_USER` — alternative Gmail method
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` — for SMS alerts
- `EMERGENCY_SMS_RECIPIENTS` — comma-separated phone numbers
- `SUPER_ADMIN_USERNAME`, `SUPER_ADMIN_PASSWORD`, `SUPER_ADMIN_EMAIL` — seeded admin account values

Key pages and features to demo
- Research & Learning Feed — posts, comments, likes
- Profile management — update profile and pictures
- Posts and media uploads — use the uploads folder
- QR scan & geofence events — simulated via Python helper functions
- Safety events — flagged content detection (SAFE_KEYWORDS)
- Password reset flow — `create_password_reset()` and `send_reset_email()`

How to simulate events from a REPL (useful during a demo)

```
python - <<'PY'
from app import fetch_user, record_scan_event, notify_parents_of_event
admin = fetch_user('admin')
# create a fake scan event
record_scan_event(scanner_id=admin['id'], student_user_id=2, event_type='Pickup', latitude=0.0, longitude=0.0, location='Main Gate')
# notify parents (requires TWILIO env configured or will raise)
# notify_parents_of_event(2, 'Pickup', latitude=0.0, longitude=0.0, location='Main Gate')
PY
```

Where settings live
- Settings are stored in the `settings` table. Use `get_setting(key)` and `set_setting(key, value)` helpers.
- Safe perimeter: `get_safe_zone()` / `update_safe_zone(lat, lng, radius_meters)`

Notes
- The app uses SQLite at `social_learning.db` by default.
- Uploaded files are saved to the `uploads/` directory.
- If you change environment variables, restart Streamlit.

Files created for this walkthrough
- [docs/SECURITY_SETUP.md](docs/SECURITY_SETUP.md)
- [docs/VIDEO_SCRIPT.md](docs/VIDEO_SCRIPT.md)
- [walkthrough.html](walkthrough.html)

End of walkthrough.
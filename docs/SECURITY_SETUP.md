# Security & Settings Guide

This file documents the app's security-related configuration and recommended setup steps.

Roles and permissions
- Roles are defined in `ROLE_PERMISSIONS` in `app.py`.
- Assign roles in the `users` table (`role` column). Key roles: `Super Admin`, `School Management`, `Staff/Security`, `Parent`, `Student`.

Passwords
- Passwords are hashed using PBKDF2-HMAC-SHA256 with 100,000 iterations.
- Use `create_user_with_email()` to create users; the helper stores salted password hashes.
- To reset a password use `create_password_reset(user_id)` to generate a token and `reset_password(token, new_password)` to apply it.
- Ensure SMTP or Gmail OAuth is configured for sending reset emails.

Email (password resets)
- Preferred: set `SMTP_USERNAME` and `SMTP_PASSWORD` and optionally `SMTP_SERVER`/`SMTP_PORT`.
- Fallback: configure Google OAuth env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`, `GOOGLE_OAUTH_USER` and install `google-auth` packages.
- Test sending a reset email in a REPL:

```
python -c "from app import create_password_reset, send_reset_email, fetch_user; u = fetch_user('admin'); t = create_password_reset(u['id']); send_reset_email(u['email'], t)"
```

SMS alerts
- SMS uses Twilio. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_PHONE_NUMBER`.
- Set `EMERGENCY_SMS_RECIPIENTS` for additional numbers to notify.
- Test via a small script that calls `send_sms()`.

Safe perimeter / Geofence
- The safe zone is configurable via `update_safe_zone(center_lat, center_lng, radius_meters)`.
- Use `is_inside_safe_zone(lat, lng)` to evaluate if coordinates are inside.
- Recommended: store a JSON-encoded `safe_zone` in `settings` table or update via helper.

Data protection & backups
- `social_learning.db` is a local SQLite file. For production, migrate to a managed DB.
- Periodically back up the file and the `uploads/` directory.

Deploy-time recommendations
- Run behind TLS (use reverse proxy like nginx or a hosted platform that provides HTTPS).
- Do not expose `social_learning.db` or `uploads/` directory publicly.
- Lock down environment variables and use secrets management (Azure Key Vault, AWS Secrets Manager, or env files outside source control).
- Use a stronger password policy and multi-factor authentication for production admin accounts.

Audit & logging
- The app records events into DB tables: `qr_scans`, `geofence_events`, `safety_events`.
- Add centralized logging (e.g., syslog, cloud logging) and monitoring in production.

If you want, I can:
- Add a small admin UI page to manage `safe_zone` and `settings` from the Streamlit app.
- Add a `settings_editor.py` script to read/update `settings` safely.

End of security guide.
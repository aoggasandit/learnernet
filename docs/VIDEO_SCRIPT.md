# Demo Video Script — 3–6 minute walkthrough

Goal: show how to set up the app, configure security settings, and demonstrate core flows.

Structure & narration (timestamps are approximate)

0:00 — Intro (10s)
- Show app name and a 1-sentence summary: "LearnerNet — a school-focused social and safety dashboard." 

0:10 — Install & run (40s)
- Terminal: `python -m pip install -r requirements.txt`
- Terminal: `python -c "from app import init_db, ensure_upload_dir, ensure_sample_data; init_db(); ensure_upload_dir(); ensure_sample_data()"`
- Terminal: `streamlit run app.py`

0:50 — Environment & security (40s)
- Explain env vars: `OPENAI_API_KEY`, SMTP creds, Twilio creds.
- Show a sample `.env` (do not display secrets on camera). Mention using a secrets manager.

1:30 — Log in as Super Admin (30s)
- Use seeded credentials (or show how to create a user via REPL).
- Navigate the UI: feed, profiles, posts.

2:00 — Demonstrate safety features (60s)
- Create a post with a flagged keyword and show it's recorded to `safety_events`.
- Simulate a QR scan or geofence event via a REPL command and show the `qr_scans`/`geofence_events` views.

3:00 — Password reset & notifications (40s)
- Generate a password reset token and call `send_reset_email()` (explain SMTP/Twilio must be configured).

3:40 — Wrap up (20s)
- Show backups, recommended production steps (TLS, secret manager, migrate DB), and where to find docs.

Recording tips
- Use OBS or default screen recorder. Record terminal at 1280x720, 30 fps.
- When showing env vars, blur values or show placeholder values.
- Keep terminal commands copyable by including them in the video description or upload the full script to the repo.

Commands to include in video description

```
python -m pip install -r requirements.txt
python -c "from app import init_db, ensure_upload_dir, ensure_sample_data; init_db(); ensure_upload_dir(); ensure_sample_data()"
streamlit run app.py
```

End of script.
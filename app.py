import base64
import datetime
import hashlib
import io
import json
import os
import re
import secrets
import sqlite3
import urllib.parse
import urllib.request
from pathlib import Path
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
import openai
import streamlit as st

SAFE_KEYWORDS = [
    "kill",
    "die",
    "attack",
    "threat",
    "bully",
    "stupid",
    "idiot",
    "hate",
    "shut up",
    "bastard",
    "abuse",
    "violence",
    "threaten",
    "terror",
    "harass",
    "rape",
    "destroy",
    "bomb",
]

ROLE_PERMISSIONS = {
    "Super Admin": [
        "view_all_data",
        "manage_users",
        "change_settings",
        "reset_passwords",
        "view_safety_events",
        "view_all_scans",
        "download_reports",
        "manage_school",
    ],
    "School Management": [
        "view_all_students",
        "view_geofence_events",
        "view_late_pickups",
        "download_reports",
        "view_safety_events",
    ],
    "Staff/Security": [
        "scan_qr",
        "mark_pickup",
        "view_today_scans",
    ],
    "Parent": [
        "view_own_child",
        "view_child_location",
        "receive_alerts",
    ],
    "Student": [
        "view_own_status",
        "consent_tracking",
    ],
}

SAFE_PERIMETER_DEFAULT = {
    "center_lat": 0.0,
    "center_lng": 0.0,
    "radius_meters": 300.0,
}

load_dotenv()

# Initialize OpenAI API key from environment (or .env). Do not make any requests at import time.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

DB_PATH = "social_learning.db"
UPLOAD_DIR = "uploads"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return salt, password_hash.hex()


def verify_password(password, stored_hash, stored_salt):
    if not stored_hash or not stored_salt:
        return False
    salt, candidate_hash = hash_password(password, stored_salt)
    return secrets.compare_digest(candidate_hash, stored_hash)


def analyze_text_safety(text):
    normalized = text.lower()
    for keyword in SAFE_KEYWORDS:
        if keyword in normalized:
            return {
                "flagged": True,
                "reason": f"Contains flagged keyword '{keyword}'.",
                "severity": "high",
            }
    return {"flagged": False, "reason": None, "severity": "low"}


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            salt TEXT,
            email TEXT,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'Parent',
            active INTEGER DEFAULT 1,
            user_code TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(post_id, user_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS post_media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            media_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            profile_picture TEXT,
            cover_picture TEXT,
            bio TEXT,
            first_name TEXT,
            last_name TEXT,
            location TEXT,
            occupation TEXT,
            website TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS parent_child_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_user_id INTEGER NOT NULL,
            student_user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(parent_user_id, student_user_id),
            FOREIGN KEY (parent_user_id) REFERENCES users(id),
            FOREIGN KEY (student_user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS qr_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanner_id INTEGER,
            student_user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            location TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (scanner_id) REFERENCES users(id),
            FOREIGN KEY (student_user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS geofence_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS safety_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "password_hash" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "salt" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN salt TEXT")
    if "email" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    if "phone" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
    if "role" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'Parent'")
    if "active" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
    if "user_code" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN user_code TEXT")

    conn.commit()
    conn.close()


def ensure_upload_dir():
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)


def save_upload(uploaded_file):
    file_name = uploaded_file.name
    safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{file_name}"
    save_path = Path(UPLOAD_DIR) / safe_name
    with open(save_path, "wb") as out_file:
        out_file.write(uploaded_file.getbuffer())
    return str(save_path), uploaded_file.type or "application/octet-stream"


def add_post(user_id, title, body):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO posts (user_id, title, body, created_at) VALUES (?, ?, ?, ?)",
        (user_id, title, body, created_at),
    )
    post_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return post_id


def add_post_media(post_id, user_id, filename, filepath, media_type):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO post_media (post_id, user_id, filename, filepath, media_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (post_id, user_id, filename, filepath, media_type, created_at),
    )
    conn.commit()
    conn.close()


def get_post_media(post_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT filename, filepath, media_type FROM post_media WHERE post_id = ? ORDER BY created_at ASC",
        (post_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"filename": row[0], "filepath": row[1], "media_type": row[2]} for row in rows
    ]


def display_media(media_items):
    for media in media_items:
        try:
            with open(media["filepath"], "rb") as file_handle:
                file_bytes = file_handle.read()
            if media["media_type"].startswith("image"):
                st.image(file_bytes, caption=media["filename"], use_column_width=True)
            elif media["media_type"].startswith("video"):
                st.video(file_bytes)
            else:
                st.write(f"Media: {media['filename']}")
        except FileNotFoundError:
            st.warning(f"Uploaded file not found: {media['filename']}")


def add_comment(post_id, user_id, body):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(
            id=row[0],
            username=row[1],
            created_at=row[2],
            password_hash=row[3],
            salt=row[4],
        )
        if row
        else None
    )


def fetch_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email, phone, role, active, user_code FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(
            id=row[0],
            username=row[1],
            created_at=row[2],
            password_hash=row[3],
            salt=row[4],
            email=row[5],
            phone=row[6],
            role=row[7],
            active=row[8],
            user_code=row[9],
        )
        if row
        else None
    )


def fetch_user(username):
    """Fetch a user dict by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email, phone, role, active, user_code FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(
            id=row[0],
            username=row[1],
            created_at=row[2],
            password_hash=row[3],
            salt=row[4],
            email=row[5],
            phone=row[6],
            role=row[7],
            active=row[8],
            user_code=row[9],
        )
        if row
        else None
    )


def fetch_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email, phone, role, active, user_code FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(
            id=row[0],
            username=row[1],
            created_at=row[2],
            password_hash=row[3],
            salt=row[4],
            email=row[5],
            phone=row[6],
            role=row[7],
            active=row[8],
            user_code=row[9],
        )
        if row
        else None
    )


def create_password_reset(user_id, ttl_minutes=60):
    conn = get_connection()
    cursor = conn.cursor()
    token = secrets.token_urlsafe(32)
    created_at = datetime.datetime.utcnow()
    expires_at = (created_at + datetime.timedelta(minutes=ttl_minutes)).isoformat()
    cursor.execute(
        "INSERT INTO password_resets (user_id, token, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (user_id, token, expires_at, created_at.isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def send_reset_email(to_email, token):
    """Send password reset email.

    Priority:
    1. If SMTP_USERNAME and SMTP_PASSWORD present, send via SMTP.
    2. Else if Google OAuth client id/secret/refresh token present, send via Gmail API.
    Raises RuntimeError if neither method is available or sending fails.
    """
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")

    subject = "LearnerNet password reset"
    reset_instructions = (
        f"Use this token to reset your password in the app:\n\n{token}\n\n"
        "Open the Auth page, choose 'Login', then use the 'Forgot password' flow to paste the token and set a new password."
    )

    # Try SMTP first if credentials provided
    if smtp_user and smtp_pass:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg.set_content(reset_instructions)

        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)
        return

    # Fallback: Gmail API using OAuth2 refresh token
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    google_refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    google_user = os.getenv("GOOGLE_OAUTH_USER")

    if not (google_client_id and google_client_secret and google_refresh_token and google_user):
        raise RuntimeError("SMTP credentials missing in environment variables.")

    # Lazy import Google OAuth libraries (only needed if using Gmail API)
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import base64 as _b64
    except ImportError as exc:
        raise RuntimeError(f"Gmail OAuth requires google-auth packages. Install with: pip install google-auth google-auth-oauthlib google-api-python-client. Error: {exc}")

    creds = Credentials(
        token=None,
        refresh_token=google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=google_client_id,
        client_secret=google_client_secret,
    )
    try:
        creds.refresh(Request())
    except Exception as exc:
        raise RuntimeError(f"Could not refresh Google OAuth token: {exc}")

    service = build("gmail", "v1", credentials=creds)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = google_user
    msg["To"] = to_email
    msg.set_content(reset_instructions)

    raw_bytes = msg.as_bytes()
    raw_b64 = _b64.urlsafe_b64encode(raw_bytes).decode()
    body = {"raw": raw_b64}
    try:
        service.users().messages().send(userId="me", body=body).execute()
    except Exception as exc:
        raise RuntimeError(f"Failed to send email via Gmail API: {exc}")


def verify_reset_token(token):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "SELECT id, user_id, expires_at, used FROM password_resets WHERE token = ?",
        (token,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    rid, user_id, expires_at, used = row
    if used:
        return None
    if expires_at < now:
        return None
    return dict(id=rid, user_id=user_id)


def reset_password(token, new_password):
    valid = verify_reset_token(token)
    if not valid:
        return False
    user_id = valid["user_id"]
    salt, password_hash = hash_password(new_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (password_hash, salt, user_id))
    cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (valid["id"],))
    conn.commit()
    conn.close()
    return True


def create_user(username, password, email=None, phone=None, role="Parent", active=1):
    return create_user_with_email(username, password, email=email, phone=phone, role=role, active=active)


def generate_unique_user_code():
    while True:
        code = secrets.token_urlsafe(12)
        if not fetch_user_by_code(code):
            return code


def fetch_user_by_code(user_code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email, phone, role, active, user_code FROM users WHERE user_code = ?",
        (user_code,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(
            id=row[0],
            username=row[1],
            created_at=row[2],
            password_hash=row[3],
            salt=row[4],
            email=row[5],
            phone=row[6],
            role=row[7],
            active=row[8],
            user_code=row[9],
        )
        if row
        else None
    )


def create_user_with_email(username, password, email=None, phone=None, role="Parent", active=1):
    if fetch_user(username) is not None:
        return None
    if email and fetch_user_by_email(email) is not None:
        return None
    if phone:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE phone = ?", (phone,))
        if cursor.fetchone():
            conn.close()
            return None
        conn.close()

    salt, password_hash = hash_password(password)
    user_code = generate_unique_user_code()
    created_at = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, salt, email, phone, role, active, user_code, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (username, password_hash, salt, email, phone, role, active, user_code, created_at),
    )
    conn.commit()
    user = fetch_user(username)
    conn.close()
    return user


def authenticate_user(username_or_email, password):
    user = fetch_user(username_or_email)
    if not user:
        user = fetch_user_by_email(username_or_email)
    if not user:
        return None
    if not user.get("active"):
        return None
    if verify_password(password, user.get("password_hash"), user.get("salt")):
        return user
    return None


def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return default
    return row[0]


def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)),
    )
    conn.commit()
    conn.close()


def get_safe_zone():
    raw = get_setting("safe_zone")
    if raw is None:
        return SAFE_PERIMETER_DEFAULT.copy()
    try:
        zone = json.loads(raw)
        return {
            "center_lat": float(zone.get("center_lat", SAFE_PERIMETER_DEFAULT["center_lat"])),
            "center_lng": float(zone.get("center_lng", SAFE_PERIMETER_DEFAULT["center_lng"])),
            "radius_meters": float(zone.get("radius_meters", SAFE_PERIMETER_DEFAULT["radius_meters"])),
        }
    except Exception:
        return SAFE_PERIMETER_DEFAULT.copy()


def update_safe_zone(center_lat, center_lng, radius_meters):
    set_setting(
        "safe_zone",
        {
            "center_lat": float(center_lat),
            "center_lng": float(center_lng),
            "radius_meters": float(radius_meters),
        },
    )


def haversine_distance(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371000 * c


def is_inside_safe_zone(latitude, longitude):
    zone = get_safe_zone()
    distance = haversine_distance(latitude, longitude, zone["center_lat"], zone["center_lng"])
    return distance <= float(zone["radius_meters"])


def get_parents_for_student(student_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT p.id, p.username, p.email, p.phone FROM users p JOIN parent_child_relations r ON p.id = r.parent_user_id WHERE r.student_user_id = ?",
        (student_user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": row[0], "username": row[1], "email": row[2], "phone": row[3]} for row in rows
    ]


def get_students_for_parent(parent_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT s.id, s.username, s.email, s.phone FROM users s JOIN parent_child_relations r ON s.id = r.student_user_id WHERE r.parent_user_id = ?",
        (parent_user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": row[0], "username": row[1], "email": row[2], "phone": row[3]} for row in rows
    ]


def create_parent_child_relation(parent_user_id, student_user_id):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT OR IGNORE INTO parent_child_relations (parent_user_id, student_user_id, created_at) VALUES (?, ?, ?)",
        (parent_user_id, student_user_id, created_at),
    )
    conn.commit()
    conn.close()


def record_scan_event(scanner_id, student_user_id, event_type, latitude=None, longitude=None, location=None, notes=None):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO qr_scans (scanner_id, student_user_id, event_type, latitude, longitude, location, notes, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (scanner_id, student_user_id, event_type, latitude, longitude, location, notes, created_at),
    )
    conn.commit()
    conn.close()


def record_geofence_event(student_user_id, event_type, latitude=None, longitude=None):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO geofence_events (student_user_id, event_type, latitude, longitude, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (student_user_id, event_type, latitude, longitude, created_at),
    )
    conn.commit()
    conn.close()


def record_safety_event(user_id, content, category="content", severity="medium"):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO safety_events (user_id, content, category, severity, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, content, category, severity, created_at),
    )
    conn.commit()
    conn.close()


def get_all_scan_events():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT s.id, s.student_user_id, u.username, s.scanner_id, scanner.username, s.event_type, s.location, s.latitude, s.longitude, s.notes, s.created_at FROM qr_scans s LEFT JOIN users u ON u.id = s.student_user_id LEFT JOIN users scanner ON scanner.id = s.scanner_id ORDER BY s.created_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "student_user_id": row[1],
            "student_username": row[2],
            "scanner_id": row[3],
            "scanner_username": row[4],
            "event_type": row[5],
            "location": row[6],
            "latitude": row[7],
            "longitude": row[8],
            "notes": row[9],
            "created_at": row[10],
        }
        for row in rows
    ]


def get_today_scan_events():
    today = datetime.datetime.utcnow().date().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, student_user_id, event_type, location, latitude, longitude, notes, created_at FROM qr_scans WHERE created_at >= ? ORDER BY created_at DESC",
        (today + "T00:00:00",),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "student_user_id": row[1],
            "event_type": row[2],
            "location": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "notes": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


def get_geofence_events():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT g.id, g.student_user_id, u.username, g.event_type, g.latitude, g.longitude, g.created_at FROM geofence_events g LEFT JOIN users u ON u.id = g.student_user_id ORDER BY g.created_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "student_user_id": row[1],
            "student_username": row[2],
            "event_type": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def get_late_pickups():
    cutoff = get_setting("pickup_cutoff", "15:00")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, student_user_id, event_type, location, latitude, longitude, notes, created_at FROM qr_scans WHERE event_type = 'Pickup' AND created_at >= ? ORDER BY created_at DESC",
        (datetime.datetime.utcnow().date().isoformat() + "T" + cutoff + ":00",),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "student_user_id": row[1],
            "event_type": row[2],
            "location": row[3],
            "latitude": row[4],
            "longitude": row[5],
            "notes": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]


def get_safety_events():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT s.id, s.user_id, u.username, s.content, s.category, s.severity, s.created_at FROM safety_events s LEFT JOIN users u ON u.id = s.user_id ORDER BY s.created_at DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "content": row[3],
            "category": row[4],
            "severity": row[5],
            "created_at": row[6],
        }
        for row in rows
    ]


def get_emergency_recipients():
    raw = os.getenv("EMERGENCY_SMS_RECIPIENTS", "")
    return [phone.strip() for phone in raw.split(",") if phone.strip()]


def send_sms(to_number, message):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    if not account_sid or not auth_token or not from_number:
        raise RuntimeError("Twilio credentials are not configured for SMS alerts.")
    data = urllib.parse.urlencode({"To": to_number, "From": from_number, "Body": message}).encode("utf-8")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    req = urllib.request.Request(url, data=data)
    auth_header = base64.b64encode(f"{account_sid}:{auth_token}".encode("utf-8")).decode("ascii")
    req.add_header("Authorization", f"Basic {auth_header}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")


def notify_parents_of_event(student_user_id, event_type, latitude=None, longitude=None, location=None):
    student = fetch_user_by_id(student_user_id)
    parents = get_parents_for_student(student_user_id)
    if not parents:
        return []
    zone = get_safe_zone()
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}" if latitude and longitude else ""
    message = (
        f"Alert: {student['username']} {event_type} outside safe perimeter. "
        f"Location: {location or 'unknown'}. "
        f"Map: {google_maps_url}"
    )
    results = []
    for parent in parents:
        if parent.get("phone"):
            try:
                send_sms(parent["phone"], message)
                results.append({"parent": parent["username"], "status": "sent"})
            except Exception as exc:
                results.append({"parent": parent["username"], "status": f"failed: {exc}"})
    for emergency_phone in get_emergency_recipients():
        try:
            send_sms(emergency_phone, message)
            results.append({"parent": emergency_phone, "status": "sent"})
        except Exception as exc:
            results.append({"parent": emergency_phone, "status": f"failed: {exc}"})
    return results


def user_has_permission(user, permission):
    if not user:
        return False
    return permission in ROLE_PERMISSIONS.get(user.get("role", ""), [])


# Profile management functions
def get_or_create_profile(user_id):
    """Get profile or create empty one if doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        profile = {
            "id": row[0],
            "user_id": row[1],
            "profile_picture": row[2],
            "cover_picture": row[3],
            "bio": row[4],
            "first_name": row[5],
            "last_name": row[6],
            "location": row[7],
            "occupation": row[8],
            "website": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }
        conn.close()
        return profile
    
    # Create empty profile
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO profiles (user_id, bio, first_name, last_name, location, occupation, website, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, None, None, None, None, None, None, created_at, created_at),
    )
    conn.commit()
    conn.close()
    
    return get_or_create_profile(user_id)


def update_profile(user_id, bio=None, first_name=None, last_name=None, location=None, occupation=None, website=None):
    """Update user profile details."""
    conn = get_connection()
    cursor = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    
    cursor.execute(
        """UPDATE profiles 
           SET bio = ?, first_name = ?, last_name = ?, location = ?, occupation = ?, website = ?, updated_at = ?
           WHERE user_id = ?""",
        (bio, first_name, last_name, location, occupation, website, updated_at, user_id),
    )
    conn.commit()
    conn.close()


def update_profile_picture(user_id, filepath):
    """Update profile picture filepath."""
    conn = get_connection()
    cursor = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "UPDATE profiles SET profile_picture = ?, updated_at = ? WHERE user_id = ?",
        (filepath, updated_at, user_id),
    )
    conn.commit()
    conn.close()


def update_cover_picture(user_id, filepath):
    """Update cover picture filepath."""
    conn = get_connection()
    cursor = conn.cursor()
    updated_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "UPDATE profiles SET cover_picture = ?, updated_at = ? WHERE user_id = ?",
        (filepath, updated_at, user_id),
    )
    conn.commit()
    conn.close()


def add_post(user_id, title, body):
    safety = analyze_text_safety(f"{title}\n{body}")
    if safety["flagged"]:
        record_safety_event(user_id, f"Post flagged: {title}\n{body}", "post", safety["severity"])
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO posts (user_id, title, body, created_at) VALUES (?, ?, ?, ?)",
        (user_id, title, body, created_at),
    )
    conn.commit()
    conn.close()


def add_comment(post_id, user_id, body):
    safety = analyze_text_safety(body)
    if safety["flagged"]:
        record_safety_event(user_id, body, "comment", safety["severity"])
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO comments (post_id, user_id, body, created_at) VALUES (?, ?, ?, ?)",
        (post_id, user_id, body, created_at),
    )
    conn.commit()
    conn.close()


def toggle_like(post_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM likes WHERE id = ?", (row[0],))
    else:
        cursor.execute(
            "INSERT INTO likes (post_id, user_id, created_at) VALUES (?, ?, ?)",
            (post_id, user_id, datetime.datetime.utcnow().isoformat()),
        )
    conn.commit()
    conn.close()


def has_liked(post_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM likes WHERE post_id = ? AND user_id = ?",
        (post_id, user_id),
    )
    liked = cursor.fetchone() is not None
    conn.close()
    return liked


def get_posts():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.title, p.body, p.created_at, u.username,
            COALESCE(l.like_count, 0),
            COALESCE(c.comment_count, 0)
        FROM posts p
        JOIN users u ON u.id = p.user_id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS like_count FROM likes GROUP BY post_id
        ) l ON l.post_id = p.id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS comment_count FROM comments GROUP BY post_id
        ) c ON c.post_id = p.id
        ORDER BY p.created_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "body": row[2],
            "created_at": row[3],
            "username": row[4],
            "like_count": row[5],
            "comment_count": row[6],
        }
        for row in rows
    ]


def get_comments(post_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.body, c.created_at, u.username
        FROM comments c
        JOIN users u ON u.id = c.user_id
        WHERE c.post_id = ?
        ORDER BY c.created_at ASC
        """,
        (post_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"body": row[0], "created_at": row[1], "username": row[2]} for row in rows
    ]


def add_resource(user_id, title, url, description):
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO resources (user_id, title, url, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, url, description, created_at),
    )
    conn.commit()
    conn.close()


def get_resources():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.id, r.title, r.url, r.description, r.created_at, u.username
        FROM resources r
        LEFT JOIN users u ON u.id = r.user_id
        ORDER BY r.created_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "url": row[2],
            "description": row[3],
            "created_at": row[4],
            "username": row[5] or "Community",
        }
        for row in rows
    ]


def get_user_posts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.id, p.title, p.body, p.created_at,
            COALESCE(l.like_count, 0),
            COALESCE(c.comment_count, 0)
        FROM posts p
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS like_count FROM likes GROUP BY post_id
        ) l ON l.post_id = p.id
        LEFT JOIN (
            SELECT post_id, COUNT(*) AS comment_count FROM comments GROUP BY post_id
        ) c ON c.post_id = p.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "title": row[1],
            "body": row[2],
            "created_at": row[3],
            "like_count": row[4],
            "comment_count": row[5],
        }
        for row in rows
    ]


def get_user_resources(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, url, description, created_at FROM resources WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": row[0], "title": row[1], "url": row[2], "description": row[3], "created_at": row[4]}
        for row in rows
    ]


def get_user_comments(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT c.body, c.created_at, p.title
        FROM comments c
        JOIN posts p ON p.id = c.post_id
        WHERE c.user_id = ?
        ORDER BY c.created_at DESC
        """,
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"body": row[0], "created_at": row[1], "post_title": row[2]} for row in rows
    ]


def get_user_likes_received(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM likes l
        JOIN posts p ON p.id = l.post_id
        WHERE p.user_id = ?
        """,
        (user_id,),
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def get_user_likes_given(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM likes WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def send_message(sender_id, receiver_id, body):
    """Send a private message from sender to receiver."""
    safety = analyze_text_safety(body)
    if safety["flagged"]:
        record_safety_event(sender_id, body, "message", safety["severity"])
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO messages (sender_id, receiver_id, body, created_at) VALUES (?, ?, ?, ?)",
        (sender_id, receiver_id, body, created_at),
    )
    conn.commit()
    conn.close()


def get_conversation(user_id, other_user_id):
    """Get all messages between two users, ordered by date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id, m.sender_id, m.receiver_id, m.body, m.created_at, u.username
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
        """,
        (user_id, other_user_id, other_user_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "sender_id": row[1],
            "receiver_id": row[2],
            "body": row[3],
            "created_at": row[4],
            "sender_username": row[5],
        }
        for row in rows
    ]


def get_message_list(user_id):
    """Get a list of unique users this user has conversed with."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT CASE
            WHEN sender_id = ? THEN receiver_id
            ELSE sender_id
        END AS other_user_id,
        u.username
        FROM messages m
        JOIN users u ON u.id = CASE
            WHEN sender_id = ? THEN receiver_id
            ELSE sender_id
        END
        WHERE sender_id = ? OR receiver_id = ?
        ORDER BY m.created_at DESC
        """,
        (user_id, user_id, user_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"user_id": row[0], "username": row[1]} for row in rows]


def get_all_users_except_current(current_user_id):
    """Get all users except the current one."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username FROM users WHERE id != ? ORDER BY username",
        (current_user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "username": row[1]} for row in rows]


def ai_research_answer(question):
    if not OPENAI_API_KEY:
        return (
            "OpenAI API key is missing. Set the environment variable OPENAI_API_KEY before running the app."
        )

    # Use the new OpenAI client (openai>=1.0.0) to create chat completions.
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = (
        "You are an AI learning assistant that helps learners do research and learn. "
        "Answer clearly, provide step-by-step guidance, and suggest resources or keywords when relevant. "
        f"User question: {question}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert study coach and researcher."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=650,
        )
        # The new client returns a structure similar to earlier SDKs; extract the message text.
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"AI request failed: {exc}"


def generate_ai_image(prompt, size="1024x1024"):
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is missing.")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(model="gpt-image-1", prompt=prompt, size=size)
    b64_image = response.data[0].b64_json
    return base64.b64decode(b64_image)


def edit_ai_image(prompt, image_bytes, filename, size="1024x1024"):
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key is missing.")
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    image_file = io.BytesIO(image_bytes)
    image_file.name = filename
    if hasattr(client.images, "edit"):
        response = client.images.edit(
            model="gpt-image-1",
            image=[image_file],
            prompt=prompt,
            size=size,
        )
    else:
        response = client.images.generate(
            model="gpt-image-1",
            image=[image_file],
            prompt=prompt,
            size=size,
        )
    b64_image = response.data[0].b64_json
    return base64.b64decode(b64_image)


def format_ai_document(source_text, instruction, style="Summary"):
    if not OPENAI_API_KEY:
        return "OpenAI API key is missing. Set the environment variable OPENAI_API_KEY before running the app."
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = (
        "You are a document formatting assistant."
        " Produce clear, structured, learner-friendly documents using headings, lists, and paragraph formatting."
    )
    user_prompt = (
        f"Please {instruction.lower()} the following text in {style} style."
        f" Preserve meaning and structure, and return the output in markdown format.\n\nSource text:\n{source_text}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"AI request failed: {exc}"


def ensure_sample_data():
    user_count = len(get_all_users_except_current(0))
    if user_count > 0:
        return

    super_admin_username = os.getenv("SUPER_ADMIN_USERNAME", "admin")
    super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "Admin1234!")
    super_admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@redemptiongate.local")
    super_admin_phone = os.getenv("SUPER_ADMIN_PHONE", "")
    super_admin = fetch_user(super_admin_username)
    if super_admin is None:
        super_admin = create_user_with_email(
            super_admin_username,
            super_admin_password,
            email=super_admin_email,
            phone=super_admin_phone or None,
            role="Super Admin",
            active=1,
        )

    staff = fetch_user("StudyBuddy")
    if staff is None:
        staff = create_user_with_email(
            "StudyBuddy",
            "learning123",
            email="security@redemptiongate.local",
            phone=None,
            role="Staff/Security",
            active=1,
        )

    add_post(
        super_admin["id"],
        "Welcome to Redemption Gate",
        "The app is now secured with role-based access, geofence alerts, and QR scan tracking.",
    )
    add_resource(
        super_admin["id"],
        "Safety and Security Guide",
        "https://example.com/safety-guide",
        "This portal is designed for school management, staff, parents, and students only.",
    )
    update_safe_zone(0.0, 0.0, 300.0)


def display_feed(current_user_id):
    st.header("Research & Learning Feed")
    posts = get_posts()
    if not posts:
        st.info("No posts yet. Create one to start a discussion.")
        return

    for post in posts:
        st.markdown(f"### {post['title']}")
        st.markdown(f"*by {post['username']} · {post['created_at'][:10]}*")
        st.write(post["body"])

        media_items = get_post_media(post["id"])
        if media_items:
            display_media(media_items)

        st.write(f"💬 {post['comment_count']}  |  👍 {post['like_count']}")

        if current_user_id:
            liked = has_liked(post["id"], current_user_id)
            action_label = "Unlike" if liked else "Like"
            if st.button(action_label, key=f"like_{post['id']}"):
                toggle_like(post["id"], current_user_id)
                st.rerun()
        else:
            st.info("Sign in to like posts and add comments.")

        with st.expander(f"Comments ({post['comment_count']})"):
            comments = get_comments(post["id"])
            if not comments:
                st.write("No comments yet.")
            for comment in comments:
                st.markdown(f"**{comment['username']}** · {comment['created_at'][:10]}")
                st.write(comment["body"])
                st.markdown("---")

            if current_user_id:
                comment_text = st.text_area(
                    "Add a comment",
                    key=f"comment_input_{post['id']}",
                    height=80,
                )
                if st.button("Post comment", key=f"comment_btn_{post['id']}"):
                    if comment_text.strip():
                        add_comment(post["id"], current_user_id, comment_text.strip())
                        st.rerun()
                    else:
                        st.error("Comment cannot be empty.")

        st.markdown("---")


def display_resources():
    st.header("Shared Learning Resources")
    resources = get_resources()
    if not resources:
        st.info("No resources shared yet.")
        return

    for resource in resources:
        st.write(f"**[{resource['title']}]({resource['url']})**")
        if resource["description"]:
            st.markdown(f"_{resource['description']}_")
        st.caption(f"Shared by {resource['username']} · {resource['created_at'][:10]}")
        st.markdown("---")


def main():
    init_db()
    ensure_upload_dir()
    ensure_sample_data()
    st.set_page_config(page_title="ScholarsNet", page_icon="📚", layout="wide")

    if "username" not in st.session_state:
        st.session_state.username = ""
        st.session_state.user_id = None
        st.session_state.email = ""
        st.session_state.auth_message = ""

    st.sidebar.title("ScholarsNet")
    if st.session_state.user_id:
        st.sidebar.success(f"Signed in as {st.session_state.username}")
        if st.sidebar.button("Sign out"):
            st.session_state.username = ""
            st.session_state.user_id = None
            st.session_state.email = ""
            st.session_state.auth_message = "You have signed out."
            st.rerun()
    else:
        st.sidebar.info("Use the Account page to sign in. Accounts are created by administrators only.")

    page = st.sidebar.radio(
        "Navigate",
        [
            "Home",
            "Create Post",
            "Share Resource",
            "AI Research Assistant",
            "AI Media Studio",
            "Direct Messages",
            "My Profile",
            "Security",
            "Admin",
            "Account",
        ],
    )

    if page == "Home":
        st.title("ScholarsNet")
        st.write(
            "Connect with other learners, scholars, publish short research posts, and find shared study resources."
        )
        display_feed(st.session_state.user_id)
        display_resources()

    elif page == "Create Post":
        st.title("Create a Discussion Post")
        if not st.session_state.user_id:
            st.warning("Please sign in before posting.")
        else:
            with st.form("post_form"):
                title = st.text_input("Post title")
                body = st.text_area("What do you want to share or ask?")
                media_files = st.file_uploader(
                    "Upload images or videos",
                    type=["png", "jpg", "jpeg", "gif", "mp4", "mov", "avi"],
                    accept_multiple_files=True,
                )
                submitted = st.form_submit_button("Publish")
                if submitted:
                    if title.strip() and (body.strip() or media_files):
                        post_id = add_post(st.session_state.user_id, title.strip(), body.strip())
                        for uploaded_file in media_files or []:
                            filepath, media_type = save_upload(uploaded_file)
                            add_post_media(
                                post_id,
                                st.session_state.user_id,
                                uploaded_file.name,
                                filepath,
                                media_type,
                            )
                        st.success("Post published successfully.")
                    else:
                        st.error("Title plus body or media is required.")

    elif page == "Share Resource":
        st.title("Share a Learning Resource")
        if not st.session_state.user_id:
            st.warning("Please sign in before sharing a resource.")
        else:
            with st.form("resource_form"):
                title = st.text_input("Resource title")
                url = st.text_input("Resource URL")
                description = st.text_area("Description")
                submitted = st.form_submit_button("Share Resource")
                if submitted:
                    if title.strip() and url.strip():
                        add_resource(
                            st.session_state.user_id,
                            title.strip(),
                            url.strip(),
                            description.strip(),
                        )
                        st.success("Resource shared successfully.")
                    else:
                        st.error("Title and URL are required.")

    elif page == "AI Research Assistant":
        st.title("AI Research Assistant")
        st.write(
            "Ask the AI for research guidance, summaries, study plans, or learning suggestions."
        )
        question = st.text_area("What would you like help with?", height=150)
        if st.button("Ask AI"):
            if question.strip():
                with st.spinner("Querying the AI..."):
                    answer = ai_research_answer(question.strip())
                st.markdown(answer)
            else:
                st.error("Please enter a question first.")

    elif page == "AI Media Studio":
        st.title("AI Media Studio")
        st.write("Generate or edit images, videos, and documents with AI.")

        with st.expander("Generate a new image"):
            image_prompt = st.text_area("Describe the image you want to create", height=120)
            image_size = st.selectbox("Image size", ["512x512", "1024x1024"], index=1)
            if st.button("Generate Image"):
                if image_prompt.strip():
                    with st.spinner("Generating image..."):
                        try:
                            image_bytes = generate_ai_image(image_prompt.strip(), size=image_size)
                            st.image(image_bytes, caption="Generated image", use_column_width=True)
                            st.download_button(
                                "Download image",
                                data=image_bytes,
                                file_name="generated_image.png",
                                mime="image/png",
                            )
                        except Exception as exc:
                            st.error(f"AI request failed: {exc}")
                else:
                    st.error("Enter an image description first.")

        with st.expander("Edit an existing image"):
            edit_prompt = st.text_area("Describe how to edit the image", height=100)
            edit_image_file = st.file_uploader("Upload an image to edit", type=["png", "jpg", "jpeg"], key="edit_image")
            edit_size = st.selectbox("Edit size", ["512x512", "1024x1024"], index=1)
            if st.button("Edit Image"):
                if edit_prompt.strip() and edit_image_file is not None:
                    with st.spinner("Editing image..."):
                        try:
                            image_bytes = edit_ai_image(
                                edit_prompt.strip(),
                                edit_image_file.getbuffer(),
                                edit_image_file.name,
                                size=edit_size,
                            )
                            st.image(image_bytes, caption="Edited image", use_column_width=True)
                            st.download_button(
                                "Download edited image",
                                data=image_bytes,
                                file_name="edited_image.png",
                                mime="image/png",
                            )
                        except Exception as exc:
                            st.error(f"AI request failed: {exc}")
                else:
                    st.error("Provide both an image and an edit prompt.")

        with st.expander("Generate or format a document"):
            doc_source = st.text_area("Paste your document text or topic prompt", height=140)
            instruction = st.selectbox(
                "Document action",
                [
                    "Create a polished study guide",
                    "Summarize the text",
                    "Rewrite as a formatted report",
                    "Create concise study notes",
                ],
            )
            doc_style = st.selectbox("Output style", ["Professional", "Learning guide", "Bullet list", "Essay"], index=1)
            if st.button("Format Document"):
                if doc_source.strip():
                    with st.spinner("Formatting document..."):
                        document_text = format_ai_document(doc_source.strip(), instruction, style=doc_style)
                        st.markdown(document_text)
                        st.download_button(
                            "Download text document",
                            data=document_text,
                            file_name="ai_document.txt",
                            mime="text/plain",
                        )
                        st.download_button(
                            "Download markdown document",
                            data=document_text,
                            file_name="ai_document.md",
                            mime="text/markdown",
                        )
                else:
                    st.error("Enter text or a topic before formatting.")

    elif page == "Direct Messages":
        st.title("Direct Messages")
        if not st.session_state.user_id:
            st.warning("Please sign in to send messages.")
        else:
            message_action = st.radio("What do you want to do?", ["View Conversations", "Start New Message"])

            if message_action == "View Conversations":
                conversations = get_message_list(st.session_state.user_id)
                if not conversations:
                    st.info("No conversations yet.")
                else:
                    selected_user = st.selectbox(
                        "Select a conversation",
                        [conv["username"] for conv in conversations],
                        key="conversation_select",
                    )
                    selected_user_obj = next(
                        (c for c in conversations if c["username"] == selected_user), None
                    )
                    if selected_user_obj:
                        other_user_id = selected_user_obj["user_id"]
                        chat_history = get_conversation(st.session_state.user_id, other_user_id)

                        st.subheader(f"Conversation with {selected_user}")
                        if not chat_history:
                            st.info("No messages yet.")
                        else:
                            for msg in chat_history:
                                if msg["sender_id"] == st.session_state.user_id:
                                    st.markdown(f"**You:** {msg['body']}")
                                else:
                                    st.markdown(f"**{msg['sender_username']}:** {msg['body']}")
                                st.caption(msg["created_at"][:16])

                        new_message = st.text_area(
                            "Type your message",
                            height=80,
                            key=f"msg_input_{other_user_id}",
                        )
                        if st.button("Send", key=f"msg_send_{other_user_id}"):
                            if new_message.strip():
                                send_message(
                                    st.session_state.user_id,
                                    other_user_id,
                                    new_message.strip(),
                                )
                                st.success("Message sent!")
                                st.rerun()
                            else:
                                st.error("Message cannot be empty.")

            else:
                all_users = get_all_users_except_current(st.session_state.user_id)
                if not all_users:
                    st.info("No other users available.")
                else:
                    recipient = st.selectbox(
                        "Select recipient",
                        [u["username"] for u in all_users],
                        key="new_message_recipient",
                    )
                    recipient_obj = next((u for u in all_users if u["username"] == recipient), None)
                    if recipient_obj:
                        message_text = st.text_area(
                            "Compose your message",
                            height=120,
                            key="new_message_text",
                        )
                        if st.button("Send Message"):
                            if message_text.strip():
                                send_message(
                                    st.session_state.user_id,
                                    recipient_obj["id"],
                                    message_text.strip(),
                                )
                                st.success(f"Message sent to {recipient}!")
                                st.rerun()
                            else:
                                st.error("Message cannot be empty.")
            user = fetch_user_by_id(st.session_state.user_id)
            st.subheader(user["username"])
            st.write(f"Joined: {user['created_at'][:10]}")
            likes_received = get_user_likes_received(user["id"])
            likes_given = get_user_likes_given(user["id"])
            comment_count = len(get_user_comments(user["id"]))
            st.write(
                f"Posts: {len(get_user_posts(user['id']))}  ·  Resources: {len(get_user_resources(user['id']))}  ·  Comments: {comment_count}"
            )
            st.write(f"Likes received: {likes_received}  ·  Likes given: {likes_given}")

            user_posts = get_user_posts(user["id"])
            user_resources = get_user_resources(user["id"])
            user_comments = get_user_comments(user["id"])

            if not user_posts and not user_resources and not user_comments:
                st.info("You haven't contributed yet. Create a post, share a resource, or add a comment.")

            if user_posts:
                st.markdown("### Your Posts")
                for post in user_posts:
                    st.write(f"**{post['title']}**")
                    st.write(post["body"])
                    st.caption(
                        f"{post['created_at'][:10]} · {post['like_count']} likes · {post['comment_count']} comments"
                    )

            if user_resources:
                st.markdown("### Your Resources")
                for resource in user_resources:
                    st.write(f"**[{resource['title']}]({resource['url']})**")
                    st.write(resource["description"])
                    st.caption(resource["created_at"][:10])

            if user_comments:
                st.markdown("### Your Comments")
                for comment in user_comments:
                    st.write(f"**{comment['post_title']}**")
                    st.write(comment["body"])
                    st.caption(comment["created_at"][:10])

    elif page == "Security":
        st.title("Security & Safe Zone Monitoring")
        if not st.session_state.user_id:
            st.warning("Please sign in to access the security dashboard.")
        else:
            current_user = fetch_user_by_id(st.session_state.user_id)
            st.write(f"Signed in as **{current_user['username']}** · {current_user['role']}")
            if current_user["role"] in ["Staff/Security", "School Management", "Super Admin"]:
                st.subheader("Scan student QR and log events")
                student_candidates = [u for u in get_all_users_except_current(0) if fetch_user_by_id(u["id"])["role"] == "Student"]
                student_choice = st.selectbox(
                    "Select student",
                    [s["username"] for s in student_candidates],
                    key="security_student_choice",
                )
                event_type = st.selectbox("Event type", ["Entry", "Exit", "Pickup"], key="security_event_type")
                location = st.text_input("Location description", key="security_location")
                latitude = st.number_input("Latitude", value=0.0, format="%.6f", key="security_lat")
                longitude = st.number_input("Longitude", value=0.0, format="%.6f", key="security_lng")
                notes = st.text_area("Notes", key="security_notes")
                if st.button("Record scan event"):
                    student_user = fetch_user(student_choice)
                    if student_user:
                        record_scan_event(
                            current_user["id"],
                            student_user["id"],
                            event_type,
                            latitude,
                            longitude,
                            location,
                            notes,
                        )
                        if not is_inside_safe_zone(latitude, longitude):
                            record_geofence_event(student_user["id"], "Exited safe perimeter", latitude, longitude)
                            notify_parents_of_event(student_user["id"], event_type, latitude, longitude, location)
                        st.success("Scan event recorded and logged.")

                if student_choice:
                    student_user = fetch_user(student_choice)
                    qr_payload = f"student:{student_user['user_code']}"
                    qr_url = f"https://chart.googleapis.com/chart?cht=qr&chs=250x250&chl={urllib.parse.quote(qr_payload)}"
                    st.markdown("#### Student QR code")
                    st.image(qr_url, caption="Scan this QR code at the gate", use_column_width=False)
                    st.code(qr_payload)

                st.markdown("---")
                st.subheader("Today's scan history")
                today_scans = get_today_scan_events()
                if not today_scans:
                    st.info("No scans recorded today.")
                else:
                    st.dataframe(today_scans)

            elif current_user["role"] == "Parent":
                st.subheader("Your children")
                children = get_students_for_parent(current_user["id"])
                if not children:
                    st.info("No linked children found. Contact an administrator to connect your account.")
                else:
                    for child in children:
                        st.markdown(f"### {child['username']}")
                        recent_scans = [scan for scan in get_all_scan_events() if scan["student_user_id"] == child["id"]]
                        if not recent_scans:
                            st.info("No scans available for this student yet.")
                        else:
                            st.dataframe(recent_scans[:5])

            elif current_user["role"] == "Student":
                st.subheader("Your status")
                st.write("Your account is connected to the school safety network.")
                st.write("If you scan in or out of campus, your parents and management will be notified.")
                qr_payload = f"student:{current_user['user_code']}"
                qr_url = f"https://chart.googleapis.com/chart?cht=qr&chs=250x250&chl={urllib.parse.quote(qr_payload)}"
                st.image(qr_url, caption="Your student QR code", use_column_width=False)
                st.code(qr_payload)
            else:
                st.info("Security tracking is reserved for Redemption Gate staff, parents, students, and management.")

    elif page == "Admin":
        st.title("Admin — Controls")
        if not st.session_state.user_id:
            st.error("Sign in as a Super Admin or School Management user to access this page.")
        else:
            current_user = fetch_user_by_id(st.session_state.user_id)
            if not current_user or current_user["role"] not in ["Super Admin", "School Management"]:
                st.error("Admin access required. Sign in as a Super Admin or School Management user.")
            else:
                can_manage_users = current_user["role"] == "Super Admin"
                st.subheader("User management")
                with st.expander("Add a new user"):
                    new_username = st.text_input("Username", key="new_user_username")
                    new_password = st.text_input("Password", type="password", key="new_user_password")
                    new_email = st.text_input("Email", key="new_user_email")
                    new_phone = st.text_input("Phone number", key="new_user_phone")
                    new_role = st.selectbox(
                        "Role",
                        ["Super Admin", "School Management", "Staff/Security", "Parent", "Student"],
                        key="new_user_role",
                    )
                    if st.button("Create user"):
                        if not new_username.strip() or not new_password:
                            st.error("Username and password are required.")
                        else:
                            user = create_user_with_email(
                                new_username.strip(),
                                new_password,
                                email=new_email.strip() if new_email else None,
                                phone=new_phone.strip() if new_phone else None,
                                role=new_role,
                                active=1,
                            )
                            if user is None:
                                st.error("Could not create user. The username, email, or phone may already be in use.")
                            else:
                                st.success(f"Created {user['username']} as {user['role']}.")

                with st.expander("Add parent-child relationship"):
                    parents = get_all_users_except_current(0)
                    parent_options = [u["username"] for u in parents if fetch_user_by_id(u["id"])["role"] == "Parent"]
                    student_options = [u["username"] for u in parents if fetch_user_by_id(u["id"])["role"] == "Student"]
                    parent_username = st.selectbox("Parent", [""] + parent_options, key="parent_select")
                    student_username = st.selectbox("Student", [""] + student_options, key="student_select")
                    if st.button("Link parent and student"):
                        if parent_username and student_username:
                            parent_user = fetch_user(parent_username)
                            student_user = fetch_user(student_username)
                            if parent_user and student_user:
                                create_parent_child_relation(parent_user["id"], student_user["id"])
                                st.success("Parent and student linked successfully.")
                            else:
                                st.error("Could not find the selected parent or student.")
                        else:
                            st.error("Select both a parent and a student.")

                st.markdown("---")
                st.subheader("School settings")
                zone = get_safe_zone()
                center_lat = st.number_input("Safe perimeter center latitude", value=zone["center_lat"], format="%.6f")
                center_lng = st.number_input("Safe perimeter center longitude", value=zone["center_lng"], format="%.6f")
                radius_m = st.number_input("Safe perimeter radius (meters)", value=float(zone["radius_meters"]), min_value=10.0)
                raw_cutoff = get_setting("pickup_cutoff")
                if raw_cutoff:
                    try:
                        pickup_cutoff = json.loads(raw_cutoff)
                    except Exception:
                        pickup_cutoff = raw_cutoff
                else:
                    pickup_cutoff = "15:00"
                pickup_cutoff = st.text_input("Pickup cutoff time (HH:MM)", value=pickup_cutoff)
                if st.button("Save school settings"):
                    update_safe_zone(center_lat, center_lng, radius_m)
                    set_setting("pickup_cutoff", pickup_cutoff)
                    st.success("School settings updated.")

                st.markdown("---")
                st.subheader("User directory")
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username, email, phone, role, active, created_at FROM users ORDER BY created_at"
                )
                rows = cursor.fetchall()
                conn.close()

                user_table = [
                    {
                        "id": r[0],
                        "username": r[1],
                        "email": r[2],
                        "phone": r[3],
                        "role": r[4],
                        "active": bool(r[5]),
                        "created_at": r[6],
                    }
                    for r in rows
                ]
                st.dataframe(user_table)

                if can_manage_users:
                    import csv
                    from io import StringIO

                    csv_buf = StringIO()
                    writer = csv.DictWriter(csv_buf, fieldnames=user_table[0].keys() if user_table else ["id", "username"])
                    if user_table:
                        writer.writeheader()
                        writer.writerows(user_table)
                    st.download_button("Download users CSV", csv_buf.getvalue(), file_name="users.csv", mime="text/csv")

                st.markdown("---")
                st.subheader("Security and scan reports")
                scan_events = get_all_scan_events()
                st.write(f"Total scanned gate events: {len(scan_events)}")
                st.dataframe(scan_events)

                geofence_events = get_geofence_events()
                st.write(f"Geofence alerts: {len(geofence_events)}")
                st.dataframe(geofence_events)

                late_pickups = get_late_pickups()
                st.write(f"Late pickup events: {len(late_pickups)}")
                st.dataframe(late_pickups)

                safety_events = get_safety_events()
                st.write(f"Safety events flagged: {len(safety_events)}")
                st.dataframe(safety_events)

                if st.button("Download scan report CSV"):
                    import csv
                    from io import StringIO

                    csv_buf = StringIO()
                    fieldnames = [
                        "id",
                        "student_user_id",
                        "student_username",
                        "scanner_id",
                        "scanner_username",
                        "event_type",
                        "location",
                        "latitude",
                        "longitude",
                        "notes",
                        "created_at",
                    ]
                    writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(scan_events)
                    st.download_button("Download scan report", csv_buf.getvalue(), file_name="scan_report.csv", mime="text/csv")

    else:
        st.title("Account")
        st.info("Only Redemption Gate staff, students, parents, and management may sign in. User accounts are created by administrators only.")
        with st.form("auth_form"):
            username = st.text_input("Username or email", key="auth_username")
            password = st.text_input("Password", type="password", key="auth_password")
            submitted = st.form_submit_button("Sign in")

            if submitted:
                if not username.strip() or not password:
                    st.error("Username/email and password are required.")
                else:
                    user = authenticate_user(username.strip(), password)
                    if user is None:
                        st.error("Invalid credentials or inactive account.")
                    else:
                        st.success("Sign in successful.")
                        st.session_state.username = user["username"]
                        st.session_state.user_id = user["id"]
                        st.session_state.email = user.get("email") or ""
                        st.session_state.role = user.get("role")
                        st.rerun()

        if st.session_state.auth_message:
            st.info(st.session_state.auth_message)

        with st.expander("Forgot password"):
            identifier = st.text_input("Enter your username or email to request a password reset")
            if st.button("Request password reset"):
                if not identifier.strip():
                    st.error("Enter a username or email.")
                else:
                    user = fetch_user(identifier.strip()) or fetch_user_by_email(identifier.strip())
                    if not user:
                        st.error("No account found for that username or email.")
                    else:
                        token = create_password_reset(user["id"])
                        try:
                            if user.get("email"):
                                send_reset_email(user.get("email"), token)
                                st.success("Password reset email sent. Check your inbox.")
                            else:
                                st.info("No email on record — password reset request recorded. Contact an administrator.")
                                try:
                                    with open("password_reset_tokens.log", "a", encoding="utf-8") as logf:
                                        logf.write(f"{datetime.datetime.utcnow().isoformat()} user_id={user['id']} username={user['username']} token={token}\n")
                                except Exception as log_exc:
                                    st.error(f"Could not record reset token on server: {log_exc}")
                        except Exception as exc:
                            st.warning("Password reset requested; email delivery failed. The request has been recorded for administrator handling.")
                            try:
                                with open("password_reset_tokens.log", "a", encoding="utf-8") as logf:
                                    logf.write(f"{datetime.datetime.utcnow().isoformat()} user_id={user['id']} username={user['username']} token={token} error={exc}\n")
                            except Exception as log_exc:
                                st.error(f"Could not record reset token on server: {log_exc}")

            st.markdown("---")
            st.write("If you already have a reset token, paste it below to set a new password.")
            token_input = st.text_input("Reset token")
            new_pw = st.text_input("New password", type="password")
            confirm_new_pw = st.text_input("Confirm new password", type="password")
            if st.button("Reset password"):
                if not token_input.strip() or not new_pw:
                    st.error("Token and new password are required.")
                elif new_pw != confirm_new_pw:
                    st.error("Passwords do not match.")
                else:
                    ok = reset_password(token_input.strip(), new_pw)
                    if ok:
                        st.success("Password reset successful. You can now log in.")
                    else:
                        st.error("Invalid or expired token.")


if __name__ == "__main__":
    main()

import base64
import datetime
import hashlib
import io
import os
import secrets
import sqlite3
from pathlib import Path
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
import openai
import streamlit as st

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

    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "password_hash" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if "salt" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN salt TEXT")
    if "email" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")

    # Table to store password reset tokens
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

    # Table to store user profiles
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
    cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(id=row[0], username=row[1], created_at=row[2]) if row else None


def fetch_user(username):
    """Fetch a user dict by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(id=row[0], username=row[1], created_at=row[2], password_hash=row[3], salt=row[4], email=row[5])
        if row
        else None
    )


def fetch_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, created_at, password_hash, salt, email FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()
    return (
        dict(id=row[0], username=row[1], created_at=row[2], password_hash=row[3], salt=row[4], email=row[5])
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


def create_user(username, password):
    return create_user_with_email(username, password, None)


def create_user_with_email(username, password, email=None):
    # prevent duplicate username or email
    if fetch_user(username) is not None:
        return None
    if email and fetch_user_by_email(email) is not None:
        return None
    salt, password_hash = hash_password(password)
    created_at = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, salt, email, created_at) VALUES (?, ?, ?, ?, ?)",
        (username, password_hash, salt, email, created_at),
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
    if verify_password(password, user.get("password_hash"), user.get("salt")):
        return user
    return None


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
    if get_posts() or get_resources():
        return

    staff = fetch_user("StudyBuddy")
    if staff is None:
        staff = create_user("StudyBuddy", "learning123")
    add_post(
        staff["id"],
        "Welcome to LearnerNet",
        "Share research notes, ask questions, and use the AI assistant to explore topics faster.",
    )
    add_resource(
        staff["id"],
        "Research Skills Guide",
        "https://www.coursera.org/learn/research-methods",
        "A beginner-friendly introduction to research techniques and academic learning.",
    )


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
        st.sidebar.info("Use the Auth page to sign in or register.")

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
            "Register/Login",
            "Admin",
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

    elif page == "Admin":
        st.title("Admin — Users")
        admin_env = os.getenv("ADMIN_USERNAMES", "admin,StudyBuddy")
        admin_usernames = [u.strip() for u in admin_env.split(",") if u.strip()]
        is_admin = (
            st.session_state.user_id
            and (
                st.session_state.username in admin_usernames
                or st.session_state.email in admin_usernames
            )
        )
        if not is_admin:
            st.error("Admin access required. Sign in as an admin user.")
        else:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, email, created_at, password_hash, salt FROM users ORDER BY created_at"
            )
            rows = cursor.fetchall()
            show_hashes = st.checkbox("Show password hashes and salts (sensitive)")
            show_tokens = st.checkbox("Show password reset tokens (sensitive)")
            import csv
            from io import StringIO

            table = []
            for r in rows:
                entry = {"id": r[0], "username": r[1], "email": r[2], "created_at": r[3]}
                if show_hashes:
                    entry["password_hash"] = r[4]
                    entry["salt"] = r[5]
                table.append(entry)

            st.dataframe(table)

            # provide CSV export
            csv_buf = StringIO()
            writer = csv.DictWriter(csv_buf, fieldnames=table[0].keys() if table else ["id", "username"])
            if table:
                writer.writeheader()
                writer.writerows(table)
            st.download_button("Download users CSV", csv_buf.getvalue(), file_name="users.csv", mime="text/csv")

            if show_tokens:
                try:
                    cursor.execute(
                        "SELECT pr.id, pr.user_id, u.username, pr.token, pr.expires_at, pr.used, pr.created_at FROM password_resets pr JOIN users u ON u.id = pr.user_id ORDER BY pr.created_at DESC"
                    )
                    token_rows = cursor.fetchall()
                    token_table = [
                        {
                            "id": tr[0],
                            "user_id": tr[1],
                            "username": tr[2],
                            "token": tr[3],
                            "expires_at": tr[4],
                            "used": bool(tr[5]),
                            "created_at": tr[6],
                        }
                        for tr in token_rows
                    ]
                    st.markdown("### Password Reset Tokens (sensitive)")
                    st.dataframe(token_table)
                except Exception as exc:
                    st.error(f"Could not load reset tokens: {exc}")

            conn.close()

    else:
        st.title("Account")
        auth_action = st.radio("What do you want to do?", ["Login", "Register"])
        with st.form("auth_form"):
            username = st.text_input("Username", key="auth_username")
            password = st.text_input("Password", type="password", key="auth_password")
            confirm_password = None
            email = None
            if auth_action == "Register":
                confirm_password = st.text_input(
                    "Confirm password",
                    type="password",
                    key="auth_confirm_password",
                )
                email = st.text_input("Email (optional)", key="auth_email")
            submitted = st.form_submit_button("Continue")

            if submitted:
                if not username.strip() or not password:
                    st.error("Username and password are required.")
                elif auth_action == "Register" and password != confirm_password:
                    st.error("Passwords do not match.")
                elif auth_action == "Register":
                    user = create_user_with_email(username.strip(), password, email.strip() if email and email.strip() else None)
                    if user is None:
                        st.error("That username or email is already taken.")
                    else:
                        st.success("Registration successful. You are now signed in.")
                        st.session_state.username = user["username"]
                        st.session_state.user_id = user["id"]
                        st.rerun()
                else:
                    user = authenticate_user(username.strip(), password)
                    if user is None:
                        st.error("Invalid username/email or password.")
                    else:
                        st.success("Sign in successful.")
                        st.session_state.username = user["username"]
                        st.session_state.user_id = user["id"]
                        st.session_state.email = user.get("email") or ""
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
                                # No email on record; record the token server-side for admin handling
                                st.info("No email on record — password reset request recorded. Contact an administrator.")
                                try:
                                    with open("password_reset_tokens.log", "a", encoding="utf-8") as logf:
                                        logf.write(f"{datetime.datetime.utcnow().isoformat()} user_id={user['id']} username={user['username']} token={token}\n")
                                except Exception as log_exc:
                                    st.error(f"Could not record reset token on server: {log_exc}")
                        except Exception as exc:
                            # Don't expose tokens in the frontend when email fails. Record server-side instead.
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

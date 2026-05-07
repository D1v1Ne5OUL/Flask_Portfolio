import sqlite3
import hashlib
import secrets
from contextlib import contextmanager

DATABASE = 'users.db'


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_auth_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')


def hash_password(password):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.sha256((password + salt).encode()).hexdigest()


def verify_password(password, stored_hash):
    try:
        salt, hash_value = stored_hash.split(':')
        return hash_value == hashlib.sha256((password + salt).encode()).hexdigest()
    except:
        return False


def register_user(username, email, password):
    with get_db() as conn:
        try:
            password_hash = hash_password(password)
            cursor = conn.execute(
                'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None


def authenticate_user(username, password):
    with get_db() as conn:
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?', (username,)
        ).fetchone()

        if user and verify_password(password, user['password_hash']):
            return dict(user)
    return None


def create_session(user_id):
    session_id = secrets.token_urlsafe(32)
    with get_db() as conn:
        conn.execute(
            'INSERT INTO sessions (session_id, user_id) VALUES (?, ?)',
            (session_id, user_id)
        )
    return session_id


def get_user_by_session(session_id):
    with get_db() as conn:
        session = conn.execute(
            'SELECT * FROM sessions WHERE session_id = ?', (session_id,)
        ).fetchone()
        if session:
            user = conn.execute(
                'SELECT * FROM users WHERE id = ?', (session['user_id'],)
            ).fetchone()
            return dict(user) if user else None
    return None


def update_session_activity(session_id):
    with get_db() as conn:
        conn.execute(
            'UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?',
            (session_id,)
        )


def delete_session(session_id):
    with get_db() as conn:
        conn.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))


def cleanup_expired_sessions(expiry_minutes=3):
    with get_db() as conn:
        conn.execute('''
            DELETE FROM sessions 
            WHERE julianday('now') - julianday(last_activity) > ?
        ''', (expiry_minutes / 1440.0,))
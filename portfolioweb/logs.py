import sqlite3
from contextlib import contextmanager

DATABASE = 'logs.db'


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_logs_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                login TEXT,
                action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT,
                result TEXT
            )
        ''')


def log_action(user_id, login, action, result):
    with get_db() as conn:
        conn.execute('''
            INSERT INTO logs (user_id, login, action, result)
            VALUES (?, ?, ?, ?)
        ''', (user_id, login, action, result))


def get_logs(limit=100):
    with get_db() as conn:
        return conn.execute(
            'SELECT * FROM logs ORDER BY action_date DESC LIMIT ?', (limit,)
        ).fetchall()
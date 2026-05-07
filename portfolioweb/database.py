import sqlite3
import json
from contextlib import contextmanager

DATABASE = 'portfolios.db'


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_portfolio_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                avatar TEXT,
                short_info TEXT,
                detailed_info TEXT,
                projects TEXT,
                social_links TEXT,
                skills TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS public_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                is_public BOOLEAN DEFAULT 1
            )
        ''')


def get_portfolio(user_id):
    with get_db() as conn:
        result = conn.execute(
            'SELECT * FROM portfolios WHERE user_id = ?', (user_id,)
        ).fetchone()
        return dict(result) if result else None


def save_portfolio(user_id, data):
    with get_db() as conn:
        projects_json = json.dumps(data.get('projects', []))
        social_links_json = json.dumps(data.get('social_links', {}))
        skills_json = json.dumps(data.get('skills', []))

        conn.execute('''
            INSERT OR REPLACE INTO portfolios 
            (user_id, full_name, avatar, short_info, detailed_info, projects, social_links, skills, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id,
            data.get('full_name', ''),
            data.get('avatar', '👤'),
            data.get('short_info', ''),
            data.get('detailed_info', ''),
            projects_json,
            social_links_json,
            skills_json
        ))

        # Добавляем в публичные профили
        conn.execute('''
            INSERT OR IGNORE INTO public_profiles (user_id, is_public)
            VALUES (?, 1)
        ''', (user_id,))


def get_all_public_portfolios():
    """Возвращает все публичные портфолио"""
    with get_db() as conn:
        results = conn.execute('''
            SELECT p.* FROM portfolios p
            INNER JOIN public_profiles pp ON p.user_id = pp.user_id
            WHERE pp.is_public = 1
            ORDER BY p.updated_at DESC
        ''').fetchall()
        
        portfolios = [dict(row) for row in results]
        print(f"[DEBUG] Найдено публичных портфолио: {len(portfolios)}")  # Для отладки
        return portfolios


def get_user_portfolio(user_id):
    with get_db() as conn:
        result = conn.execute(
            'SELECT * FROM portfolios WHERE user_id = ?', (user_id,)
        ).fetchone()
        return dict(result) if result else None
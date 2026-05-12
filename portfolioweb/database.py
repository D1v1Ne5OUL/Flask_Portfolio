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
        # Проверяем и пересоздаем таблицу с правильным PRIMARY KEY
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
                user_id INTEGER NOT NULL UNIQUE,
                is_public BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES portfolios(user_id)
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
        # Удаляем дубликаты из проектов
        projects_list = data.get('projects', [])
        if isinstance(projects_list, list):
            # Сохраняем порядок, но убираем дубликаты
            seen = set()
            unique_projects = []
            for project in projects_list:
                if project and project not in seen:
                    seen.add(project)
                    unique_projects.append(project)
            projects_list = unique_projects
        
        # Удаляем дубликаты из навыков
        skills_list = data.get('skills', [])
        if isinstance(skills_list, list):
            seen = set()
            unique_skills = []
            for skill in skills_list:
                if skill and skill not in seen:
                    seen.add(skill)
                    unique_skills.append(skill)
            skills_list = unique_skills
        
        projects_json = json.dumps(projects_list)
        social_links_json = json.dumps(data.get('social_links', {}))
        skills_json = json.dumps(skills_list)

        # Используем INSERT OR REPLACE для гарантии уникальности
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

        # Добавляем в публичные профили с проверкой на уникальность
        conn.execute('''
            INSERT OR IGNORE INTO public_profiles (user_id, is_public)
            VALUES (?, 1)
        ''', (user_id,))


def get_all_public_portfolios():
    """Возвращает все публичные портфолио без дубликатов"""
    with get_db() as conn:
        results = conn.execute('''
            SELECT DISTINCT p.* FROM portfolios p
            INNER JOIN public_profiles pp ON p.user_id = pp.user_id
            WHERE pp.is_public = 1
            ORDER BY p.updated_at DESC
        ''').fetchall()
        
        portfolios = []
        seen_users = set()
        
        for row in results:
            portfolio = dict(row)
            # Исключаем дубликаты по user_id
            if portfolio['user_id'] not in seen_users:
                seen_users.add(portfolio['user_id'])
                portfolios.append(portfolio)
        
        print(f"[DEBUG] Найдено уникальных публичных портфолио: {len(portfolios)}")
        return portfolios


def get_user_portfolio(user_id):
    with get_db() as conn:
        result = conn.execute(
            'SELECT * FROM portfolios WHERE user_id = ?', (user_id,)
        ).fetchone()
        return dict(result) if result else None


def cleanup_duplicate_portfolios():
    """Очистка дублирующихся записей в таблице portfolios"""
    with get_db() as conn:
        # Находим дубликаты
        duplicates = conn.execute('''
            SELECT user_id, COUNT(*) as count, MIN(rowid) as keep_id
            FROM portfolios
            GROUP BY user_id
            HAVING COUNT(*) > 1
        ''').fetchall()
        
        for dup in duplicates:
            user_id = dup['user_id']
            keep_id = dup['keep_id']
            
            # Удаляем все дубликаты, кроме первого
            conn.execute('''
                DELETE FROM portfolios 
                WHERE user_id = ? AND rowid != ?
            ''', (user_id, keep_id))
            
            print(f"[DEBUG] Очищены дубликаты для user_id={user_id}")
        
        return len(duplicates)


def recreate_portfolios_table():
    """Пересоздание таблицы portfolios для исправления структуры"""
    with get_db() as conn:
        # Переименовываем старую таблицу
        conn.execute('ALTER TABLE portfolios RENAME TO portfolios_old')
        
        # Создаем новую таблицу с правильной структурой
        conn.execute('''
            CREATE TABLE portfolios (
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
        
        # Копируем данные, оставляя только уникальные user_id
        conn.execute('''
            INSERT INTO portfolios (user_id, full_name, avatar, short_info, detailed_info, projects, social_links, skills, updated_at)
            SELECT user_id, full_name, avatar, short_info, detailed_info, projects, social_links, skills, MAX(updated_at)
            FROM portfolios_old
            GROUP BY user_id
        ''')
        
        # Удаляем старую таблицу
        conn.execute('DROP TABLE portfolios_old')
        
        print("[DEBUG] Таблица portfolios пересоздана, дубликаты удалены")
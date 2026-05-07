# add_users.py
import sqlite3
import json

# Подключаемся к БД пользователей
users_conn = sqlite3.connect('users.db')
users_cursor = users_conn.cursor()

# Создаем таблицу пользователей если её нет
users_cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Простая хэш-функция для паролей (для теста)
import hashlib
def simple_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Тестовые пользователи
test_users = [
    ('ivan', 'ivan@test.com', '123456', 'Иван Петров', '👨‍💻', 
     'Fullstack разработчик с 5-летним опытом',
     'Специализируюсь на React, Node.js и TypeScript. Работал в крупных IT-компаниях.',
     ['Интернет-магазин книг', 'CRM система для риелторов', 'Telegram бот'],
     ['Python', 'JavaScript', 'React', 'Node.js', 'PostgreSQL']),
    
    ('maria', 'maria@test.com', '123456', 'Мария Сидорова', '🎨',
     'UI/UX дизайнер с портфолио из 30+ проектов',
     'Создаю удобные и красивые интерфейсы для мобильных приложений и веб-сервисов.',
     ['Мобильное приложение для доставки', 'Лендинг для стартапа', 'Брендинг компании'],
     ['Figma', 'Adobe XD', 'Photoshop', 'Illustrator', 'User Research']),
    
    ('alex', 'alex@test.com', '123456', 'Алексей Смирнов', '🐍',
     'Backend разработчик на Python',
     'Разрабатываю высоконагруженные API и микросервисы. Работаю с Docker и Kubernetes.',
     ['API для маркетплейса', 'Система аналитики', 'Платформа для онлайн-курсов'],
     ['Python', 'Django', 'FastAPI', 'PostgreSQL', 'Docker', 'Redis'])
]

user_ids = []

print("="*60)
print("📝 Добавление тестовых пользователей...")
print("="*60)

for username, email, password, full_name, avatar, short_info, detailed_info, projects, skills in test_users:
    try:
        password_hash = simple_hash(password)
        users_cursor.execute('''
            INSERT INTO users (username, email, password_hash)
            VALUES (?, ?, ?)
        ''', (username, email, password_hash))
        user_id = users_cursor.lastrowid
        user_ids.append(user_id)
        print(f"✅ Создан пользователь: {username} / {password} (id={user_id})")
    except sqlite3.IntegrityError:
        # Пользователь уже существует, получаем его id
        users_cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        user_id = users_cursor.fetchone()[0]
        user_ids.append(user_id)
        print(f"⚠️ Пользователь {username} уже существует (id={user_id})")

users_conn.commit()
users_conn.close()

# Подключаемся к БД портфолио
portfolios_conn = sqlite3.connect('portfolios.db')
portfolios_cursor = portfolios_conn.cursor()

# Создаем таблицы если их нет
portfolios_cursor.execute('''
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

portfolios_cursor.execute('''
    CREATE TABLE IF NOT EXISTS public_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        is_public BOOLEAN DEFAULT 1
    )
''')

print("\n" + "="*60)
print("📁 Добавление портфолио...")
print("="*60)

# Данные портфолио для каждого пользователя
for i, user_data in enumerate(test_users):
    username, email, password, full_name, avatar, short_info, detailed_info, projects, skills = user_data
    user_id = user_ids[i]
    
    try:
        # Добавляем портфолио
        portfolios_cursor.execute('''
            INSERT OR REPLACE INTO portfolios 
            (user_id, full_name, avatar, short_info, detailed_info, projects, social_links, skills, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            user_id,
            full_name,
            avatar,
            short_info,
            detailed_info,
            json.dumps(projects),
            json.dumps({}),
            json.dumps(skills)
        ))
        
        # Добавляем в публичные профили
        portfolios_cursor.execute('''
            INSERT OR IGNORE INTO public_profiles (user_id, is_public)
            VALUES (?, 1)
        ''', (user_id,))
        
        print(f"✅ Добавлено портфолио для: {full_name}")
        print(f"   📌 Проекты: {', '.join(projects[:2])}...")
        print(f"   ⚡ Навыки: {', '.join(skills[:3])}...")
        print("-"*40)
        
    except Exception as e:
        print(f"❌ Ошибка для {full_name}: {e}")

portfolios_conn.commit()
portfolios_conn.close()

print("\n" + "="*60)
print("🎉 ГОТОВО! Теперь у вас есть:")
print("="*60)
print("\n📋 Данные для входа:")
for user_data in test_users:
    print(f"   • {user_data[0]} / {user_data[2]} - {user_data[3]}")
print("\n🔗 Перейдите на http://localhost:5000 и войдите под любым пользователем")
print("👥 На главной странице вы увидите портфолио ДРУГИХ пользователей")
print("="*60)
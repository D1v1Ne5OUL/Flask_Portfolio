from flask import Flask, render_template, request, redirect, url_for, session, abort, g
from functools import wraps
import os
import json

from auth import (
    init_auth_db, register_user, authenticate_user,
    create_session, get_user_by_session, update_session_activity,
    delete_session, cleanup_expired_sessions
)
from logs import init_logs_db, log_action
from database import (
    init_portfolio_db, get_portfolio, save_portfolio,
    get_all_public_portfolios, get_user_portfolio
)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['DEBUG'] = True  # Включаем режим отладки

# Инициализация всех БД
init_auth_db()
init_logs_db()
init_portfolio_db()


# Фильтр для Jinja2
@app.template_filter('from_json')
def from_json_filter(value):
    if not value:
        return []
    try:
        return json.loads(value)
    except:
        return []


@app.template_filter('from_json_dict')
def from_json_dict_filter(value):
    if not value:
        return {}
    try:
        return json.loads(value)
    except:
        return {}


# Декоратор проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('session_id')
        if not session_id:
            return redirect(url_for('login'))

        user = get_user_by_session(session_id)
        if not user:
            session.clear()
            return redirect(url_for('login'))

        update_session_activity(session_id)
        g.user = user
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    cleanup_expired_sessions(3)
    session_id = session.get('session_id')
    if session_id:
        user = get_user_by_session(session_id)
        if user:
            update_session_activity(session_id)
            g.user = user


# Ошибки
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = authenticate_user(username, password)
        if user:
            session_id = create_session(user['id'])
            session['session_id'] = session_id
            log_action(user['id'], username, 'LOGIN', 'SUCCESS')
            return redirect(url_for('index'))
        else:
            log_action(None, username, 'LOGIN', 'FAILED')
            return render_template('login.html', error='Неверное имя пользователя или пароль')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            return render_template('register.html', error='Все поля обязательны для заполнения')

        if password != confirm_password:
            return render_template('register.html', error='Пароли не совпадают')

        if len(password) < 4:
            return render_template('register.html', error='Пароль должен содержать минимум 4 символа')

        user_id = register_user(username, email, password)
        if user_id:
            log_action(user_id, username, 'REGISTER', 'SUCCESS')
            
            # Создаем портфолио для нового пользователя
            empty_portfolio = {
                'full_name': username,
                'avatar': '👤',
                'short_info': '',
                'detailed_info': '',
                'projects': [],
                'social_links': {},
                'skills': []
            }
            save_portfolio(user_id, empty_portfolio)
            
            return redirect(url_for('login'))
        else:
            return render_template('register.html', error='Пользователь с таким именем или email уже существует')

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    log_action(g.user['id'], g.user['username'], 'LOGOUT', 'SUCCESS')
    delete_session(session.get('session_id'))
    session.clear()
    return redirect(url_for('login'))


# Главная страница
@app.route('/')
@login_required
def index():
    # Получаем все публичные портфолио
    all_portfolios = get_all_public_portfolios()
    
    # Исключаем текущего пользователя (не показываем своё портфолио на главной)
    other_portfolios = [p for p in all_portfolios if p['user_id'] != g.user['id']]
    
    print(f"[DEBUG] Текущий пользователь: {g.user['username']} (id={g.user['id']})")
    print(f"[DEBUG] Всего публичных портфолио: {len(all_portfolios)}")
    print(f"[DEBUG] Портфолио других пользователей: {len(other_portfolios)}")
    
    # Пагинация
    page = request.args.get('page', 1, type=int)
    per_page = 9
    total = len(other_portfolios)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = other_portfolios[start:end]

    log_action(g.user['id'], g.user['username'], 'VIEW_HOMEPAGE', 'SUCCESS')

    return render_template('index.html',
                           portfolios=paginated,
                           page=page,
                           has_next=end < total,
                           has_prev=page > 1,
                           total_count=total)


# Редактирование портфолио
@app.route('/portfolio/edit', methods=['GET', 'POST'])
@login_required
def edit_portfolio():
    portfolio = get_portfolio(g.user['id']) or {}

    if request.method == 'POST':
        projects = request.form.getlist('projects[]')
        projects = [p for p in projects if p.strip()]

        skills = request.form.getlist('skills[]')
        skills = [s for s in skills if s.strip()]

        data = {
            'full_name': request.form.get('full_name', ''),
            'avatar': request.form.get('avatar', '👤'),
            'short_info': request.form.get('short_info', ''),
            'detailed_info': request.form.get('detailed_info', ''),
            'projects': projects,
            'social_links': {
                'github': request.form.get('github', ''),
                'linkedin': request.form.get('linkedin', ''),
                'telegram': request.form.get('telegram', '')
            },
            'skills': skills
        }

        save_portfolio(g.user['id'], data)
        log_action(g.user['id'], g.user['username'], 'EDIT_PORTFOLIO', 'SUCCESS')

        return redirect(url_for('view_my_portfolio'))

    return render_template('portfolio_edit.html', portfolio=portfolio)


# Просмотр своего портфолио
@app.route('/portfolio/my')
@login_required
def view_my_portfolio():
    portfolio = get_portfolio(g.user['id'])
    log_action(g.user['id'], g.user['username'], 'VIEW_MY_PORTFOLIO', 'SUCCESS')
    return render_template('portfolio_view.html', portfolio=portfolio, is_owner=True)


# Просмотр портфолио другого пользователя
@app.route('/portfolio/user/<int:user_id>')
@login_required
def view_user_portfolio(user_id):
    if user_id == g.user['id']:
        return redirect(url_for('view_my_portfolio'))

    portfolio = get_user_portfolio(user_id)
    if not portfolio:
        abort(404)

    log_action(g.user['id'], g.user['username'], f'VIEW_USER_{user_id}', 'SUCCESS')
    return render_template('user_view.html', portfolio=portfolio)


# Управление аккаунтом
@app.route('/account')
@login_required
def account():
    log_action(g.user['id'], g.user['username'], 'VIEW_ACCOUNT', 'SUCCESS')
    return render_template('account.html', user=g.user)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=443, ssl_context='adhoc')
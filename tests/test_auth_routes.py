"""认证路由测试 — 登录/注册/退出/暴力破解防护"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from models import db, User, Family, Category, AccountType, DEFAULT_CATEGORIES, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR


@pytest.fixture
def app():
    """提供包含 index 路由的测试 app（覆盖 conftest 的 app）"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    db_path = temp_db.name

    from flask import Flask
    application = Flask(__name__)
    application.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    application.config['SECRET_KEY'] = 'test-secret-key'
    application.config['TESTING'] = True
    application.static_folder = str(BASE_DIR / 'src' / 'static')
    application.template_folder = str(BASE_DIR / 'src' / 'templates')

    db.init_app(application)

    @application.template_filter('currency')
    def currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '0.00'
        return f'{value:,.{decimals}f}'

    @application.template_filter('signed_currency')
    def signed_currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '+0.00'
        formatted = f'{abs(value):,.{decimals}f}'
        return f'+{formatted}' if value >= 0 else f'-{formatted}'

    # 注册 dummy index 路由（auth 模块 url_for('index') 需要）
    @application.route('/')
    def index():
        return 'index page', 200

    # 注册蓝图
    from routes.auth import auth_bp
    from routes.account import account_bp
    from routes.category import category_bp
    from routes.savings import savings_bp
    from routes.baby_fund import baby_fund_bp
    from routes.upload import upload_bp
    from routes.family import family_bp
    from routes.transaction import transaction_bp
    from routes.reports import reports_bp

    application.register_blueprint(auth_bp)
    application.register_blueprint(account_bp)
    application.register_blueprint(category_bp)
    application.register_blueprint(savings_bp)
    application.register_blueprint(baby_fund_bp)
    application.register_blueprint(upload_bp)
    application.register_blueprint(family_bp)
    application.register_blueprint(transaction_bp)
    application.register_blueprint(reports_bp)

    from datetime import timedelta
    @application.context_processor
    def inject_timedelta():
        return {'timedelta': timedelta}

    with application.app_context():
        db.create_all()
        for cat_data in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=cat_data['name']).first():
                db.session.add(Category(**cat_data))
        for at_data in DEFAULT_ACCOUNT_TYPES:
            if not AccountType.query.filter_by(name=at_data['name']).first():
                db.session.add(AccountType(**at_data))
        db.session.commit()

    yield application
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """提供 Flask 测试客户端"""
    return app.test_client()


class TestLoginPage:
    """登录页面基础测试"""

    def test_login_page_returns_200(self, client):
        """登录页面正常访问"""
        resp = client.get('/auth/login')
        assert resp.status_code == 200

    def test_login_success_redirects(self, app, client):
        """正确凭证登录成功后重定向到首页"""
        with app.app_context():
            user = User(username='loginuser', nickname='登录用户')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()

        resp = client.post('/auth/login', data={
            'username': 'loginuser',
            'password': 'Test1234'
        }, follow_redirects=False)
        # 登录成功应重定向
        assert resp.status_code == 302

    def test_login_wrong_password_fails(self, app, client):
        """错误密码登录失败"""
        with app.app_context():
            user = User(username='wrongpw', nickname='密码错误')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()

        resp = client.post('/auth/login', data={
            'username': 'wrongpw',
            'password': 'WrongPass1'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '用户名或密码错误' in resp.data.decode('utf-8')

    def test_login_empty_fields_rejected(self, client):
        """空用户名或密码被拒绝"""
        resp = client.post('/auth/login', data={
            'username': '',
            'password': ''
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '不能为空' in resp.data.decode('utf-8')


class TestRegister:
    """注册路由测试"""

    def test_register_success(self, app, client):
        """注册新用户成功"""
        resp = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'NewPass123',
            'nickname': '新用户'
        }, follow_redirects=False)
        # 注册成功后应重定向到首页
        assert resp.status_code == 302

        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.nickname == '新用户'

    def test_register_duplicate_username_fails(self, app, client):
        """注册重复用户名失败"""
        with app.app_context():
            user = User(username='dupuser', nickname='已存在')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()

        resp = client.post('/auth/register', data={
            'username': 'dupuser',
            'password': 'AnotherPass1',
            'nickname': '重复'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '用户名已存在' in resp.data.decode('utf-8')

    def test_register_short_password_rejected(self, client):
        """密码少于8位被拒绝"""
        resp = client.post('/auth/register', data={
            'username': 'shortpw',
            'password': 'Sh1',
            'nickname': '短密码'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '不能少于8个字符' in resp.data.decode('utf-8')

    def test_register_password_no_digit_rejected(self, client):
        """密码不含数字被拒绝"""
        resp = client.post('/auth/register', data={
            'username': 'nodigit',
            'password': 'AllLetters',
            'nickname': '无数字'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '必须同时包含字母和数字' in resp.data.decode('utf-8')

    def test_register_password_no_letter_rejected(self, client):
        """密码不含字母被拒绝"""
        resp = client.post('/auth/register', data={
            'username': 'noletter',
            'password': '12345678',
            'nickname': '无字母'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '必须同时包含字母和数字' in resp.data.decode('utf-8')


class TestLogout:
    """退出路由测试"""

    def test_logout_clears_session(self, app, client):
        """退出清除 session"""
        # 先登录
        with app.app_context():
            user = User(username='logoutuser', nickname='退出测试')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

        # 手动设置 session 模拟已登录
        with client.session_transaction() as sess:
            sess['user_id'] = user_id
            sess['username'] = 'logoutuser'

        # 执行退出
        resp = client.get('/auth/logout', follow_redirects=False)
        assert resp.status_code == 302

        # 验证 session 已清除
        with client.session_transaction() as sess:
            assert 'user_id' not in sess
            assert 'username' not in sess


class TestBruteForceProtection:
    """暴力破解防护测试"""

    def test_lockout_after_5_failures(self, app, client):
        """5次失败后账号被锁定"""
        with app.app_context():
            user = User(username='bruteuser', nickname='暴力破解')
            user.set_password('CorrectPass1')
            db.session.add(user)
            db.session.commit()

        # 连续5次错误登录
        for i in range(5):
            resp = client.post('/auth/login', data={
                'username': 'bruteuser',
                'password': f'WrongPass{i}'
            }, follow_redirects=True)

        # 第5次应该触发锁定消息
        data = resp.data.decode('utf-8')
        assert '锁定' in data

        # 第6次尝试即使密码正确也应被锁定
        resp = client.post('/auth/login', data={
            'username': 'bruteuser',
            'password': 'CorrectPass1'
        }, follow_redirects=True)
        data = resp.data.decode('utf-8')
        assert '分钟后重试' in data

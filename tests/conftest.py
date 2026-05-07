"""pytest 全局 fixtures — 提供正确配置的 Flask 测试 app"""
import sys
import os
import tempfile

# 确保 src 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from flask import Flask
from models import db as _db, User, Family, Category, AccountType, DEFAULT_CATEGORIES, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR


def create_test_app(db_path=None):
    """创建正确配置的测试 Flask app（含 currency 过滤器和蓝图）"""
    if db_path is None:
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        db_path = temp_db.name

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['TESTING'] = True
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    _db.init_app(app)

    # 注册 Jinja2 自定义过滤器（与 database.py 一致）
    @app.template_filter('currency')
    def currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '0.00'
        return f'{value:,.{decimals}f}'

    @app.template_filter('signed_currency')
    def signed_currency_filter(value, decimals=2):
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '+0.00'
        formatted = f'{abs(value):,.{decimals}f}'
        return f'+{formatted}' if value >= 0 else f'-{formatted}'

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
    from routes.template import template_bp
    from routes.recurring import recurring_bp
    from routes.monthly_todo import monthly_todo_bp
    from routes.advisor import advisor_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(savings_bp)
    app.register_blueprint(baby_fund_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(family_bp)
    app.register_blueprint(transaction_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(template_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(monthly_todo_bp)
    app.register_blueprint(advisor_bp)

    # 注册 timedelta context processor（与 main.py 一致）
    from datetime import timedelta
    @app.context_processor
    def inject_timedelta():
        return {'timedelta': timedelta}

    # 注册 index 路由桩（模板中 url_for('index') 依赖）
    @app.route('/')
    def index():
        return 'index stub'

    return app, db_path


@pytest.fixture
def app():
    """提供配置完整的测试 app"""
    application, db_path = create_test_app()
    with application.app_context():
        _db.create_all()
        # 插入预设数据
        for cat_data in DEFAULT_CATEGORIES:
            if not Category.query.filter_by(name=cat_data['name']).first():
                _db.session.add(Category(**cat_data))
        for at_data in DEFAULT_ACCOUNT_TYPES:
            if not AccountType.query.filter_by(name=at_data['name']).first():
                _db.session.add(AccountType(**at_data))
        _db.session.commit()
    yield application
    # 清理
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """提供 Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def logged_in_client(app):
    """提供已登录的测试客户端"""
    with app.app_context():
        user = User(username='testuser', nickname='测试用户')
        user.set_password('Test1234')
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
    return client


@pytest.fixture
def family_client(app):
    """提供有家庭的已登录测试客户端"""
    with app.app_context():
        family = Family(name='测试家庭', invite_code='TESTCODE')
        _db.session.add(family)
        _db.session.flush()

        user = User(username='family_user', nickname='家庭成员', family_id=family.id)
        user.set_password('Test1234')
        _db.session.add(user)
        _db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
    return client

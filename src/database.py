from datetime import timedelta
from datetime import timedelta
from flask import Flask
from models import db, Category, DEFAULT_CATEGORIES, AccountType, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY


def _safe_add_column(table, column, col_type):
    """安全地给 SQLite 表添加列，忽略已存在的列"""
    try:
        db.session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
        db.session.commit()
    except Exception:
        db.session.rollback()


def init_database(app: Flask) -> None:
    """初始化数据库表和预设分类"""
    with app.app_context():
        # 创建所有表
        db.create_all()

        # SQLite 兼容：给已有表添加新列（create_all 不会 ALTER 已有表）
        _safe_add_column('fund_holdings', 'status', "VARCHAR(20) DEFAULT 'holding'")

        # 插入预设分类（仅当不存在时）
        for cat_data in DEFAULT_CATEGORIES:
            existing = Category.query.filter_by(name=cat_data['name']).first()
            if not existing:
                category = Category(**cat_data)
                db.session.add(category)

        # 插入预设账户类型（仅当不存在时）
        for at_data in DEFAULT_ACCOUNT_TYPES:
            existing = AccountType.query.filter_by(name=at_data['name']).first()
            if not existing:
                account_type = AccountType(**at_data)
                db.session.add(account_type)

        db.session.commit()
        print(f"数据库初始化完成: {SQLALCHEMY_DATABASE_URI}")
        print(f"预设分类: {len(DEFAULT_CATEGORIES)} 个")
        print(f"预设账户类型: {len(DEFAULT_ACCOUNT_TYPES)} 个")


def create_app() -> Flask:
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # 会话 24 小时过期

    # 初始化数据库
    db.init_app(app)

    # 注册 Jinja2 自定义过滤器
    @app.template_filter('currency')
    def currency_filter(value, decimals=2):
        """千分位逗号格式化金额，如 1020000 → 1,020,000.00"""
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '0.00'
        return f'{value:,.{decimals}f}'

    @app.template_filter('signed_currency')
    def signed_currency_filter(value, decimals=2):
        """带正负号的千分位金额，如 +1,234.56 或 -3,210.00"""
        try:
            value = float(value)
        except (ValueError, TypeError):
            return '+0.00'
        formatted = f'{abs(value):,.{decimals}f}'
        return f'+{formatted}' if value >= 0 else f'-{formatted}'

    # 静态文件和模板目录
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    return app

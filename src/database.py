from datetime import timedelta
from datetime import timedelta
from flask import Flask
from models import db, Category, DEFAULT_CATEGORIES, AccountType, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY, INSECURE_SECRET_KEY


def _safe_add_column(table, column, col_type):
    """安全地给 SQLite 表添加列，忽略已存在的列"""
    try:
        db.session.execute(db.text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
        db.session.commit()
    except Exception:
        db.session.rollback()


def _rename_account_type(old_name, new_name):
    """安全地重命名账户类型，忽略不存在的"""
    try:
        existing = AccountType.query.filter_by(name=old_name).first()
        if existing:
            existing.name = new_name
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
        _safe_add_column('transactions', 'transfer_pair_id', 'INTEGER')
        _safe_add_column('users', 'avatar_text', 'VARCHAR(4)')
        _safe_add_column('account_balance', 'source', "VARCHAR(20) DEFAULT 'snapshot'")
        _safe_add_column('accounts', 'group_id', 'INTEGER')

        # 移除 account_balance 的 unique constraint（允许同月多条转账记录）
        try:
            check = db.session.execute(db.text(
                "SELECT sql FROM sqlite_master WHERE tbl_name='account_balance' AND type='table'"
            )).fetchone()
            if check and 'uq_account_month' in (check[0] or ''):
                db.session.execute(db.text('''
                    CREATE TABLE account_balance_new (
                        id INTEGER NOT NULL PRIMARY KEY,
                        account_id INTEGER NOT NULL,
                        balance NUMERIC(10, 2) NOT NULL,
                        change_amount NUMERIC(10, 2),
                        record_month DATE NOT NULL,
                        note VARCHAR(200),
                        source VARCHAR(20) DEFAULT 'snapshot',
                        recorded_by INTEGER,
                        created_at DATETIME,
                        FOREIGN KEY(account_id) REFERENCES accounts (id),
                        FOREIGN KEY(recorded_by) REFERENCES users (id)
                    )
                '''))
                db.session.execute(db.text('''
                    INSERT INTO account_balance_new (id, account_id, balance, change_amount, record_month, note, source, recorded_by, created_at)
                    SELECT id, account_id, balance, change_amount, record_month, note, source, recorded_by, created_at
                    FROM account_balance
                '''))
                db.session.execute(db.text('DROP TABLE account_balance'))
                db.session.execute(db.text('ALTER TABLE account_balance_new RENAME TO account_balance'))
                db.session.commit()
        except Exception:
            db.session.rollback()

        # 账户类型名称迁移（v2.0.10+）
        _rename_account_type('微众', '微众理财')
        _rename_account_type('中金', '中金基金')

        # 删除旧的预设支出分类（v2.0.12+）
        for old_cat in ['餐饮', '交通']:
            cat = Category.query.filter_by(name=old_cat, is_default=True).first()
            if cat:
                db.session.delete(cat)

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
    # 安全闸：SECRET_KEY 缺失或仍为不安全默认值时，拒绝启动而非静默降级
    if not SECRET_KEY or SECRET_KEY == INSECURE_SECRET_KEY:
        raise RuntimeError(
            'SECRET_KEY 未设置或仍为不安全的默认值，拒绝启动。\n'
            '请在 .env 中设置一个随机密钥，生成方法：\n'
            '  python3 -c "import secrets; print(secrets.token_hex(32))"'
        )

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

    @app.template_filter('to_beijing')
    def to_beijing_filter(value, fmt='%H:%M'):
        """UTC 时间转北京时间（+8小时）"""
        if not value:
            return ''
        return (value + timedelta(hours=8)).strftime(fmt)

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

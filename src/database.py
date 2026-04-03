from datetime import timedelta
from datetime import timedelta
from flask import Flask
from models import db, Category, DEFAULT_CATEGORIES, AccountType, DEFAULT_ACCOUNT_TYPES
from config import BASE_DIR, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY


def init_database(app: Flask) -> None:
    """初始化数据库表和预设分类"""
    with app.app_context():
        # 创建所有表
        db.create_all()

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

    # 静态文件和模板目录
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    return app

"""宝宝基金模型和路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date
from flask import Flask
from models import db, User, Family, BabyFund, Transaction, Category, TransactionModification
from config import BASE_DIR


def _create_test_app():
    """创建测试用 Flask 应用（使用独立临时数据库）"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['TESTING'] = True
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    db.init_app(app)

    from routes.baby_fund import baby_fund_bp
    # 注册需要的蓝图（用于 url_for）
    from routes.auth import auth_bp
    from routes.category import category_bp
    from routes.reports import reports_bp
    from routes.account import account_bp
    from routes.savings import savings_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(savings_bp)
    app.register_blueprint(baby_fund_bp)

    # 模拟主应用的 index 路由（模板中 url_for('index') 需要）
    @app.route('/')
    def index():
        return 'ok'

    return app, temp_db.name


def test_baby_fund_creates_transaction():
    """测试创建宝宝基金时自动生成收入交易"""
    app, db_path = _create_test_app()

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='parent', nickname='家长')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'parent'

    resp = client.post('/baby-fund/add', data={
        'giver_name': '外婆', 'amount': '10000',
        'event_date': '2026-03-01', 'event_type': '生日',
        'notes': '生日红包'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        fund = BabyFund.query.first()
        assert fund is not None
        assert fund.giver_name == '外婆'
        assert fund.transaction_id is not None
        txn = Transaction.query.get(fund.transaction_id)
        assert txn is not None
        assert txn.type == 'income'
        assert float(txn.amount) == 10000.0

    print("✅ test_baby_fund_creates_transaction passed")
    os.unlink(db_path)


def test_baby_fund_delete_cascades():
    """测试删除宝宝基金时级联删除交易"""
    app, db_path = _create_test_app()

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='parent2', nickname='家长2')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'parent2'

    client.post('/baby-fund/add', data={
        'giver_name': '奶奶', 'amount': '8000',
        'event_date': '2026-01-28', 'event_type': '红包'
    })

    with app.app_context():
        fund = BabyFund.query.first()
        fund_id = fund.id
        txn_id = fund.transaction_id

    resp = client.post(f'/baby-fund/{fund_id}/delete', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        assert BabyFund.query.get(fund_id) is None
        assert Transaction.query.get(txn_id) is None

    print("✅ test_baby_fund_delete_cascades passed")
    os.unlink(db_path)


def test_baby_fund_edit_syncs_transaction():
    """测试编辑宝宝基金时同步更新关联交易"""
    app, db_path = _create_test_app()

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='editor', nickname='编辑者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'editor'

    client.post('/baby-fund/add', data={
        'giver_name': '姑姑', 'amount': '5000',
        'event_date': '2026-03-01', 'event_type': '红包'
    })

    with app.app_context():
        fund = BabyFund.query.first()
        fund_id = fund.id

    resp = client.post(f'/baby-fund/{fund_id}/edit', data={
        'giver_name': '姑妈', 'amount': '8000',
        'event_date': '2026-03-01', 'event_type': '生日'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        fund = BabyFund.query.get(fund_id)
        assert fund.giver_name == '姑妈'
        assert float(fund.amount) == 8000.0
        txn = Transaction.query.get(fund.transaction_id)
        assert float(txn.amount) == 8000.0

    print("✅ test_baby_fund_edit_syncs_transaction passed")
    os.unlink(db_path)


def test_baby_fund_invalid_event_type():
    """测试无效的事件类型被拒绝"""
    app, db_path = _create_test_app()

    with app.app_context():
        db.create_all()
        cat = Category(name='宝宝基金', type='income', is_default=True)
        db.session.add(cat)
        user = User(username='validator', nickname='校验者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    resp = client.post('/baby-fund/add', data={
        'giver_name': '测试', 'amount': '1000',
        'event_date': '2026-03-01', 'event_type': '无效类型'
    }, follow_redirects=True)

    with app.app_context():
        assert BabyFund.query.count() == 0

    print("✅ test_baby_fund_invalid_event_type passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_baby_fund_creates_transaction()
    test_baby_fund_delete_cascades()
    test_baby_fund_edit_syncs_transaction()
    test_baby_fund_invalid_event_type()

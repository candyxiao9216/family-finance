"""储蓄计划模型和路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date
from flask import Flask
from models import db, User, Family, SavingsPlan, SavingsRecord
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
    return app, temp_db.name


def test_savings_plan_model():
    """测试储蓄计划模型 CRUD"""
    app, db_path = _create_test_app()
    with app.app_context():
        db.create_all()

        user = User(username='test_saver', nickname='储蓄者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        plan = SavingsPlan(
            name='月度储蓄', type='monthly',
            target_amount=Decimal('50000'), year=2026, month=3,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()

        assert plan.id is not None
        assert plan.name == '月度储蓄'
        assert plan.type == 'monthly'
        d = plan.to_dict()
        assert d['target_amount'] == 50000.0
        assert d['year'] == 2026

        db.session.remove()
        db.drop_all()
    print("✅ test_savings_plan_model passed")
    os.unlink(db_path)


def test_savings_record_model():
    """测试储蓄记录模型"""
    app, db_path = _create_test_app()
    with app.app_context():
        db.create_all()

        user = User(username='test_rec', nickname='记录者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()

        plan = SavingsPlan(
            name='年度储蓄', type='annual',
            target_amount=Decimal('600000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()

        record = SavingsRecord(
            plan_id=plan.id, user_id=user.id,
            amount=Decimal('35000'), record_date=date(2026, 3, 15),
            description='3月储蓄'
        )
        db.session.add(record)
        db.session.commit()

        assert record.id is not None
        assert record.plan_id == plan.id
        d = record.to_dict()
        assert d['amount'] == 35000.0

        db.session.remove()
        db.drop_all()
    print("✅ test_savings_record_model passed")
    os.unlink(db_path)


def _create_route_test_app():
    """创建带路由的测试应用"""
    from routes.savings import savings_bp
    from routes.auth import auth_bp
    from routes.category import category_bp
    from routes.reports import reports_bp
    from routes.account import account_bp

    app, db_path = _create_test_app()
    app.register_blueprint(savings_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(account_bp)

    # 添加 index 路由占位（模板中用到 url_for('index')）
    @app.route('/')
    def index():
        return 'ok'

    return app, db_path


def test_savings_routes():
    """测试储蓄计划路由"""
    app, db_path = _create_route_test_app()

    with app.app_context():
        db.create_all()
        user = User(username='route_test', nickname='路由测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'route_test'

    resp = client.get('/savings/')
    assert resp.status_code == 200

    resp = client.post('/savings/plan/add', data={
        'name': '月度储蓄', 'type': 'monthly',
        'target_amount': '50000', 'year': '2026', 'month': '3'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        plan = SavingsPlan.query.first()
        assert plan is not None
        assert plan.name == '月度储蓄'
        plan_id = plan.id

    resp = client.post('/savings/record/add', data={
        'plan_id': str(plan_id), 'amount': '35000',
        'record_date': '2026-03-15', 'description': '3月储蓄'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        record = SavingsRecord.query.first()
        assert record is not None
        assert float(record.amount) == 35000.0
        db.session.remove()
        db.drop_all()

    print("✅ test_savings_routes passed")
    os.unlink(db_path)


def test_savings_progress_calculation():
    """测试进度计算逻辑"""
    app, db_path = _create_route_test_app()

    with app.app_context():
        db.create_all()
        user = User(username='progress_test', nickname='进度测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        plan = SavingsPlan(
            name='进度测试', type='annual',
            target_amount=Decimal('100000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()
        plan_id = plan.id

        for amt in ['30000', '40000']:
            r = SavingsRecord(
                plan_id=plan.id, user_id=user.id,
                amount=Decimal(amt), record_date=date(2026, 3, 1)
            )
            db.session.add(r)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['username'] = 'progress_test'

    resp = client.get('/savings/')
    assert resp.status_code == 200
    assert b'70' in resp.data

    with app.app_context():
        r = SavingsRecord(
            plan_id=plan_id, user_id=user_id,
            amount=Decimal('50000'), record_date=date(2026, 3, 2)
        )
        db.session.add(r)
        db.session.commit()

    resp = client.get('/savings/')
    assert b'100' in resp.data

    with app.app_context():
        db.session.remove()
        db.drop_all()
    print("✅ test_savings_progress_calculation passed")
    os.unlink(db_path)


def test_savings_edit_plan():
    """测试编辑储蓄计划"""
    app, db_path = _create_route_test_app()

    with app.app_context():
        db.create_all()
        user = User(username='edit_test', nickname='编辑测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        plan = SavingsPlan(
            name='旧名称', type='annual',
            target_amount=Decimal('100000'), year=2026,
            created_by=user.id
        )
        db.session.add(plan)
        db.session.commit()
        plan_id = plan.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    resp = client.post(f'/savings/plan/{plan_id}/edit', data={
        'name': '新名称', 'target_amount': '200000'
    }, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        plan = SavingsPlan.query.get(plan_id)
        assert plan.name == '新名称'
        assert float(plan.target_amount) == 200000.0
        db.session.remove()
        db.drop_all()

    print("✅ test_savings_edit_plan passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_savings_plan_model()
    test_savings_record_model()
    test_savings_routes()
    test_savings_progress_calculation()
    test_savings_edit_plan()

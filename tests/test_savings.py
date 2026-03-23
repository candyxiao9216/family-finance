"""储蓄计划模型和路由测试"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date
from models import db, User, Family, SavingsPlan, SavingsRecord
from database import create_app


def _create_test_app():
    """创建测试用 Flask 应用"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['TESTING'] = True
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

        # 创建月度计划
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
        print("✅ test_savings_record_model passed")

    os.unlink(db_path)


if __name__ == '__main__':
    test_savings_plan_model()
    test_savings_record_model()

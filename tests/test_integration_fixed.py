"""
Family 模型集成测试（修复版）
验证 Family 与 User 的完整集成
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from models import db, User, Family, Transaction, Category
from database import create_app


def test_family_user_integration():
    """测试 Family 与 User 的集成"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        # 创建数据库表
        db.create_all()

        # 创建家庭
        family = Family(name="张氏家庭", invite_code="ZHANG001")
        db.session.add(family)
        db.session.commit()

        # 创建家庭成员
        user1 = User(username="zhang_san", nickname="张三")
        user1.set_password("password123")
        user1.family_id = family.id

        user2 = User(username="li_si", nickname="李四")
        user2.set_password("password456")
        user2.family_id = family.id

        db.session.add_all([user1, user2])
        db.session.commit()

        # 重新查询以刷新关系
        family = Family.query.get(family.id)
        user1 = User.query.get(user1.id)
        user2 = User.query.get(user2.id)

        # 验证家庭关系
        assert len(family.members) == 2
        assert family.members[0].username == "zhang_san"
        assert family.members[1].username == "li_si"

        # 验证用户信息
        assert user1.family.name == "张氏家庭"
        assert user2.family.invite_code == "ZHANG001"

        # 测试 to_dict 方法
        family_dict = family.to_dict()
        assert family_dict['name'] == "张氏家庭"
        assert family_dict['member_count'] == 2

        user1_dict = user1.to_dict()
        assert user1_dict['family_id'] == family.id
        assert user1_dict['family_name'] == "张氏家庭"

        print("✅ Family-User 集成测试通过！")


def test_family_transaction_integration():
    """测试 Family 与 Transaction 的集成"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # 创建家庭和用户
        family = Family(name="测试家庭", invite_code="TEST001")
        db.session.add(family)

        user = User(username="test_user", nickname="测试用户")
        user.set_password("testpass")
        user.family_id = family.id

        # 创建预设分类
        category = Category(name="工资", type="income", is_default=True)
        db.session.add(category)

        db.session.add(user)
        db.session.commit()

        # 重新查询以获取正确的ID
        user = User.query.filter_by(username="test_user").first()
        category = Category.query.filter_by(name="工资").first()

        # 创建交易记录
        transaction = Transaction(
            amount=5000.00,
            type="income",
            category_id=category.id,
            user_id=user.id,
            description="月度工资",
            transaction_date=datetime.now().date()
        )
        db.session.add(transaction)
        db.session.commit()

        # 重新查询以刷新关系
        transaction = Transaction.query.first()
        user = User.query.get(user.id)
        family = Family.query.get(family.id)

        # 验证关系
        assert transaction.user.family == family
        assert user.transactions[0].amount == 5000.00
        assert family.members[0].transactions[0].description == "月度工资"

        print("✅ Family-Transaction 集成测试通过！")


if __name__ == "__main__":
    test_family_user_integration()
    test_family_transaction_integration()
    print("🎉 所有集成测试通过！")
"""
Family 模型测试用例
"""
import pytest
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from models import db, User, Family
from database import create_app


class TestFamilyModel:
    """Family 模型测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    def test_family_creation(self, app):
        """测试 Family 模型创建"""
        with app.app_context():
            # 创建家庭
            family = Family(
                name="测试家庭",
                invite_code="TEST123"
            )
            db.session.add(family)
            db.session.commit()

            # 验证字段
            assert family.id is not None
            assert family.name == "测试家庭"
            assert family.invite_code == "TEST123"
            assert isinstance(family.created_at, datetime)

    def test_family_user_relationship(self, app):
        """测试 Family 与 User 的关系"""
        with app.app_context():
            # 创建家庭
            family = Family(name="家庭A", invite_code="FAM001")
            db.session.add(family)

            # 创建用户并关联到家庭
            user1 = User(username="user1", nickname="用户1")
            user1.set_password("password123")
            user1.family = family

            user2 = User(username="user2", nickname="用户2")
            user2.set_password("password456")
            user2.family = family

            db.session.add_all([user1, user2])
            db.session.commit()

            # 验证关系
            assert len(family.members) == 2
            assert user1 in family.members
            assert user2 in family.members
            assert user1.family_id == family.id
            assert user2.family_id == family.id

    def test_family_to_dict(self, app):
        """测试 Family 的 to_dict 方法"""
        with app.app_context():
            family = Family(
                name="我的家庭",
                invite_code="MYFAMILY"
            )
            db.session.add(family)
            db.session.commit()

            family_dict = family.to_dict()

            assert family_dict['id'] == family.id
            assert family_dict['name'] == "我的家庭"
            assert family_dict['invite_code'] == "MYFAMILY"
            assert 'created_at' in family_dict

    def test_family_unique_constraints(self, app):
        """测试 Family 的唯一约束"""
        with app.app_context():
            # 创建第一个家庭
            family1 = Family(name="家庭1", invite_code="UNIQUE1")
            db.session.add(family1)
            db.session.commit()

            # 尝试创建重复邀请码的家庭
            family2 = Family(name="家庭2", invite_code="UNIQUE1")
            db.session.add(family2)

            # 应该抛出唯一约束异常
            with pytest.raises(Exception):
                db.session.commit()

    def test_family_string_representation(self, app):
        """测试 Family 的字符串表示"""
        with app.app_context():
            family = Family(name="测试家庭", invite_code="TESTCODE")
            db.session.add(family)
            db.session.commit()

            assert str(family) == f"<Family {family.id}: 测试家庭>"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
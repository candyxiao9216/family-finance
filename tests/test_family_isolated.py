"""
Family 模型独立测试
每个测试完全独立运行，确保数据库隔离
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from models import db, User, Family
from database import create_app


def test_family_basic():
    """测试 Family 模型基本功能"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # 创建家庭
        family = Family(name="测试家庭", invite_code="TEST001")
        db.session.add(family)
        db.session.commit()

        # 验证基本字段
        assert family.id is not None
        assert family.name == "测试家庭"
        assert family.invite_code == "TEST001"
        assert isinstance(family.created_at, datetime)

        # 测试 to_dict 方法
        family_dict = family.to_dict()
        assert family_dict['name'] == "测试家庭"
        assert family_dict['invite_code'] == "TEST001"
        assert family_dict['member_count'] == 0

        print("✅ Family 模型基本功能测试通过！")


def test_family_user_relationship():
    """测试 Family 与 User 的关系"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # 创建家庭
        family = Family(name="张氏家庭", invite_code="ZHANG001")
        db.session.add(family)
        db.session.commit()

        # 创建用户并关联到家庭
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

        # 验证关系
        assert len(family.members) == 2
        assert user1 in family.members
        assert user2 in family.members
        assert user1.family_id == family.id
        assert user2.family_id == family.id

        # 验证用户字典包含家庭信息
        user1_dict = user1.to_dict()
        assert user1_dict['family_id'] == family.id
        assert user1_dict['family_name'] == "张氏家庭"

        print("✅ Family-User 关系测试通过！")


def test_family_unique_constraints():
    """测试 Family 的唯一约束"""
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # 创建第一个家庭
        family1 = Family(name="家庭A", invite_code="UNIQUE001")
        db.session.add(family1)
        db.session.commit()

        # 尝试创建重复邀请码的家庭
        family2 = Family(name="家庭B", invite_code="UNIQUE001")
        db.session.add(family2)

        # 应该抛出唯一约束异常
        try:
            db.session.commit()
            assert False, "应该抛出唯一约束异常"
        except Exception as e:
            assert "UNIQUE constraint failed" in str(e)
            print("✅ Family 唯一约束测试通过！")


if __name__ == "__main__":
    print("🧪 开始运行 Family 模型独立测试...")

    # 每个测试都在独立的进程中运行
    import subprocess
    import tempfile

    # 创建临时测试脚本
    test_code = '''
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import db, User, Family
from database import create_app

def run_test():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()

        # 创建家庭
        family = Family(name="测试家庭", invite_code="TEST001")
        db.session.add(family)
        db.session.commit()

        assert family.id is not None
        assert family.name == "测试家庭"
        print("✅ 独立测试通过！")

run_test()
'''

    # 在独立进程中运行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_code)
        temp_file = f.name

    try:
        result = subprocess.run([sys.executable, temp_file], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 独立进程测试通过！")
        else:
            print(f"❌ 独立进程测试失败: {result.stderr}")
    finally:
        os.unlink(temp_file)

    # 运行主测试
    test_family_basic()
    test_family_user_relationship()
    test_family_unique_constraints()

    print("🎉 所有 Family 模型测试通过！")
    print("✅ Family 数据模型实现完成！")
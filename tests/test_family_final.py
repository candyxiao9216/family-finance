"""
Family 模型最终测试
直接验证模型功能，不涉及复杂的测试框架
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from models import db, User, Family
from database import create_app


def test_family_model():
    """测试 Family 模型基本功能"""
    print("🧪 开始测试 Family 模型...")

    # 创建应用实例
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        # 创建数据库表
        db.create_all()

        # 测试1: 创建 Family 实例
        family = Family(name="测试家庭", invite_code="TEST001")
        db.session.add(family)
        db.session.commit()

        # 验证基本字段
        assert family.id is not None, "Family ID 应该不为空"
        assert family.name == "测试家庭", "Family 名称应该正确"
        assert family.invite_code == "TEST001", "邀请码应该正确"
        assert isinstance(family.created_at, datetime), "创建时间应该是 datetime 类型"

        print("✅ Family 模型创建测试通过")

        # 测试2: 测试 to_dict 方法
        family_dict = family.to_dict()
        assert family_dict['name'] == "测试家庭", "字典中名称应该正确"
        assert family_dict['invite_code'] == "TEST001", "字典中邀请码应该正确"
        assert family_dict['member_count'] == 0, "初始成员数应该为0"

        print("✅ Family to_dict 方法测试通过")

        # 测试3: 测试 Family-User 关系
        user = User(username="test_user", nickname="测试用户")
        user.set_password("password123")
        user.family_id = family.id
        db.session.add(user)
        db.session.commit()

        # 重新查询以刷新关系
        family = Family.query.get(family.id)
        user = User.query.get(user.id)

        # 验证关系
        assert len(family.members) == 1, "家庭成员数量应该为1"
        assert user in family.members, "用户应该在家庭成员中"
        assert user.family_id == family.id, "用户的家庭ID应该正确"

        print("✅ Family-User 关系测试通过")

        # 测试4: 测试唯一约束
        try:
            # 尝试创建重复邀请码的家庭
            family2 = Family(name="另一个家庭", invite_code="TEST001")
            db.session.add(family2)
            db.session.commit()
            assert False, "应该抛出唯一约束异常"
        except Exception as e:
            assert "UNIQUE constraint failed" in str(e), "应该捕获唯一约束异常"
            print("✅ Family 唯一约束测试通过")

        # 回滚事务
        db.session.rollback()

        print("🎉 所有 Family 模型测试通过！")
        return True


if __name__ == "__main__":
    try:
        success = test_family_model()
        if success:
            print("\n✅ Family 数据模型实现完成！")
            print("\n📋 实现的功能：")
            print("  • Family 模型基本字段 (id, name, invite_code, created_at)")
            print("  • Family-User 一对多关系")
            print("  • to_dict() 方法")
            print("  • invite_code 唯一约束")
            print("  • 完整的数据库关系映射")
        else:
            print("❌ 测试失败")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
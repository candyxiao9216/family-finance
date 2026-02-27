"""
User-Family 关联功能测试
验证 User 模型与 Family 模型的一对多关系
"""
import sys
import os
import tempfile

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from models import db, User, Family
from database import create_app


def test_user_family_association():
    """测试 User 与 Family 的关联功能"""
    print("🧪 开始测试 User-Family 关联功能...")

    # 创建临时数据库文件
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()

    try:
        # 创建完全独立的应用实例
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
        app.config['TESTING'] = True

        with app.app_context():
            # 创建数据库表
            db.create_all()

            # 测试1: 创建用户和家庭并建立关联
            print("📝 测试1: 用户与家庭关联创建")

            # 创建家庭（使用随机 invite_code 避免冲突）
            import random
            import string
            random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            family = Family(name="测试家庭", invite_code=f"TEST_{random_code}")
            db.session.add(family)
            db.session.commit()

            # 创建用户并关联到家庭
            user = User(username="test_user", nickname="测试用户")
            user.set_password("password123")
            user.family_id = family.id
            db.session.add(user)
            db.session.commit()

            # 验证关联关系
            assert user.family_id == family.id, "用户应该关联到正确的家庭"
            assert user.family == family, "用户应该能通过关系访问家庭"
            print("✅ 用户与家庭关联创建测试通过")

            # 测试2: 验证家庭能访问成员
            print("📝 测试2: 家庭访问成员")

            # 重新查询以刷新关系
            family = Family.query.get(family.id)
            user = User.query.get(user.id)

            assert len(family.members) == 1, "家庭应该有一个成员"
            assert user in family.members, "用户应该在家庭成员列表中"
            print("✅ 家庭访问成员测试通过")

            # 测试3: 验证 to_dict() 方法包含家庭信息
            print("📝 测试3: to_dict() 方法包含家庭信息")

            user_dict = user.to_dict()
            assert user_dict['family_id'] == family.id, "用户字典应包含家庭ID"
            assert user_dict['family_name'] == "测试家庭", "用户字典应包含家庭名称"
            print("✅ to_dict() 方法测试通过")

            # 测试4: 测试用户没有家庭关联的情况
            print("📝 测试4: 用户无家庭关联")

            user2 = User(username="lonely_user", nickname="独立用户")
            user2.set_password("password456")
            user2.family_id = None  # 明确设置为 None
            db.session.add(user2)
            db.session.commit()

            user2_dict = user2.to_dict()
            assert user2_dict['family_id'] is None, "独立用户应无家庭ID"
            assert user2_dict['family_name'] is None, "独立用户应无家庭名称"
            print("✅ 用户无家庭关联测试通过")

            # 测试5: 测试多个用户关联到同一个家庭
            print("📝 测试5: 多个用户关联到同一家庭")

            user3 = User(username="family_member2", nickname="家庭成员2")
            user3.set_password("password789")
            user3.family_id = family.id
            db.session.add(user3)
            db.session.commit()

            # 重新查询家庭
            family = Family.query.get(family.id)
            assert len(family.members) == 2, "家庭应该有两个成员"

            member_usernames = [member.username for member in family.members]
            assert "test_user" in member_usernames, "第一个用户应该在家庭成员中"
            assert "family_member2" in member_usernames, "第二个用户应该在家庭成员中"
            print("✅ 多个用户关联到同一家庭测试通过")

            # 测试6: 验证家庭字典包含成员数量
            print("📝 测试6: 家庭字典包含成员数量")

            family_dict = family.to_dict()
            assert family_dict['member_count'] == 2, "家庭字典应正确显示成员数量"
            print("✅ 家庭字典成员数量测试通过")

            print("\n🎉 所有 User-Family 关联测试通过！")
            print("\n📋 验证的功能：")
            print("  • User 模型的 family_id 外键字段")
            print("  • User-Family 一对多关系映射")
            print("  • User.to_dict() 包含家庭信息")
            print("  • Family.to_dict() 包含成员数量")
            print("  • 向后兼容性（用户可无家庭关联）")
            print("  • 多用户关联同一家庭")

            return True

    finally:
        # 清理临时文件
        if os.path.exists(temp_db.name):
            os.unlink(temp_db.name)


if __name__ == "__main__":
    try:
        success = test_user_family_association()
        if success:
            print("\n✅ User-Family 关联功能实现完成！")
        else:
            print("❌ 测试失败")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
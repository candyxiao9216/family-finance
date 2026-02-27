"""
验证 Family 模型集成
确认 Family 模型已正确集成到系统中
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from models import db, User, Family, Transaction, Category
from database import create_app


def verify_family_integration():
    """验证 Family 模型集成"""
    print("🔍 验证 Family 模型集成...")

    # 创建应用实例
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    with app.app_context():
        # 创建数据库表
        db.create_all()

        # 验证1: 检查 Family 模型是否可导入
        print("✅ Family 模型可正常导入")

        # 验证2: 检查 Family 表结构
        family = Family(name="验证家庭", invite_code="VERIFY001")
        db.session.add(family)
        db.session.commit()

        assert family.id is not None, "Family ID 应该不为空"
        print("✅ Family 表结构正常")

        # 验证3: 检查 Family-User 关系
        user = User(username="verify_user", nickname="验证用户")
        user.set_password("password123")
        user.family_id = family.id
        db.session.add(user)
        db.session.commit()

        # 重新查询以刷新关系
        family = Family.query.get(family.id)
        user = User.query.get(user.id)

        assert len(family.members) == 1, "家庭成员关系正常"
        assert user.family_id == family.id, "用户家庭关系正常"
        print("✅ Family-User 关系正常")

        # 验证4: 检查主应用导入
        try:
            from main import app
            print("✅ 主应用导入正常")
        except ImportError as e:
            print(f"❌ 主应用导入失败: {e}")
            return False

        # 验证5: 检查模型完整性
        assert hasattr(Family, 'name'), "Family 模型缺少 name 字段"
        assert hasattr(Family, 'invite_code'), "Family 模型缺少 invite_code 字段"
        assert hasattr(Family, 'created_at'), "Family 模型缺少 created_at 字段"
        assert hasattr(Family, 'members'), "Family 模型缺少 members 关系"
        assert hasattr(Family, 'to_dict'), "Family 模型缺少 to_dict 方法"
        print("✅ Family 模型完整性检查通过")

        # 验证6: 检查 User 模型更新
        assert hasattr(User, 'family_id'), "User 模型缺少 family_id 字段"
        assert hasattr(User, 'family'), "User 模型缺少 family 关系"
        print("✅ User 模型更新检查通过")

        print("\n🎉 Family 模型集成验证完成！")
        print("\n📊 验证结果：")
        print("  ✅ Family 模型可正常导入和使用")
        print("  ✅ Family 表结构完整")
        print("  ✅ Family-User 关系正常")
        print("  ✅ 主应用导入正常")
        print("  ✅ 模型完整性检查通过")
        print("  ✅ User 模型更新检查通过")

        return True


if __name__ == "__main__":
    try:
        success = verify_family_integration()
        if success:
            print("\n✅ Family 数据模型集成成功！")
            print("\n📋 下一步：")
            print("  1. 创建家庭管理相关路由和视图")
            print("  2. 实现家庭邀请功能")
            print("  3. 添加家庭共享数据权限控制")
        else:
            print("❌ 集成验证失败")
    except Exception as e:
        print(f"❌ 验证过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
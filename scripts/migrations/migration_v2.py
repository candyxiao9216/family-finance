#!/usr/bin/env python3
"""
第二阶段数据迁移脚本
为现有数据库添加用户关联支持
"""

import os
import sys
from pathlib import Path

# 添加项目路径到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import create_app
from src.models import User, Category, Transaction
from src.config import SQLALCHEMY_DATABASE_URI
from werkzeug.security import generate_password_hash

# 直接使用数据库实例
from src.models import db


def migrate_to_v2():
    """第二阶段数据迁移：添加用户关联"""
    app = create_app()

    with app.app_context():
        print("开始第二阶段数据迁移...")

        # 1. 创建 users 表（如果不存在）
        print("1. 创建 users 表...")
        db.create_all()

        # 2. 检查是否需要添加 user_id 列到 transactions 表
        print("2. 检查 transactions 表结构...")

        # 检查 transactions 表是否有 user_id 列
        result = db.session.execute("PRAGMA table_info(transactions)")
        columns = [row[1] for row in result]

        if 'user_id' not in columns:
            print("  添加 user_id 列到 transactions 表...")
            db.session.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)")

        # 3. 检查 categories 表是否有 user_id 和 is_default 列
        print("3. 检查 categories 表结构...")

        result = db.session.execute("PRAGMA table_info(categories)")
        columns = [row[1] for row in result]

        if 'user_id' not in columns:
            print("  添加 user_id 列到 categories 表...")
            db.session.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER REFERENCES users(id)")

        if 'is_default' not in columns:
            print("  添加 is_default 列到 categories 表...")
            db.session.execute("ALTER TABLE categories ADD COLUMN is_default BOOLEAN DEFAULT 0")

        # 4. 创建默认用户（admin）
        print("4. 创建默认用户...")
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(username='admin', nickname='管理员')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("   创建默认用户: admin/admin123")

        # 5. 为现有分类标记为系统预设
        print("5. 更新现有分类...")
        categories = Category.query.all()
        for category in categories:
            if category.user_id is None:
                category.user_id = None  # 保持为 NULL，表示系统预设
                category.is_default = True

        # 6. 为现有交易关联默认用户
        print("6. 更新现有交易...")
        transactions = Transaction.query.all()
        for transaction in transactions:
            if transaction.user_id is None:
                transaction.user_id = admin_user.id

        db.session.commit()

        print(f"迁移完成:")
        print(f"  - 用户: {User.query.count()} 个")
        print(f"  - 分类: {Category.query.count()} 个")
        print(f"  - 交易: {Transaction.query.count()} 条")
        print(f"  - 默认用户: admin/admin123")


if __name__ == '__main__':
    try:
        migrate_to_v2()
        print("\n✅ 数据迁移成功完成！")
    except Exception as e:
        print(f"\n❌ 数据迁移失败: {e}")
        import traceback
        traceback.print_exc()
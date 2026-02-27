#!/usr/bin/env python3
"""
第二阶段数据迁移脚本（简化版）
直接使用 SQLite 命令进行表结构迁移
"""

import sqlite3
import hashlib
import secrets
from pathlib import Path

def generate_password_hash(password):
    """生成密码哈希（兼容版本）"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2:sha256:100000${salt}${password_hash.hex()}"


def migrate_to_v2_simple():
    """第二阶段数据迁移：直接使用 SQLite"""

    # 数据库文件路径
    db_path = Path(__file__).parent.parent / "data" / "family_finance.db"

    if not db_path.exists():
        print(f"❌ 数据库文件不存在: {db_path}")
        return False

    print(f"开始第二阶段数据迁移...")
    print(f"数据库文件: {db_path}")

    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 1. 检查并创建 users 表
        print("1. 检查并创建 users 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nickname TEXT,
                role TEXT DEFAULT 'member',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. 检查并添加 user_id 列到 transactions 表
        print("2. 检查并添加 user_id 列到 transactions 表...")
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'user_id' not in columns:
            print("   添加 user_id 列...")
            cursor.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)")

        # 3. 检查并添加 user_id 和 is_default 列到 categories 表
        print("3. 检查并添加 user_id 和 is_default 列到 categories 表...")
        cursor.execute("PRAGMA table_info(categories)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'user_id' not in columns:
            print("   添加 user_id 列...")
            cursor.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER REFERENCES users(id)")

        if 'is_default' not in columns:
            print("   添加 is_default 列...")
            cursor.execute("ALTER TABLE categories ADD COLUMN is_default BOOLEAN DEFAULT 0")

        # 4. 创建默认用户
        print("4. 创建默认用户...")
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_exists = cursor.fetchone()

        if not admin_exists:
            password_hash = generate_password_hash('admin123')
            cursor.execute("""
                INSERT INTO users (username, password_hash, nickname, role)
                VALUES ('admin', ?, '管理员', 'admin')
            """, (password_hash,))
            print("   创建默认用户: admin/admin123")

        # 5. 获取默认用户ID
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        admin_id = cursor.fetchone()[0]

        # 6. 更新现有分类为系统预设
        print("5. 更新现有分类为系统预设...")
        cursor.execute("UPDATE categories SET is_default = 1 WHERE user_id IS NULL")

        # 7. 为现有交易关联默认用户
        print("6. 为现有交易关联默认用户...")
        cursor.execute("UPDATE transactions SET user_id = ? WHERE user_id IS NULL", (admin_id,))

        # 提交更改
        conn.commit()

        # 统计结果
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM categories")
        category_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM transactions")
        transaction_count = cursor.fetchone()[0]

        print(f"✅ 迁移完成:")
        print(f"   用户: {user_count} 个")
        print(f"   分类: {category_count} 个")
        print(f"   交易: {transaction_count} 条")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        return False


if __name__ == '__main__':
    success = migrate_to_v2_simple()
    if success:
        print("\n✅ 数据迁移成功完成！")
    else:
        print("\n❌ 数据迁移失败！")
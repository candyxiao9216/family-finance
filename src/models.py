from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    nickname = db.Column(db.String(80), nullable=True)
    role = db.Column(db.String(20), default='member')
    family_id = db.Column(db.Integer, db.ForeignKey('families.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系定义
    transactions = db.relationship('Transaction', foreign_keys='Transaction.user_id', backref='user', lazy=True)
    categories = db.relationship('Category', backref='user', lazy=True)

    def set_password(self, password):
        """设置密码哈希（使用更兼容的方法）"""
        # 使用 pbkdf2:sha256 方法，更兼容不同环境
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'nickname': self.nickname,
            'role': self.role,
            'family_id': self.family_id,
            'family_name': self.family.name if self.family else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 数据关联：交易与分类
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    is_default = db.Column(db.Boolean, default=False)  # 是否系统预设分类
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 可为 NULL 表示系统预设
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'is_default': self.is_default,
            'user_id': self.user_id
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 修改追踪字段
    last_modified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 最后修改人
    last_modified_at = db.Column(db.DateTime, nullable=True)  # 最后修改时间
    modification_count = db.Column(db.Integer, default=0)  # 修改次数

    # 最后修改人关系（需用 foreign_keys 避免与 user backref 冲突）
    last_modifier = db.relationship('User', foreign_keys=[last_modified_by], backref='modified_transactions')

    @property
    def category_name(self):
        return self.category.name if self.category else None

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount),
            'type': self.type,
            'category_id': self.category_id,
            'category_name': self.category_name,
            'description': self.description,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_modified_by': self.last_modified_by,
            'last_modified_at': self.last_modified_at.isoformat() if self.last_modified_at else None,
            'modification_count': self.modification_count or 0
        }


# 预设分类（系统默认分类，is_default=True）
DEFAULT_CATEGORIES = [
    {'name': '工资', 'type': 'income', 'is_default': True},
    {'name': '奖金', 'type': 'income', 'is_default': True},
    {'name': '餐饮', 'type': 'expense', 'is_default': True},
    {'name': '交通', 'type': 'expense', 'is_default': True},
]


class Family(db.Model):
    __tablename__ = 'families'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系定义
    members = db.relationship('User', backref='family', lazy=True)

    def __repr__(self):
        return f"<Family {self.id}: {self.name}>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'invite_code': self.invite_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'member_count': len(self.members) if self.members else 0
        }


class TransactionModification(db.Model):
    """交易修改记录表 - 记录每次交易修改的详细信息"""
    __tablename__ = 'transaction_modifications'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)  # 关联的交易 ID
    modified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # 修改人 ID
    field_name = db.Column(db.String(50), nullable=False)  # 被修改的字段名
    old_value = db.Column(db.Text, nullable=True)  # 修改前的值
    new_value = db.Column(db.Text, nullable=True)  # 修改后的值
    modified_at = db.Column(db.DateTime, default=datetime.utcnow)  # 修改时间

    # 关系定义
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id], backref='modifications')
    modifier = db.relationship('User', foreign_keys=[modified_by], backref='transaction_modifications')

    def __repr__(self):
        return f"<TransactionModification {self.id}: {self.field_name} on Transaction {self.transaction_id}>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'modified_by': self.modified_by,
            'modifier_name': self.modifier.nickname or self.modifier.username if self.modifier else None,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None
        }

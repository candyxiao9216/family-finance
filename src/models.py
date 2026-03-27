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

    # 账户关联
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    account = db.relationship('Account', backref='transactions', lazy=True)

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
            'modification_count': self.modification_count or 0,
            'account_id': self.account_id
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


class AccountType(db.Model):
    """账户类型表 - 定义储蓄/投资等账户类型"""
    __tablename__ = 'account_types'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # 'savings' 或 'investment'
    is_default = db.Column(db.Boolean, default=False)

    # 关系定义
    accounts = db.relationship('Account', backref='account_type', lazy=True)

    def __repr__(self):
        return f"<AccountType {self.id}: {self.name} ({self.category})>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'is_default': self.is_default
        }


# 预设账户类型
DEFAULT_ACCOUNT_TYPES = [
    {'name': '银行', 'category': 'savings', 'is_default': True},
    {'name': '微众', 'category': 'savings', 'is_default': True},
    {'name': '中金', 'category': 'savings', 'is_default': True},
    {'name': '富途', 'category': 'investment', 'is_default': True},
    {'name': '中银国际', 'category': 'investment', 'is_default': True},
]


class Account(db.Model):
    """账户表 - 用户的具体账户"""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('account_types.id'), nullable=False)
    initial_balance = db.Column(db.Numeric(10, 2), default=0)
    current_balance = db.Column(db.Numeric(10, 2), default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 关系定义
    owner = db.relationship('User', backref='accounts', lazy=True)
    balance_records = db.relationship('AccountBalance', backref='account', lazy=True,
                                     order_by='AccountBalance.record_month.desc()')

    def __repr__(self):
        return f"<Account {self.id}: {self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type_id': self.type_id,
            'type_name': self.account_type.name if self.account_type else None,
            'category': self.account_type.category if self.account_type else None,
            'initial_balance': float(self.initial_balance),
            'current_balance': float(self.current_balance),
            'user_id': self.user_id
        }


class AccountBalance(db.Model):
    """账户余额月度快照表 - 记录每月账户余额变化"""
    __tablename__ = 'account_balance'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    balance = db.Column(db.Numeric(10, 2), nullable=False)
    change_amount = db.Column(db.Numeric(10, 2), nullable=True)
    record_month = db.Column(db.Date, nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('account_id', 'record_month', name='uq_account_month'),
    )

    recorder = db.relationship('User', foreign_keys=[recorded_by])

    def __repr__(self):
        return f"<AccountBalance {self.id}: account={self.account_id} month={self.record_month}>"

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'balance': float(self.balance),
            'change_amount': float(self.change_amount) if self.change_amount else 0,
            'record_month': self.record_month.strftime('%Y-%m') if self.record_month else None
        }


class SavingsPlan(db.Model):
    """储蓄计划表"""
    __tablename__ = 'savings_plans'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'monthly' 或 'annual'
    target_amount = db.Column(db.Numeric(10, 2), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=True)  # 仅月度计划，1-12
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='savings_plans')
    records = db.relationship('SavingsRecord', backref='plan', lazy=True,
                              cascade='all, delete-orphan')

    def __repr__(self):
        return f"<SavingsPlan {self.id}: {self.name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'target_amount': float(self.target_amount),
            'year': self.year,
            'month': self.month,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SavingsRecord(db.Model):
    """储蓄记录表"""
    __tablename__ = 'savings_records'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('savings_plans.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    record_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship('User', foreign_keys=[user_id], backref='savings_records')
    account = db.relationship('Account', foreign_keys=[account_id])

    def __repr__(self):
        return f"<SavingsRecord {self.id}: plan={self.plan_id} amount={self.amount}>"

    def to_dict(self):
        return {
            'id': self.id,
            'plan_id': self.plan_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'account_id': self.account_id,
            'record_date': self.record_date.isoformat() if self.record_date else None,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BabyFund(db.Model):
    """宝宝基金表"""
    __tablename__ = 'baby_funds'

    VALID_EVENT_TYPES = ['满月', '生日', '红包', '其他']

    id = db.Column(db.Integer, primary_key=True)
    giver_name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by], backref='baby_funds')
    account = db.relationship('Account', foreign_keys=[account_id])
    transaction = db.relationship('Transaction', foreign_keys=[transaction_id])

    def __repr__(self):
        return f"<BabyFund {self.id}: {self.giver_name} ¥{self.amount}>"

    def to_dict(self):
        return {
            'id': self.id,
            'giver_name': self.giver_name,
            'amount': float(self.amount),
            'account_id': self.account_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'event_type': self.event_type,
            'notes': self.notes,
            'transaction_id': self.transaction_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class ImportRecord(db.Model):
    """导入记录表"""
    __tablename__ = 'import_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name = db.Column(db.String(200), nullable=False)
    import_time = db.Column(db.DateTime, default=datetime.utcnow)
    total_rows = db.Column(db.Integer, nullable=True)
    imported_count = db.Column(db.Integer, nullable=True)
    skipped_count = db.Column(db.Integer, nullable=True)
    duplicate_count = db.Column(db.Integer, nullable=True)
    source_type = db.Column(db.String(20), nullable=True)  # 'wechat'/'alipay'/'template'
    status = db.Column(db.String(20), default='completed')

    importer = db.relationship('User', foreign_keys=[user_id], backref='import_records')

    def __repr__(self):
        return f"<ImportRecord {self.id}: {self.file_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'import_time': self.import_time.isoformat() if self.import_time else None,
            'total_rows': self.total_rows,
            'imported_count': self.imported_count,
            'skipped_count': self.skipped_count,
            'duplicate_count': self.duplicate_count,
            'source_type': self.source_type,
            'status': self.status
        }


class TransactionTemplate(db.Model):
    """常用交易模板"""
    __tablename__ = 'transaction_templates'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' / 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    use_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[user_id])
    category = db.relationship('Category', foreign_keys=[category_id])
    account = db.relationship('Account', foreign_keys=[account_id])


class RecurringTransaction(db.Model):
    """定期交易"""
    __tablename__ = 'recurring_transactions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    frequency = db.Column(db.String(20), nullable=False)  # 'monthly' / 'weekly' / 'custom'
    interval_days = db.Column(db.Integer, nullable=True)
    day_of_month = db.Column(db.Integer, nullable=True)  # 1-28
    day_of_week = db.Column(db.Integer, nullable=True)   # 0=周一
    next_run_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[user_id])
    category = db.relationship('Category', foreign_keys=[category_id])
    account = db.relationship('Account', foreign_keys=[account_id])

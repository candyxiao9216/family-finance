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
    {'name': '微众', 'category': 'fund', 'is_default': True},
    {'name': '中金', 'category': 'fund', 'is_default': True},
    {'name': '富途', 'category': 'stock', 'is_default': True},
    {'name': '中银国际', 'category': 'stock', 'is_default': True},
    {'name': '招行基金', 'category': 'fund', 'is_default': True},
    {'name': '微众基金', 'category': 'fund', 'is_default': True},
    {'name': '富途基金', 'category': 'fund', 'is_default': True},
    {'name': '招行理财', 'category': 'fund', 'is_default': True},
]


class Account(db.Model):
    """账户表 - 用户的具体账户"""
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('account_types.id'), nullable=False)
    currency = db.Column(db.String(3), default='CNY')  # CNY / HKD / USD
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
    note = db.Column(db.String(200), nullable=True)  # 本月备注
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


class MonthlyTodo(db.Model):
    """月度待办引导表 - 用于记录每月的财务待办事项和引导"""
    __tablename__ = 'monthly_todos'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)  # 1-12
    
    # 待办类型：'transaction'(交易录入), 'snapshot'(账户快照), 'savings'(储蓄记录), 'baby_fund'(宝宝基金)
    category = db.Column(db.String(20), nullable=False, default='transaction')

    # 检测 key：用于自动检测完成状态（对应 category）
    detect_key = db.Column(db.String(30), nullable=True)

    # 待办项内容
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # 是否必选项（必选项参与进度计算，可选项不参与）
    is_required = db.Column(db.Boolean, default=True)

    # 优先级：1-5，其中 5 最高
    priority = db.Column(db.Integer, default=3)

    # 状态：'pending'(待处理), 'completed'(已完成)
    status = db.Column(db.String(20), default='pending')

    # 是否由系统自动检测完成（True=自动检测通过, False=手动打钩）
    auto_detected = db.Column(db.Boolean, default=False)

    # 完成日期
    completed_at = db.Column(db.DateTime, nullable=True)

    # 提示信息和小贴士
    tips = db.Column(db.Text, nullable=True)

    # 跳转链接（引导用户去完成操作的页面）
    action_url = db.Column(db.String(200), nullable=True)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系定义
    creator = db.relationship('User', foreign_keys=[user_id], backref='monthly_todos')

    # 复合唯一键：同一用户同一月份的待办项应该唯一
    __table_args__ = (
        db.UniqueConstraint('user_id', 'year', 'month', 'title', name='uq_user_month_todo'),
    )

    def __repr__(self):
        return f"<MonthlyTodo {self.id}: {self.title} ({self.year}-{self.month:02d})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'year': self.year,
            'month': self.month,
            'category': self.category,
            'detect_key': self.detect_key,
            'title': self.title,
            'description': self.description,
            'is_required': self.is_required,
            'priority': self.priority,
            'status': self.status,
            'auto_detected': self.auto_detected,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tips': self.tips,
            'action_url': self.action_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockHolding(db.Model):
    """股票持仓表"""
    __tablename__ = 'stock_holdings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    stock_code = db.Column(db.String(20), nullable=False)   # 00700, 600519, AAPL
    stock_name = db.Column(db.String(100), nullable=False)
    market = db.Column(db.String(10), nullable=False)        # HK / A / US
    shares = db.Column(db.Float, nullable=False)             # 持有股数
    avg_cost = db.Column(db.Float, nullable=False)           # 买入均价（摊薄成本）
    currency = db.Column(db.String(3), default='HKD')
    notes = db.Column(db.Text, nullable=True)                # 备注（如：公司RSU）
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[user_id], backref='stock_holdings')
    account = db.relationship('Account', foreign_keys=[account_id], backref='stock_holdings')

    def __repr__(self):
        return f"<StockHolding {self.id}: {self.stock_name}({self.stock_code}) {self.shares}股>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'market': self.market,
            'shares': self.shares,
            'avg_cost': self.avg_cost,
            'currency': self.currency,
            'notes': self.notes,
            'account_name': self.account.name if self.account else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FundHolding(db.Model):
    """基金持仓表"""
    __tablename__ = 'fund_holdings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    fund_code = db.Column(db.String(30), nullable=False)     # 004253, HK0000369188, LU0788108826
    fund_name = db.Column(db.String(100), nullable=False)
    fund_type = db.Column(db.String(30), nullable=True)      # 指数型基金/混合型基金/QDII基金/债券型基金/货币型基金/FOF基金
    shares = db.Column(db.Float, nullable=True)              # 持有份额（货币基金可能为空）
    amount = db.Column(db.Float, nullable=True)              # 持有金额
    avg_cost = db.Column(db.Float, nullable=True)            # 买入均价(净值)
    latest_nav = db.Column(db.Float, nullable=True)          # 最新净值
    profit = db.Column(db.Float, nullable=True)              # 持有收益
    profit_rate = db.Column(db.String(20), nullable=True)    # 持有收益率
    currency = db.Column(db.String(3), default='CNY')
    status = db.Column(db.String(20), default='holding')  # holding(持有) / redeemed(已赎回)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[user_id], backref='fund_holdings')
    account = db.relationship('Account', foreign_keys=[account_id], backref='fund_holdings')

    def __repr__(self):
        return f"<FundHolding {self.id}: {self.fund_name}({self.fund_code})>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'fund_code': self.fund_code,
            'fund_name': self.fund_name,
            'fund_type': self.fund_type,
            'shares': self.shares,
            'amount': self.amount,
            'avg_cost': self.avg_cost,
            'latest_nav': self.latest_nav,
            'profit': self.profit,
            'profit_rate': self.profit_rate,
            'currency': self.currency,
            'status': self.status or 'holding',
            'notes': self.notes,
            'account_name': self.account.name if self.account else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class WealthHolding(db.Model):
    """理财产品持仓表"""
    __tablename__ = 'wealth_holdings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)  # 产品名称
    manager = db.Column(db.String(100), nullable=True)        # 管理机构（浦银理财、民生理财等）
    buy_amount = db.Column(db.Float, nullable=False)          # 买入金额
    current_amount = db.Column(db.Float, nullable=True)       # 当前金额
    total_profit = db.Column(db.Float, nullable=True)         # 累计收益
    annual_rate = db.Column(db.Float, nullable=True)          # 年化收益率（小数，如 0.0295）
    buy_date = db.Column(db.Date, nullable=True)              # 买入日期
    expire_date = db.Column(db.Date, nullable=True)           # 到期日期（活期为空）
    product_type = db.Column(db.String(20), default='fixed')  # fixed(定期)/flexible(活期)/closed(封闭)
    currency = db.Column(db.String(3), default='CNY')
    notes = db.Column(db.Text, nullable=True)                 # 备注
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', foreign_keys=[user_id], backref='wealth_holdings')
    account = db.relationship('Account', foreign_keys=[account_id], backref='wealth_holdings')

    def __repr__(self):
        return f"<WealthHolding {self.id}: {self.product_name}>"

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'account_id': self.account_id,
            'product_name': self.product_name,
            'manager': self.manager,
            'buy_amount': self.buy_amount,
            'current_amount': self.current_amount,
            'total_profit': self.total_profit,
            'annual_rate': self.annual_rate,
            'buy_date': self.buy_date.isoformat() if self.buy_date else None,
            'expire_date': self.expire_date.isoformat() if self.expire_date else None,
            'product_type': self.product_type,
            'currency': self.currency,
            'notes': self.notes,
            'account_name': self.account.name if self.account else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class MarketDataCache(db.Model):
    """行情数据缓存表"""
    __tablename__ = 'market_data_cache'

    id = db.Column(db.Integer, primary_key=True)
    data_key = db.Column(db.String(100), unique=True, nullable=False)  # 如 stock_HK_00700 / fund_004253
    data_json = db.Column(db.Text, nullable=False)
    fetched_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<MarketDataCache {self.data_key}>"


class AiAdviceCache(db.Model):
    """AI 建议缓存表"""
    __tablename__ = 'ai_advice_cache'

    id = db.Column(db.Integer, primary_key=True)
    advice_key = db.Column(db.String(100), unique=True, nullable=False)  # 如 stock_analysis_00700
    advice_text = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), nullable=True)
    generated_at = db.Column(db.DateTime, nullable=False)


class AiAdviceHistory(db.Model):
    """AI 建议历史记录（永久保存，供回看）"""
    __tablename__ = 'ai_advice_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    advice_type = db.Column(db.String(30), nullable=False)  # comprehensive/stocks/funds/wealth/savings
    advice_text = db.Column(db.Text, nullable=False)
    model_used = db.Column(db.String(50), nullable=True)
    generated_at = db.Column(db.DateTime, nullable=False)

    owner = db.relationship('User', foreign_keys=[user_id])

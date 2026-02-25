from datetime import datetime
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 数据关联：交易与分类
class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' 或 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    description = db.Column(db.Text, nullable=True)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# 预设分类
DEFAULT_CATEGORIES = [
    {'name': '工资', 'type': 'income'},
    {'name': '奖金', 'type': 'income'},
    {'name': '餐饮', 'type': 'expense'},
    {'name': '交通', 'type': 'expense'},
]

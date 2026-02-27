from datetime import date, datetime
from decimal import Decimal

from flask import Flask, redirect, render_template, request, url_for
from sqlalchemy import func, extract, case

from database import create_app, init_database
from models import db, Transaction, Category, User, Family
from routes.auth import auth_bp
from routes.family import family_bp
from flask import session

app = create_app()

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(family_bp)

@app.before_request
def require_login():
    """登录状态检查"""
    # 允许访问的公开路由
    allowed_routes = ['auth.login', 'auth.register', 'static', 'family.family_info', 'family.family_members']

    if request.endpoint and request.endpoint not in allowed_routes:
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))


@app.route('/init-db')
def init_db_route():
    """初始化数据库（开发用路由）"""
    init_database(app)
    return "数据库初始化成功！<a href='/'>返回首页</a>"


@app.route('/')
def index():
    """首页 - 交易列表"""
    # 获取当前用户的交易，按日期降序
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.transaction_date.desc()).all()

    # 计算本月统计（仅当前用户）
    current_month = date.today().month
    current_year = date.today().year

    month_stats = db.session.query(
        func.sum(
            case(
                ((Transaction.type == 'income') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & (Transaction.user_id == user_id), Transaction.amount)
            )
        ).label('income'),
        func.sum(
            case(
                ((Transaction.type == 'expense') & (extract('month', Transaction.transaction_date) == current_month) &
                 (extract('year', Transaction.transaction_date) == current_year) & (Transaction.user_id == user_id), Transaction.amount)
            )
        ).label('expense')
    ).first()

    monthly_income = month_stats.income or Decimal('0')
    monthly_expense = month_stats.expense or Decimal('0')
    monthly_balance = monthly_income - monthly_expense

    # 获取当前用户可用的分类（系统预设 + 用户自定义）
    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()

    return render_template('index.html',
                          transactions=transactions,
                          monthly_income=float(monthly_income),
                          monthly_expense=float(monthly_expense),
                          monthly_balance=float(monthly_balance),
                          categories=categories,
                          username=session.get('nickname', session.get('username', '用户')))


@app.route('/add', methods=['POST'])
def add_transaction():
    """添加交易"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction_type = request.form.get('type')
    amount = request.form.get('amount')
    category_id = request.form.get('category')
    transaction_date_str = request.form.get('date')
    description = request.form.get('description')

    # 基本验证
    if not all([transaction_type, amount, category_id, transaction_date_str]):
        return "缺少必填字段", 400

    try:
        transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()
    except ValueError:
        return "日期格式错误", 400

    # 创建交易记录
    transaction = Transaction(
        amount=Decimal(amount),
        type=transaction_type,
        category_id=int(category_id),
        description=description or None,
        transaction_date=transaction_date,
        user_id=user_id
    )

    db.session.add(transaction)
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/delete/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    """删除交易"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    transaction = Transaction.query.get_or_404(transaction_id)

    # 检查权限：只能删除自己的交易
    if transaction.user_id != user_id:
        return "无权删除此交易", 403

    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for('index'))


if __name__ == '__main__':
    # 首次运行时初始化数据库
    init_database(app)
    # 使用 5001 端口避免与 macOS AirPlay Receiver 冲突
    app.run(host='0.0.0.0', port=5001, debug=True)

"""
分类管理路由模块
实现分类的列表、添加、删除功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, Category, Transaction

category_bp = Blueprint('category', __name__, url_prefix='/categories')


@category_bp.route('/')
def category_list():
    """分类管理页面"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).order_by(Category.type, Category.is_default.desc(), Category.name).all()

    income_categories = [c for c in categories if c.type == 'income']
    expense_categories = [c for c in categories if c.type == 'expense']

    return render_template('categories.html',
                           income_categories=income_categories,
                           expense_categories=expense_categories,
                           username=session.get('nickname', session.get('username', '用户')))


@category_bp.route('/add', methods=['POST'])
def category_add():
    """添加自定义分类"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    name = request.form.get('name', '').strip()
    cat_type = request.form.get('type')

    if not name or cat_type not in ('income', 'expense'):
        flash('请输入分类名称并选择类型', 'error')
        return redirect(url_for('category.category_list'))

    # 检查同名分类是否已存在（同用户 + 系统预设范围内）
    existing = Category.query.filter(
        Category.name == name,
        Category.type == cat_type,
        (Category.user_id == None) | (Category.user_id == user_id)
    ).first()

    if existing:
        flash('该分类已存在', 'error')
        return redirect(url_for('category.category_list'))

    category = Category(
        name=name,
        type=cat_type,
        is_default=False,
        user_id=user_id
    )
    db.session.add(category)
    db.session.commit()

    flash(f'分类「{name}」添加成功', 'success')
    return redirect(url_for('category.category_list'))


@category_bp.route('/edit/<int:category_id>', methods=['POST'])
def category_edit(category_id):
    """修改分类名称"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    category = Category.query.get_or_404(category_id)

    if category.user_id is not None and category.user_id != user_id:
        flash('无权修改此分类', 'error')
        return redirect(url_for('category.category_list'))

    new_name = request.form.get('name', '').strip()
    if not new_name:
        flash('分类名称不能为空', 'error')
        return redirect(url_for('category.category_list'))

    # 检查同名分类
    existing = Category.query.filter(
        Category.name == new_name,
        Category.type == category.type,
        Category.id != category_id,
        (Category.user_id == None) | (Category.user_id == user_id)
    ).first()
    if existing:
        flash('该分类名称已存在', 'error')
        return redirect(url_for('category.category_list'))

    old_name = category.name
    category.name = new_name
    db.session.commit()
    flash(f'分类「{old_name}」已改名为「{new_name}」', 'success')
    return redirect(url_for('category.category_list'))


@category_bp.route('/delete/<int:category_id>', methods=['POST'])
def category_delete(category_id):
    """删除自定义分类"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    category = Category.query.get_or_404(category_id)

    # 只能删除自己创建的分类（系统分类所有人可删）
    if category.user_id is not None and category.user_id != user_id:
        flash('无权删除此分类', 'error')
        return redirect(url_for('category.category_list'))

    # 将关联交易的 category_id 设为 NULL
    Transaction.query.filter_by(category_id=category_id).update({'category_id': None})

    cat_name = category.name
    db.session.delete(category)
    db.session.commit()

    flash(f'分类「{cat_name}」已删除，关联交易已变为未分类', 'success')
    return redirect(url_for('category.category_list'))

"""快捷模板路由模块"""
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, session, url_for, flash

from models import db, User, TransactionTemplate, Category, Account

template_bp = Blueprint('template', __name__, url_prefix='/templates')


@template_bp.route('/')
def template_list():
    """快捷模板列表页"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    templates = TransactionTemplate.query.filter_by(user_id=user_id)\
        .order_by(TransactionTemplate.use_count.desc()).all()

    categories = Category.query.filter(
        (Category.user_id == None) | (Category.user_id == user_id)
    ).all()
    accounts = Account.query.filter_by(user_id=user_id).all()

    return render_template('quick_templates.html',
                           templates=templates,
                           categories=categories,
                           accounts=accounts,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')),
                           page_title='快捷模板')


@template_bp.route('/add', methods=['POST'])
def add_template():
    """创建快捷模板"""
    user_id = session.get('user_id')
    name = request.form.get('name')
    amount = request.form.get('amount')
    tpl_type = request.form.get('type')
    category_id = request.form.get('category_id', type=int)
    account_id = request.form.get('account_id', type=int)
    description = request.form.get('description')

    if not all([name, amount, tpl_type]):
        flash('请填写所有必填字段', 'error')
        return redirect(url_for('template.template_list'))

    tpl = TransactionTemplate(
        user_id=user_id,
        name=name,
        amount=Decimal(amount),
        type=tpl_type,
        category_id=category_id or None,
        account_id=account_id or None,
        description=description or None
    )
    db.session.add(tpl)
    db.session.commit()

    flash('模板创建成功', 'success')
    return redirect(url_for('template.template_list'))


@template_bp.route('/<int:tpl_id>/edit', methods=['POST'])
def edit_template(tpl_id):
    """编辑快捷模板"""
    tpl = TransactionTemplate.query.get_or_404(tpl_id)

    tpl.name = request.form.get('name', tpl.name)
    tpl.amount = Decimal(request.form.get('amount', str(tpl.amount)))
    tpl.type = request.form.get('type', tpl.type)
    tpl.category_id = request.form.get('category_id', type=int) or None
    tpl.account_id = request.form.get('account_id', type=int) or None
    tpl.description = request.form.get('description') or None

    db.session.commit()
    flash('模板已更新', 'success')
    return redirect(url_for('template.template_list'))


@template_bp.route('/<int:tpl_id>/delete', methods=['POST'])
def delete_template(tpl_id):
    """删除快捷模板"""
    tpl = TransactionTemplate.query.get_or_404(tpl_id)
    db.session.delete(tpl)
    db.session.commit()
    flash('模板已删除', 'success')
    return redirect(url_for('template.template_list'))


@template_bp.route('/<int:tpl_id>/use', methods=['POST'])
def use_template(tpl_id):
    """使用模板（递增使用次数）"""
    tpl = TransactionTemplate.query.get(tpl_id)
    if tpl:
        tpl.use_count = (tpl.use_count or 0) + 1
        db.session.commit()
    return '', 204

"""账号设置路由模块"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify

from models import db, User

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
def settings_page():
    """账号设置页"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    family = user.family if user else None

    return render_template('settings.html',
                           user=user,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')),
                           page_title='账号设置')


@settings_bp.route('/nickname', methods=['POST'])
def update_nickname():
    """修改昵称"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401

    user = User.query.get(user_id)
    nickname = request.form.get('nickname', '').strip()

    if not nickname or len(nickname) > 20:
        flash('昵称不能为空且不超过20字', 'error')
        return redirect(url_for('settings.settings_page'))

    user.nickname = nickname
    session['nickname'] = nickname  # 同步 session
    db.session.commit()

    flash('昵称已更新', 'success')
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/avatar', methods=['POST'])
def update_avatar():
    """修改展示图标"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401

    user = User.query.get(user_id)
    avatar_text = request.form.get('avatar_text', '').strip()

    if not avatar_text or len(avatar_text) > 2:
        flash('图标需为1-2个字符', 'error')
        return redirect(url_for('settings.settings_page'))

    user.avatar_text = avatar_text
    db.session.commit()

    flash('展示图标已更新', 'success')
    return redirect(url_for('settings.settings_page'))


@settings_bp.route('/password', methods=['POST'])
def update_password():
    """修改密码"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '未登录'}), 401

    user = User.query.get(user_id)
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    # 验证旧密码
    if not user.check_password(old_password):
        flash('当前密码错误', 'error')
        return redirect(url_for('settings.settings_page'))

    # 验证新密码规则
    if len(new_password) < 8:
        flash('新密码至少8位', 'error')
        return redirect(url_for('settings.settings_page'))

    has_letter = any(c.isalpha() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    if not (has_letter and has_digit):
        flash('新密码需包含字母和数字', 'error')
        return redirect(url_for('settings.settings_page'))

    # 验证两次输入一致
    if new_password != confirm_password:
        flash('两次输入的密码不一致', 'error')
        return redirect(url_for('settings.settings_page'))

    user.set_password(new_password)
    db.session.commit()

    flash('密码已修改', 'success')
    return redirect(url_for('settings.settings_page'))

"""
家庭管理路由模块
实现家庭创建、加入、成员管理等功能
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Family
from routes.auth import generate_invite_code, create_family_for_first_user, join_family_with_invite_code

# 创建家庭蓝图
family_bp = Blueprint('family', __name__, url_prefix='/family')


@family_bp.route('/info')
def family_info():
    """获取家庭信息"""
    user_id = session.get('user_id')
    if not user_id:
        flash('请先登录', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        flash('用户不存在', 'error')
        return redirect(url_for('auth.login'))

    if not user.family_id:
        flash('您尚未加入任何家庭', 'error')
        return redirect(url_for('index'))

    family = Family.query.get(user.family_id)
    if not family:
        flash('家庭信息不存在', 'error')
        return redirect(url_for('index'))

    return render_template('family/info.html',
                         family=family,
                         user=user)


@family_bp.route('/members')
def family_members():
    """获取家庭成员列表"""
    user_id = session.get('user_id')
    if not user_id:
        flash('请先登录', 'error')
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        flash('用户不存在', 'error')
        return redirect(url_for('auth.login'))

    if not user.family_id:
        flash('您尚未加入任何家庭', 'error')
        return redirect(url_for('index'))

    family = Family.query.get(user.family_id)
    if not family:
        flash('家庭信息不存在', 'error')
        return redirect(url_for('index'))

    # 获取家庭成员，按创建时间排序
    members = User.query.filter_by(family_id=user.family_id).order_by(User.created_at.asc()).all()

    return render_template('family/members.html',
                         family=family,
                         members=members,
                         user=user)


@family_bp.route('/regenerate-invite', methods=['POST'])
def regenerate_invite_code():
    """重新生成邀请码"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '请先登录'}), 401

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': '用户不存在'}), 401

    if not user.family_id:
        return jsonify({'error': '您尚未加入任何家庭'}), 400

    family = Family.query.get(user.family_id)
    if not family:
        return jsonify({'error': '家庭信息不存在'}), 400

    # 生成新的邀请码
    new_invite_code = generate_invite_code()
    family.invite_code = new_invite_code
    db.session.commit()

    return jsonify({
        'success': True,
        'new_invite_code': new_invite_code,
        'message': '邀请码已更新'
    })


@family_bp.route('/api/info')
def api_family_info():
    """API: 获取家庭信息（JSON格式）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '请先登录'}), 401

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': '用户不存在'}), 401

    if not user.family_id:
        return jsonify({'error': '您尚未加入任何家庭'}), 400

    family = Family.query.get(user.family_id)
    if not family:
        return jsonify({'error': '家庭信息不存在'}), 400

    return jsonify({
        'family': family.to_dict(),
        'members': [member.to_dict() for member in family.members]
    })


@family_bp.route('/api/members')
def api_family_members():
    """API: 获取家庭成员列表（JSON格式）"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': '请先登录'}), 401

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return jsonify({'error': '用户不存在'}), 401

    if not user.family_id:
        return jsonify({'error': '您尚未加入任何家庭'}), 400

    family = Family.query.get(user.family_id)
    if not family:
        return jsonify({'error': '家庭信息不存在'}), 400

    members = User.query.filter_by(family_id=user.family_id).order_by(User.created_at.asc()).all()

    return jsonify({
        'family': family.to_dict(),
        'members': [member.to_dict() for member in members]
    })
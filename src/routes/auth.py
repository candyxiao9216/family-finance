"""
用户认证路由模块（支持家庭功能）
实现注册、登录、登出功能，支持家庭创建和加入
"""

import random
import string
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db, User, Family

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def generate_invite_code(length=8):
    """生成随机邀请码"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


def create_family_for_first_user(user):
    """为第一个用户自动创建家庭"""
    # 检查是否已有家庭存在
    existing_family = Family.query.first()
    if existing_family:
        return existing_family

    # 创建新家庭
    family_name = f"{user.nickname or user.username}的家庭"
    invite_code = generate_invite_code()

    family = Family(
        name=family_name,
        invite_code=invite_code
    )

    db.session.add(family)
    db.session.flush()  # 获取 family.id

    # 将用户关联到家庭
    user.family_id = family.id
    db.session.commit()

    return family


def join_family_with_invite_code(user, invite_code):
    """用户通过邀请码加入家庭"""
    # 查找邀请码对应的家庭
    family = Family.query.filter_by(invite_code=invite_code).first()
    if not family:
        return None, "无效的邀请码"

    # 将用户关联到家庭
    user.family_id = family.id
    db.session.commit()

    return family, None


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册（支持家庭功能）"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        nickname = request.form.get('nickname', '')
        invite_code = request.form.get('invite_code', '').strip()

        # 基本验证
        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('auth/register-redesigned.html')

        if len(username) < 3 or len(username) > 20:
            flash('用户名长度必须在3-20个字符之间')
            return render_template('auth/register-redesigned.html')

        if len(password) < 6:
            flash('密码长度不能少于6个字符')
            return render_template('auth/register-redesigned.html')

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在，请选择其他用户名')
            return render_template('auth/register-redesigned.html')

        # 创建新用户
        try:
            user = User(
                username=username,
                nickname=nickname or username
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # 获取 user.id

            # 家庭处理逻辑
            if invite_code:
                # 使用邀请码加入家庭
                family, error = join_family_with_invite_code(user, invite_code)
                if error:
                    db.session.rollback()
                    flash(error)
                    return render_template('auth/register-redesigned.html')

                flash(f'注册成功！您已加入 {family.name}')
            else:
                # 第一个用户自动创建家庭
                family = create_family_for_first_user(user)
                flash(f'注册成功！已为您创建家庭 {family.name}，邀请码：{family.invite_code}')

            db.session.commit()

            # 自动登录
            session['user_id'] = user.id
            session['username'] = user.username
            session['nickname'] = user.nickname
            session['family_id'] = user.family_id

            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            flash(f'注册失败：{str(e)}')
            return render_template('auth/register-redesigned.html')

    return render_template('auth/register-redesigned.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    # 如果已登录，重定向到首页
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('用户名和密码不能为空')
            return render_template('auth/login-redesigned.html')

        # 验证用户
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            # 登录成功
            session['user_id'] = user.id
            session['username'] = user.username
            session['nickname'] = user.nickname
            session['family_id'] = user.family_id

            flash(f'欢迎回来，{user.nickname}！')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误')
            return render_template('auth/login-redesigned.html')

    return render_template('auth/login-redesigned.html')


@auth_bp.route('/logout')
def logout():
    """用户登出"""
    # 清除会话数据
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('nickname', None)
    session.pop('family_id', None)

    flash('您已成功登出')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
def profile():
    """用户个人资料页面"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        # 用户不存在，清除会话
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('auth/profile.html', user=user)
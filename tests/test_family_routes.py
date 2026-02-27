"""
家庭路由测试用例
测试家庭创建、加入、成员管理等路由功能
"""
import pytest
import sys
import os

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import datetime
from flask import session
from models import db, User, Family
from database import create_app


class TestFamilyRoutes:
    """家庭路由测试类"""

    @pytest.fixture
    def app(self):
        """创建测试应用"""
        app = create_app()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # 禁用 CSRF 保护

        with app.app_context():
            db.create_all()
            yield app
            db.session.remove()
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return app.test_client()

    def test_create_family_first_user(self, client, app):
        """测试第一个用户自动创建家庭"""
        with app.app_context():
            # 注册第一个用户
            response = client.post('/auth/register', data={
                'username': 'firstuser',
                'password': 'password123',
                'nickname': '第一个用户'
            }, follow_redirects=True)

            # 验证注册成功
            assert response.status_code == 200

            # 验证用户已创建
            user = User.query.filter_by(username='firstuser').first()
            assert user is not None

            # 验证家庭已自动创建
            family = Family.query.first()
            assert family is not None
            assert family.name == f"{user.nickname}的家庭"
            assert len(family.invite_code) == 8  # 邀请码长度应为8位

            # 验证用户已关联到家庭
            assert user.family_id == family.id

    def test_join_family_with_invite_code(self, client, app):
        """测试用户通过邀请码加入家庭"""
        with app.app_context():
            # 创建第一个用户和家庭
            family = Family(name="测试家庭", invite_code="TEST1234")
            db.session.add(family)

            first_user = User(
                username="firstuser",
                nickname="第一个用户"
            )
            first_user.set_password("password123")
            first_user.family = family
            db.session.add(first_user)
            db.session.commit()

            # 第二个用户注册时使用邀请码
            response = client.post('/auth/register', data={
                'username': 'seconduser',
                'password': 'password456',
                'nickname': '第二个用户',
                'invite_code': 'TEST1234'
            }, follow_redirects=True)

            # 验证注册成功
            assert response.status_code == 200

            # 验证第二个用户已加入家庭
            second_user = User.query.filter_by(username='seconduser').first()
            assert second_user is not None
            assert second_user.family_id == family.id

    def test_join_family_invalid_invite_code(self, client, app):
        """测试使用无效邀请码"""
        with app.app_context():
            # 创建第一个用户和家庭
            family = Family(name="测试家庭", invite_code="TEST1234")
            db.session.add(family)

            first_user = User(
                username="firstuser",
                nickname="第一个用户"
            )
            first_user.set_password("password123")
            first_user.family = family
            db.session.add(first_user)
            db.session.commit()

            # 第二个用户使用无效邀请码
            response = client.post('/auth/register', data={
                'username': 'seconduser',
                'password': 'password456',
                'nickname': '第二个用户',
                'invite_code': 'INVALID'
            }, follow_redirects=True)

            # 验证注册失败
            assert '无效的邀请码' in response.get_data(as_text=True)

    def test_get_family_info(self, client, app):
        """测试获取家庭信息"""
        with app.app_context():
            # 创建家庭和用户
            family = Family(name="测试家庭", invite_code="TEST1234")
            db.session.add(family)

            user = User(
                username="testuser",
                nickname="测试用户"
            )
            user.set_password("password123")
            user.family = family
            db.session.add(user)
            db.session.commit()

            # 登录用户
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'password123'
            })

            # 获取家庭信息
            response = client.get('/family/info')

            # 验证返回的家庭信息
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert '测试家庭' in response_text
            assert 'TEST1234' in response_text

    def test_get_family_members(self, client, app):
        """测试获取家庭成员列表"""
        with app.app_context():
            # 创建家庭和多个用户
            family = Family(name="测试家庭", invite_code="TEST1234")
            db.session.add(family)

            users = []
            for i in range(3):
                user = User(
                    username=f"user{i}",
                    nickname=f"用户{i}"
                )
                user.set_password("password123")
                user.family = family
                users.append(user)
                db.session.add(user)

            db.session.commit()

            # 登录其中一个用户
            client.post('/auth/login', data={
                'username': 'user0',
                'password': 'password123'
            })

            # 获取家庭成员列表
            response = client.get('/family/members')

            # 验证返回的成员列表
            assert response.status_code == 200
            response_text = response.get_data(as_text=True)
            assert '用户0' in response_text
            assert '用户1' in response_text
            assert '用户2' in response_text

    def test_regenerate_invite_code(self, client, app):
        """测试重新生成邀请码"""
        with app.app_context():
            # 创建家庭和用户
            family = Family(name="测试家庭", invite_code="OLDCODE")
            db.session.add(family)

            user = User(
                username="testuser",
                nickname="测试用户"
            )
            user.set_password("password123")
            user.family = family
            db.session.add(user)
            db.session.commit()

            # 登录用户
            client.post('/auth/login', data={
                'username': 'testuser',
                'password': 'password123'
            })

            # 重新生成邀请码
            response = client.post('/family/regenerate-invite')

            # 验证邀请码已更新
            assert response.status_code == 200
            family = Family.query.first()
            assert family.invite_code != "OLDCODE"
            assert len(family.invite_code) == 8

    def test_family_routes_require_login(self, client, app):
        """测试家庭路由需要登录"""
        # 未登录时访问家庭路由
        response = client.get('/family/info', follow_redirects=True)

        # 验证重定向到登录页面
        response_text = response.get_data(as_text=True)
        assert '登录' in response_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
"""测试家庭路由 (src/routes/family.py)"""
import pytest
from models import db, User, Family


class TestFamilyInfo:
    """GET /family/info 家庭信息页"""

    def test_unauthenticated_redirect(self, client):
        """未登录用户重定向到登录页"""
        resp = client.get('/family/info')
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_user_without_family_redirect(self, logged_in_client):
        """无家庭用户重定向到首页"""
        resp = logged_in_client.get('/family/info')
        assert resp.status_code == 302

    def test_family_user_returns_200(self, family_client):
        """有家庭用户访问返回 200"""
        resp = family_client.get('/family/info')
        assert resp.status_code == 200
        assert '家庭信息'.encode() in resp.data or '测试家庭'.encode() in resp.data


class TestFamilyMembers:
    """GET /family/members 家庭成员页"""

    def test_unauthenticated_redirect(self, client):
        """未登录用户重定向到登录页"""
        resp = client.get('/family/members')
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_user_without_family_redirect(self, logged_in_client):
        """无家庭用户重定向到首页"""
        resp = logged_in_client.get('/family/members')
        assert resp.status_code == 302

    def test_family_user_returns_200(self, family_client):
        """有家庭用户访问返回 200"""
        resp = family_client.get('/family/members')
        assert resp.status_code == 200
        assert 'family_user'.encode() in resp.data or '家庭成员'.encode() in resp.data


class TestRegenerateInvite:
    """POST /family/regenerate-invite 重新生成邀请码"""

    def test_unauthenticated_returns_401(self, client):
        """未登录用户返回 401"""
        resp = client.post('/family/regenerate-invite')
        assert resp.status_code == 401

    def test_user_without_family_returns_400(self, logged_in_client):
        """无家庭用户返回 400"""
        resp = logged_in_client.post('/family/regenerate-invite')
        assert resp.status_code == 400
        data = resp.get_json()
        assert '尚未加入' in data.get('error', '')

    def test_family_user_regenerates_code(self, family_client, app):
        """有家庭用户成功重新生成邀请码"""
        # 获取旧邀请码
        with app.app_context():
            user = User.query.filter_by(username='family_user').first()
            family = Family.query.get(user.family_id)
            old_code = family.invite_code

        resp = family_client.post('/family/regenerate-invite')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert 'new_invite_code' in data
        assert data['new_invite_code'] != old_code


class TestFamilyApiInfo:
    """GET /family/api/info JSON API"""

    def test_unauthenticated_returns_401(self, client):
        """未登录用户返回 401"""
        resp = client.get('/family/api/info')
        assert resp.status_code == 401

    def test_user_without_family_returns_400(self, logged_in_client):
        """无家庭用户返回 400"""
        resp = logged_in_client.get('/family/api/info')
        assert resp.status_code == 400

    def test_family_user_returns_json(self, family_client):
        """有家庭用户返回 JSON 家庭信息"""
        resp = family_client.get('/family/api/info')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'family' in data
        assert 'members' in data
        assert data['family']['name'] == '测试家庭'


class TestFamilyApiMembers:
    """GET /family/api/members JSON API"""

    def test_unauthenticated_returns_401(self, client):
        """未登录用户返回 401"""
        resp = client.get('/family/api/members')
        assert resp.status_code == 401

    def test_user_without_family_returns_400(self, logged_in_client):
        """无家庭用户返回 400"""
        resp = logged_in_client.get('/family/api/members')
        assert resp.status_code == 400

    def test_family_user_returns_members(self, family_client):
        """有家庭用户返回成员列表"""
        resp = family_client.get('/family/api/members')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'family' in data
        assert 'members' in data
        assert len(data['members']) >= 1

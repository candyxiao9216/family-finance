"""测试月度收支路由 (src/routes/transaction.py)"""
import pytest
from models import db, User, Category


class TestTransactionList:
    """GET /transactions 路由测试"""

    def test_unauthenticated_still_renders(self, client):
        """未登录访问交易列表页应被全局 before_request 拦截跳登录"""
        resp = client.get('/transactions/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers.get('Location', '')

    def test_list_page_returns_200(self, logged_in_client, app):
        """已登录用户访问月度收支页返回 200"""
        resp = logged_in_client.get('/transactions/')
        assert resp.status_code == 200
        assert '月度收支'.encode() in resp.data or b'transactions' in resp.data

    def test_list_page_with_family_view(self, family_client, app):
        """家庭视图下访问月度收支页返回 200"""
        resp = family_client.get('/transactions/?view=family')
        assert resp.status_code == 200

    def test_list_page_pagination(self, logged_in_client, app):
        """分页参数正常工作"""
        resp = logged_in_client.get('/transactions/?page=1')
        assert resp.status_code == 200

        resp = logged_in_client.get('/transactions/?page=999')
        assert resp.status_code == 200  # 空页不报错

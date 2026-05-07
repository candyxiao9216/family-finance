"""所有页面渲染回归测试 — 确保每个页面能正常渲染，不因 CSS 类冲突或模板错误导致 500"""
import pytest


class TestPageRendering:
    """验证所有用户可见页面正常渲染（HTTP 200）"""

    def test_index_page(self, logged_in_client):
        """首页仪表盘正常渲染"""
        resp = logged_in_client.get('/')
        assert resp.status_code == 200

    def test_transactions_page(self, logged_in_client):
        """月度收支页正常渲染，包含 form-row（两列表单布局）"""
        resp = logged_in_client.get('/transactions', follow_redirects=True)
        assert resp.status_code == 200
        assert b'form-row' in resp.data

    def test_accounts_page(self, logged_in_client):
        """资产总览页正常渲染，包含 card-header"""
        resp = logged_in_client.get('/accounts', follow_redirects=True)
        assert resp.status_code == 200
        assert b'card-header' in resp.data

    def test_savings_page(self, logged_in_client):
        """储蓄计划页正常渲染，包含 card-header"""
        resp = logged_in_client.get('/savings/', follow_redirects=True)
        assert resp.status_code == 200
        assert b'card-header' in resp.data

    def test_baby_funds_page(self, logged_in_client):
        """宝宝基金页正常渲染"""
        resp = logged_in_client.get('/baby-fund/', follow_redirects=True)
        assert resp.status_code == 200

    def test_categories_page(self, logged_in_client):
        """分类管理页正常渲染"""
        resp = logged_in_client.get('/categories/', follow_redirects=True)
        assert resp.status_code == 200

    def test_reports_page(self, logged_in_client):
        """数据报表页正常渲染"""
        resp = logged_in_client.get('/reports', follow_redirects=True)
        assert resp.status_code == 200

    def test_upload_page(self, logged_in_client):
        """批量导入页正常渲染"""
        resp = logged_in_client.get('/upload', follow_redirects=True)
        assert resp.status_code == 200

    def test_advisor_page(self, logged_in_client):
        """财务顾问页正常渲染，包含 advisor-container"""
        resp = logged_in_client.get('/advisor/', follow_redirects=True)
        assert resp.status_code == 200
        assert b'advisor-container' in resp.data

    def test_transactions_form_has_grid_layout(self, logged_in_client):
        """月度收支的添加交易表单使用 grid 两列布局（不是被覆盖的 flex）"""
        resp = logged_in_client.get('/transactions', follow_redirects=True)
        html = resp.data.decode()
        assert 'form-row' in html
        assert 'add-holding-form' not in html

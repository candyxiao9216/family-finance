"""报表路由测试"""
import json
import pytest
from datetime import date, timedelta
from models import db, Transaction, User, Account, AccountType, AccountBalance


class TestReportsPage:
    """报表页面"""

    def test_reports_page_200(self, logged_in_client):
        """登录后访问报表页面返回 200"""
        resp = logged_in_client.get('/reports/')
        assert resp.status_code == 200
        assert '数据报表' in resp.data.decode('utf-8')

    def test_reports_page_personal_view(self, logged_in_client):
        """个人视图参数正常"""
        resp = logged_in_client.get('/reports/?view=personal')
        assert resp.status_code == 200

    def test_reports_page_family_view_fallback(self, logged_in_client):
        """无家庭用户访问家庭视图回退到个人"""
        resp = logged_in_client.get('/reports/?view=family')
        assert resp.status_code == 200


class TestTrendAPI:
    """趋势图 API"""

    def test_trend_api_returns_json(self, logged_in_client):
        """趋势 API 返回 JSON 格式"""
        resp = logged_in_client.get('/reports/api/trend')
        assert resp.status_code == 200
        assert resp.content_type == 'application/json'

        data = json.loads(resp.data)
        assert 'labels' in data
        assert 'income' in data
        assert 'expense' in data

    def test_trend_api_default_6_months(self, logged_in_client):
        """默认返回 6 个月数据"""
        resp = logged_in_client.get('/reports/api/trend')
        data = json.loads(resp.data)
        assert len(data['labels']) == 6
        assert len(data['income']) == 6
        assert len(data['expense']) == 6

    def test_trend_api_1_month(self, logged_in_client):
        """查询 1 个月数据"""
        resp = logged_in_client.get('/reports/api/trend?months=1')
        data = json.loads(resp.data)
        assert len(data['labels']) == 1

    def test_trend_api_3_months(self, logged_in_client):
        """查询 3 个月数据"""
        resp = logged_in_client.get('/reports/api/trend?months=3')
        data = json.loads(resp.data)
        assert len(data['labels']) == 3

    def test_trend_api_12_months(self, logged_in_client):
        """查询 12 个月数据"""
        resp = logged_in_client.get('/reports/api/trend?months=12')
        data = json.loads(resp.data)
        assert len(data['labels']) == 12

    def test_trend_api_invalid_months_fallback(self, logged_in_client):
        """无效月份参数回退到 6 个月"""
        resp = logged_in_client.get('/reports/api/trend?months=7')
        data = json.loads(resp.data)
        assert len(data['labels']) == 6

    def test_trend_api_with_data(self, app):
        """有交易数据时返回正确聚合结果"""
        with app.app_context():
            user = User(username='report_user', nickname='报表测试')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # 添加本月交易
            today = date.today()
            txn_income = Transaction(
                user_id=user_id,
                amount=5000,
                type='income',
                transaction_date=today,
                description='工资'
            )
            txn_expense = Transaction(
                user_id=user_id,
                amount=2000,
                type='expense',
                transaction_date=today,
                description='餐饮'
            )
            db.session.add_all([txn_income, txn_expense])
            db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        resp = client.get('/reports/api/trend?months=1')
        data = json.loads(resp.data)

        current_month = today.strftime('%Y-%m')
        assert current_month in data['labels']
        idx = data['labels'].index(current_month)
        assert data['income'][idx] == 5000.0
        assert data['expense'][idx] == 2000.0

    def test_trend_api_unauthenticated(self, client):
        """未登录访问趋势 API 返回 401"""
        resp = client.get('/reports/api/trend')
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert data['error'] == '未登录'


class TestCategoryAPI:
    """分类占比 API"""

    def test_category_api_returns_json(self, logged_in_client):
        """分类 API 返回 JSON"""
        resp = logged_in_client.get('/reports/api/category')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'labels' in data
        assert 'values' in data

    def test_category_api_income_type(self, logged_in_client):
        """查询收入分类占比"""
        resp = logged_in_client.get('/reports/api/category?type=income')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'labels' in data

    def test_category_api_invalid_type_fallback(self, logged_in_client):
        """无效类型参数回退到 expense"""
        resp = logged_in_client.get('/reports/api/category?type=invalid')
        assert resp.status_code == 200

    def test_category_api_unauthenticated(self, client):
        """未登录访问分类 API 返回 401"""
        resp = client.get('/reports/api/category')
        assert resp.status_code == 401


class TestAssetTrendAPI:
    """资产趋势 API"""

    def test_asset_trend_api_returns_json(self, logged_in_client):
        """资产趋势 API 返回 JSON"""
        resp = logged_in_client.get('/reports/api/asset-trend')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'labels' in data
        assert 'savings' in data
        assert 'investment' in data
        assert 'total' in data

    def test_asset_trend_no_accounts_empty(self, logged_in_client):
        """无账户时返回空数据"""
        resp = logged_in_client.get('/reports/api/asset-trend')
        data = json.loads(resp.data)
        assert data['labels'] == []
        assert data['savings'] == []

    def test_asset_trend_with_data(self, app):
        """有快照数据时返回正确聚合"""
        with app.app_context():
            user = User(username='asset_user', nickname='资产测试')
            user.set_password('Test1234')
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            savings_type = AccountType.query.filter_by(category='savings').first()
            account = Account(
                user_id=user_id,
                name='资产测试账户',
                type_id=savings_type.id,
                initial_balance=0,
                current_balance=50000
            )
            db.session.add(account)
            db.session.commit()

            # 添加本月快照
            this_month = date.today().replace(day=1)
            snapshot = AccountBalance(
                account_id=account.id,
                balance=50000,
                record_month=this_month,
                recorded_by=user_id
            )
            db.session.add(snapshot)
            db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = user_id

        resp = client.get('/reports/api/asset-trend?months=1')
        data = json.loads(resp.data)

        assert len(data['labels']) == 1
        assert data['savings'][0] == 50000.0
        assert data['total'][0] == 50000.0

    def test_asset_trend_unauthenticated(self, client):
        """未登录访问资产趋势 API 返回 401"""
        resp = client.get('/reports/api/asset-trend')
        assert resp.status_code == 401

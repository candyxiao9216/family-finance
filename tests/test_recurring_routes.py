"""测试定期交易路由 (src/routes/recurring.py)"""
import pytest
from datetime import date, timedelta
from models import db, RecurringTransaction


class TestRecurringList:
    """GET /recurring 列表页"""

    def test_list_page_returns_200(self, logged_in_client):
        """已登录用户访问定期交易列表返回 200"""
        resp = logged_in_client.get('/recurring/')
        assert resp.status_code == 200
        assert '定期交易'.encode() in resp.data or b'recurring' in resp.data


class TestAddRecurring:
    """POST /recurring/add 创建定期交易"""

    def test_create_monthly_recurring(self, logged_in_client, app):
        """成功创建月度定期交易"""
        resp = logged_in_client.post('/recurring/add', data={
            'name': '月租金',
            'amount': '5000.00',
            'type': 'expense',
            'frequency': 'monthly',
            'day_of_month': '1',
            'description': '每月房租'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '定期交易创建成功'.encode() in resp.data

        with app.app_context():
            item = RecurringTransaction.query.filter_by(name='月租金').first()
            assert item is not None
            assert float(item.amount) == 5000.00
            assert item.frequency == 'monthly'
            assert item.day_of_month == 1
            assert item.is_active is True

    def test_create_weekly_recurring(self, logged_in_client, app):
        """成功创建每周定期交易"""
        resp = logged_in_client.post('/recurring/add', data={
            'name': '周末聚餐',
            'amount': '200.00',
            'type': 'expense',
            'frequency': 'weekly',
            'day_of_week': '5',  # 周六
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '定期交易创建成功'.encode() in resp.data

        with app.app_context():
            item = RecurringTransaction.query.filter_by(name='周末聚餐').first()
            assert item is not None
            assert item.frequency == 'weekly'
            assert item.day_of_week == 5

    def test_create_custom_recurring(self, logged_in_client, app):
        """成功创建自定义周期定期交易"""
        resp = logged_in_client.post('/recurring/add', data={
            'name': '季度缴费',
            'amount': '1000.00',
            'type': 'expense',
            'frequency': 'custom',
            'interval_days': '90',
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '定期交易创建成功'.encode() in resp.data

        with app.app_context():
            item = RecurringTransaction.query.filter_by(name='季度缴费').first()
            assert item is not None
            assert item.frequency == 'custom'
            assert item.interval_days == 90

    def test_create_recurring_missing_fields(self, logged_in_client):
        """缺少必填字段返回错误"""
        resp = logged_in_client.post('/recurring/add', data={
            'name': '测试',
            # 缺少 amount, type, frequency
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '请填写所有必填字段'.encode() in resp.data


class TestToggleRecurring:
    """POST /recurring/<id>/toggle 切换启用/暂停"""

    def test_toggle_disable(self, logged_in_client, app):
        """暂停定期交易"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            item = RecurringTransaction(
                user_id=user.id,
                name='待暂停',
                amount=100.00,
                type='expense',
                frequency='monthly',
                next_run_date=date.today() + timedelta(days=10),
                is_active=True
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        resp = logged_in_client.post(f'/recurring/{item_id}/toggle', follow_redirects=True)
        assert resp.status_code == 200
        assert '暂停'.encode() in resp.data

        with app.app_context():
            item = RecurringTransaction.query.get(item_id)
            assert item.is_active is False

    def test_toggle_enable_with_expired_date(self, logged_in_client, app):
        """重新启用已过期的定期交易，next_run_date 更新为今天"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            item = RecurringTransaction(
                user_id=user.id,
                name='待启用',
                amount=100.00,
                type='expense',
                frequency='monthly',
                next_run_date=date.today() - timedelta(days=30),
                is_active=False
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        resp = logged_in_client.post(f'/recurring/{item_id}/toggle', follow_redirects=True)
        assert resp.status_code == 200
        assert '启用'.encode() in resp.data

        with app.app_context():
            item = RecurringTransaction.query.get(item_id)
            assert item.is_active is True
            assert item.next_run_date == date.today()


class TestDeleteRecurring:
    """POST /recurring/<id>/delete 删除定期交易"""

    def test_delete_success(self, logged_in_client, app):
        """成功删除定期交易"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            item = RecurringTransaction(
                user_id=user.id,
                name='待删除',
                amount=50.00,
                type='income',
                frequency='monthly',
                next_run_date=date.today(),
                is_active=True
            )
            db.session.add(item)
            db.session.commit()
            item_id = item.id

        resp = logged_in_client.post(f'/recurring/{item_id}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert '定期交易已删除'.encode() in resp.data

        with app.app_context():
            assert RecurringTransaction.query.get(item_id) is None

    def test_delete_nonexistent(self, logged_in_client):
        """删除不存在的定期交易返回 404"""
        resp = logged_in_client.post('/recurring/99999/delete')
        assert resp.status_code == 404

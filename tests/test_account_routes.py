"""账户管理路由测试"""
import pytest
from datetime import date
from models import db, Account, AccountType, AccountBalance, User


@pytest.fixture
def app_with_auth(app):
    """添加 before_request 登录检查的 app（模拟 main.py 行为）"""
    from flask import session, redirect, url_for, request

    @app.before_request
    def require_login():
        allowed_routes = ['auth.login', 'auth.register', 'static']
        if request.endpoint and request.endpoint not in allowed_routes:
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))

    return app


@pytest.fixture
def auth_client(app_with_auth):
    """未登录的测试客户端（含 before_request）"""
    return app_with_auth.test_client()


@pytest.fixture
def account_client(app):
    """已登录且有账户的测试客户端"""
    with app.app_context():
        user = User(username='acct_user', nickname='账户测试')
        user.set_password('Test1234')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        # 获取预设账户类型
        savings_type = AccountType.query.filter_by(category='savings').first()

        # 创建测试账户
        account = Account(
            user_id=user_id,
            name='测试储蓄卡',
            type_id=savings_type.id,
            currency='CNY',
            initial_balance=10000,
            current_balance=10000
        )
        db.session.add(account)
        db.session.commit()
        account_id = account.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    return client, user_id, account_id


class TestAccountListUnauth:
    """未登录访问账户页"""

    def test_redirect_to_login(self, auth_client):
        """未登录访问账户页应重定向到登录页"""
        resp = auth_client.get('/accounts/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']


class TestAccountList:
    """登录后访问账户页"""

    def test_accounts_page_200(self, logged_in_client):
        """登录后访问账户页返回 200"""
        resp = logged_in_client.get('/accounts/')
        assert resp.status_code == 200
        assert '资产总览' in resp.data.decode('utf-8')

    def test_accounts_page_with_view(self, logged_in_client):
        """个人视图参数正常工作"""
        resp = logged_in_client.get('/accounts/?view=personal')
        assert resp.status_code == 200


class TestCreateAccount:
    """创建账户"""

    def test_create_account_success(self, logged_in_client, app):
        """创建新账户成功并重定向"""
        with app.app_context():
            savings_type = AccountType.query.filter_by(category='savings').first()
            type_id = savings_type.id

        resp = logged_in_client.post('/accounts/create', data={
            'name': '新建测试账户',
            'type_id': type_id,
            'initial_balance': '5000',
            'currency': 'CNY'
        }, follow_redirects=False)

        assert resp.status_code == 302

        # 验证账户已创建
        with app.app_context():
            account = Account.query.filter_by(name='新建测试账户').first()
            assert account is not None
            assert float(account.initial_balance) == 5000.0
            assert account.currency == 'CNY'

    def test_create_account_missing_fields(self, logged_in_client):
        """缺少必填字段返回 400"""
        resp = logged_in_client.post('/accounts/create', data={
            'name': '',
            'type_id': ''
        })
        assert resp.status_code == 400


class TestAddSnapshot:
    """记录账户余额快照"""

    def test_add_snapshot_success(self, account_client, app):
        """录入月度余额快照成功"""
        client, user_id, account_id = account_client
        month_str = date.today().strftime('%Y-%m')

        resp = client.post(f'/accounts/{account_id}/snapshot', data={
            'balance': '12000',
            'month': month_str
        }, follow_redirects=False)

        assert resp.status_code == 302

        # 验证快照已保存
        with app.app_context():
            record_month = date.today().replace(day=1)
            snapshot = AccountBalance.query.filter_by(
                account_id=account_id, record_month=record_month
            ).first()
            assert snapshot is not None
            assert float(snapshot.balance) == 12000.0

            # 验证账户当前余额已更新
            account = Account.query.get(account_id)
            assert float(account.current_balance) == 12000.0

    def test_add_snapshot_missing_month(self, account_client):
        """缺少月份返回 400"""
        client, user_id, account_id = account_client

        resp = client.post(f'/accounts/{account_id}/snapshot', data={
            'balance': '12000'
        })
        assert resp.status_code == 400

    def test_add_snapshot_update_existing(self, account_client, app):
        """更新已有快照（同月份覆盖）"""
        client, user_id, account_id = account_client
        month_str = date.today().strftime('%Y-%m')

        # 第一次录入
        client.post(f'/accounts/{account_id}/snapshot', data={
            'balance': '12000',
            'month': month_str
        })
        # 第二次录入（覆盖）
        client.post(f'/accounts/{account_id}/snapshot', data={
            'balance': '15000',
            'month': month_str
        })

        with app.app_context():
            record_month = date.today().replace(day=1)
            snapshots = AccountBalance.query.filter_by(
                account_id=account_id, record_month=record_month
            ).all()
            assert len(snapshots) == 1
            assert float(snapshots[0].balance) == 15000.0


class TestDeleteAccount:
    """删除账户"""

    def test_delete_own_account(self, account_client, app):
        """删除自己的账户成功"""
        client, user_id, account_id = account_client

        resp = client.post(f'/accounts/{account_id}/delete', follow_redirects=False)
        assert resp.status_code == 302

        with app.app_context():
            account = Account.query.get(account_id)
            assert account is None

    def test_delete_others_account_forbidden(self, app):
        """不能删除他人账户"""
        with app.app_context():
            # 创建两个用户
            user1 = User(username='owner1', nickname='所有者')
            user1.set_password('Test1234')
            user2 = User(username='visitor1', nickname='访客')
            user2.set_password('Test1234')
            db.session.add_all([user1, user2])
            db.session.commit()

            savings_type = AccountType.query.filter_by(category='savings').first()
            account = Account(
                user_id=user1.id,
                name='别人的账户',
                type_id=savings_type.id,
                initial_balance=0,
                current_balance=0
            )
            db.session.add(account)
            db.session.commit()
            account_id = account.id
            visitor_id = user2.id

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = visitor_id

        resp = client.post(f'/accounts/{account_id}/delete')
        assert resp.status_code == 403


class TestBatchSnapshot:
    """批量快照"""

    def test_batch_snapshot_success(self, account_client, app):
        """批量录入多个账户快照"""
        client, user_id, account_id = account_client
        month_str = date.today().strftime('%Y-%m')

        resp = client.post('/accounts/batch-snapshot', data={
            'month': month_str,
            'view': 'personal',
            f'balance_{account_id}': '20000',
            f'note_{account_id}': '测试备注'
        }, follow_redirects=True)

        assert resp.status_code == 200

        with app.app_context():
            record_month = date.today().replace(day=1)
            snapshot = AccountBalance.query.filter_by(
                account_id=account_id, record_month=record_month
            ).first()
            assert snapshot is not None
            assert float(snapshot.balance) == 20000.0
            assert snapshot.note == '测试备注'

    def test_batch_snapshot_missing_month(self, account_client):
        """批量快照缺少月份参数"""
        client, user_id, account_id = account_client

        resp = client.post('/accounts/batch-snapshot', data={
            'view': 'personal',
            f'balance_{account_id}': '20000'
        }, follow_redirects=True)

        # 应重定向且 flash 错误提示
        assert resp.status_code == 200
        assert '请选择月份' in resp.data.decode('utf-8')

    def test_batch_snapshot_skip_empty(self, account_client, app):
        """批量快照跳过未填写的账户"""
        client, user_id, account_id = account_client
        month_str = date.today().strftime('%Y-%m')

        # 不提交任何 balance 数据
        resp = client.post('/accounts/batch-snapshot', data={
            'month': month_str,
            'view': 'personal'
        }, follow_redirects=True)

        assert resp.status_code == 200

        with app.app_context():
            record_month = date.today().replace(day=1)
            snapshots = AccountBalance.query.filter_by(
                account_id=account_id, record_month=record_month
            ).all()
            assert len(snapshots) == 0

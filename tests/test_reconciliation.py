"""对账助手功能测试"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from models import db, Account, AccountType, AccountBalance, Transaction


class TestReconciliationHelper:
    """批量快照弹窗中的对账助手（理论变化/预计余额/差额）"""

    def _setup_account_with_transactions(self, app, user_id):
        """设置测试账户 + 交易数据"""
        with app.app_context():
            at = AccountType.query.filter_by(category='savings').first()
            acct = Account(
                user_id=user_id, name='测试储蓄', type_id=at.id,
                currency='CNY', initial_balance=Decimal('50000'),
                current_balance=Decimal('50000')
            )
            db.session.add(acct)
            db.session.commit()

            # 上月快照
            this_month = date.today().replace(day=1)
            prev_month = this_month - relativedelta(months=1)
            snap = AccountBalance(
                account_id=acct.id, balance=Decimal('50000'),
                record_month=prev_month, recorded_by=user_id
            )
            db.session.add(snap)

            # 本月交易：收入 35000，支出 5000 → 理论变化 +30000
            t1 = Transaction(
                user_id=user_id, amount=Decimal('35000'), type='income',
                account_id=acct.id, transaction_date=this_month
            )
            t2 = Transaction(
                user_id=user_id, amount=Decimal('5000'), type='expense',
                account_id=acct.id, transaction_date=this_month
            )
            db.session.add_all([t1, t2])
            db.session.commit()
            return acct.id

    def test_batch_modal_has_reconciliation_columns(self, logged_in_client, app):
        """批量快照弹窗应包含理论变化、预计余额、差额列"""
        resp = logged_in_client.get('/accounts/')
        html = resp.data.decode()
        assert '理论变化' in html
        assert '预计余额' in html
        assert '差额' in html

    def test_theory_change_calculation(self, logged_in_client, app):
        """理论变化 = 本月收入合计 - 本月支出合计（按账户）"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            user_id = user.id

        self._setup_account_with_transactions(app, user_id)

        resp = logged_in_client.get('/accounts/')
        html = resp.data.decode()

        # 理论变化应为 +30,000（收入35000 - 支出5000）
        assert '+30,000' in html

    def test_expected_balance_calculation(self, logged_in_client, app):
        """预计余额 = 上月余额 + 理论变化"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            user_id = user.id

        self._setup_account_with_transactions(app, user_id)

        resp = logged_in_client.get('/accounts/')
        html = resp.data.decode()

        # 预计余额应为 80,000（50000 + 30000）
        assert '80,000' in html
        # data-expected 属性用于 JS 差额计算
        assert 'data-expected="80000.0"' in html

    def test_diff_js_function_exists(self, logged_in_client, app):
        """页面应包含 calcDiff JS 函数"""
        resp = logged_in_client.get('/accounts/')
        html = resp.data.decode()
        assert 'function calcDiff(input)' in html

    def test_no_prev_snapshot_shows_dash(self, logged_in_client, app):
        """无上月快照时，理论变化和预计余额显示 —"""
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            at = AccountType.query.filter_by(category='savings').first()
            # 创建账户但不录入上月快照
            acct = Account(
                user_id=user.id, name='新账户', type_id=at.id,
                currency='CNY', initial_balance=Decimal('0'),
                current_balance=Decimal('0')
            )
            db.session.add(acct)
            db.session.commit()

        resp = logged_in_client.get('/accounts/')
        html = resp.data.decode()
        # 无上月快照，data-expected 应为空
        assert 'data-expected=""' in html

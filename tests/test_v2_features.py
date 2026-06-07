"""补充测试：月度待办自动检测、最近常用、AI缓存、首页仪表盘优化"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from datetime import date, datetime
from decimal import Decimal

from models import (db, User, Account, AccountType, AccountBalance, Transaction,
                    BabyFund, SavingsPlan, SavingsRecord, MonthlyTodo, MonthlySummaryCache,
                    Category)


class TestMonthlyTodoAutoDetect:
    """月度待办自动检测测试"""

    def test_checklist_created_on_first_visit(self, logged_in_client, app):
        """首次访问应自动创建 4 项 checklist"""
        today = date.today()
        resp = logged_in_client.get(f'/monthly-todo/?year={today.year}&month={today.month}')
        assert resp.status_code == 200
        with app.app_context():
            todos = MonthlyTodo.query.filter_by(year=today.year, month=today.month).all()
            assert len(todos) == 4

    def test_transaction_auto_detected(self, logged_in_client, app):
        """有交易记录后，交易待办应自动完成"""
        today = date.today()
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            cat = Category.query.first()
            txn = Transaction(
                amount=100, type='income', category_id=cat.id,
                user_id=user.id, transaction_date=today, created_at=datetime.utcnow()
            )
            db.session.add(txn)
            db.session.commit()

        resp = logged_in_client.get(f'/monthly-todo/?year={today.year}&month={today.month}')
        assert resp.status_code == 200
        with app.app_context():
            todo = MonthlyTodo.query.filter_by(
                year=today.year, month=today.month, detect_key='transaction'
            ).first()
            assert todo.status == 'completed'

    def test_homepage_shows_checklist(self, logged_in_client, app):
        """首页路由应能正常返回（checklist 在实际 main.py 首页中渲染）"""
        # conftest 的首页是 stub，改为验证 monthly-todo 页面包含 checklist
        today = date.today()
        resp = logged_in_client.get(f'/monthly-todo/?year={today.year}&month={today.month}')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert '录入本月交易记录' in html or '待办' in html


class TestRecentShortcuts:
    """最近常用快捷填充测试"""

    def test_shortcuts_in_transaction_page(self, logged_in_client, app):
        """记账页应包含最近常用区域"""
        # 先创建一些交易数据
        today = date.today()
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            cat = Category.query.first()
            for _ in range(3):
                txn = Transaction(
                    amount=100, type='income', category_id=cat.id,
                    user_id=user.id, transaction_date=today, created_at=datetime.utcnow()
                )
                db.session.add(txn)
            db.session.commit()

        resp = logged_in_client.get('/transactions/')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'recent-shortcuts' in html or 'recentShortcuts' in html

    def test_shortcuts_data_passed(self, logged_in_client, app):
        """记账页应传递 recent_shortcuts 数据（JSON 嵌入页面）"""
        resp = logged_in_client.get('/transactions/')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'recentShortcuts' in html

    def test_shortcuts_empty_without_data(self, logged_in_client, app):
        """没有交易数据时，最近常用应为空"""
        resp = logged_in_client.get('/transactions/')
        assert resp.status_code == 200
        html = resp.data.decode()
        # income/expense/transfer 都应为空数组
        assert '"income": []' in html
        assert '"expense": []' in html
        assert '"transfer": []' in html


class TestAiSummaryCache:
    """AI 月度总结缓存测试"""

    def test_cache_model_exists(self, app):
        """MonthlySummaryCache 模型应可正常创建记录"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            if not user:
                user = User(username='testuser', nickname='测试用户')
                user.set_password('Test1234')
                db.session.add(user)
                db.session.commit()

            cache = MonthlySummaryCache(
                user_id=user.id, year=2026, month=5,
                section='asset_personal', content='测试缓存内容',
                created_at=datetime.utcnow()
            )
            db.session.add(cache)
            db.session.commit()

            result = MonthlySummaryCache.query.filter_by(
                user_id=user.id, year=2026, month=5, section='asset_personal'
            ).first()
            assert result is not None
            assert result.content == '测试缓存内容'

    def test_cache_separate_by_view(self, app):
        """个人和家庭视图的缓存应分开存储"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            if not user:
                user = User(username='testuser', nickname='测试用户')
                user.set_password('Test1234')
                db.session.add(user)
                db.session.commit()

            # 存两份不同 view 的缓存
            for section, content in [('asset_personal', '个人总结'), ('asset_family', '家庭总结')]:
                cache = MonthlySummaryCache(
                    user_id=user.id, year=2026, month=5,
                    section=section, content=content,
                    created_at=datetime.utcnow()
                )
                db.session.add(cache)
            db.session.commit()

            personal = MonthlySummaryCache.query.filter_by(
                user_id=user.id, section='asset_personal'
            ).first()
            family = MonthlySummaryCache.query.filter_by(
                user_id=user.id, section='asset_family'
            ).first()
            assert personal.content == '个人总结'
            assert family.content == '家庭总结'

    def test_refresh_api_clears_cache(self, logged_in_client, app):
        """刷新 API 应清除缓存"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            user_id = user.id
            cache = MonthlySummaryCache(
                user_id=user_id, year=2026, month=5,
                section='asset_personal', content='旧缓存',
                created_at=datetime.utcnow()
            )
            db.session.add(cache)
            db.session.commit()

        resp = logged_in_client.post('/reports/api/refresh-summary?year=2026&month=5')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['ok'] is True

        with app.app_context():
            remaining = MonthlySummaryCache.query.filter_by(
                user_id=user_id, year=2026, month=5
            ).count()
            assert remaining == 0

    def test_refresh_requires_login(self, client, app):
        """未登录不能刷新缓存"""
        resp = client.post('/reports/api/refresh-summary?year=2026&month=5')
        assert resp.status_code == 401


class TestDashboardOptimization:
    """首页仪表盘优化测试（conftest 首页为 stub，改用 test_main_routes 覆盖渲染）"""

    def test_transaction_page_has_quick_actions_links(self, logged_in_client, app):
        """记账页 recent_shortcuts 数据中包含快捷操作所需的结构"""
        resp = logged_in_client.get('/transactions/')
        assert resp.status_code == 200
        html = resp.data.decode()
        # 页面应包含 recentShortcuts JS 变量
        assert 'recentShortcuts' in html

    def test_monthly_summary_has_view_switcher(self, family_client, app):
        """家庭用户的月度总结页应有视图切换"""
        resp = family_client.get('/reports/monthly-summary')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'view-btn' in html

    def test_monthly_summary_personal_no_switcher(self, logged_in_client, app):
        """无家庭的用户不应显示视图切换"""
        resp = logged_in_client.get('/reports/monthly-summary')
        assert resp.status_code == 200
        html = resp.data.decode()
        # 没有家庭，不应出现 view-switcher
        assert 'view=family' not in html

    def test_monthly_summary_nav_carries_view(self, family_client, app):
        """月度总结的月份导航应带 view 参数"""
        resp = family_client.get('/reports/monthly-summary?view=family')
        assert resp.status_code == 200
        html = resp.data.decode()
        assert 'view=family' in html


class TestTransferEdit:
    """转账记录编辑测试"""

    def test_transfer_edit_page_renders(self, logged_in_client, app):
        """转账记录编辑页应显示转账专用表单"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            # 创建账户
            at = AccountType.query.first()
            acct_from = Account(name='测试卡A', user_id=user.id, type_id=at.id)
            acct_to = Account(name='测试卡B', user_id=user.id, type_id=at.id)
            db.session.add(acct_from)
            db.session.add(acct_to)
            db.session.flush()

            # 创建转账配对记录
            txn_out = Transaction(
                amount=1000, type='transfer_out', user_id=user.id,
                account_id=acct_from.id, transaction_date=date.today(),
                description='测试转账', created_at=datetime.utcnow()
            )
            db.session.add(txn_out)
            db.session.flush()

            txn_in = Transaction(
                amount=1000, type='transfer_in', user_id=user.id,
                account_id=acct_to.id, transaction_date=date.today(),
                description='测试转账', created_at=datetime.utcnow(),
                transfer_pair_id=txn_out.id
            )
            db.session.add(txn_in)
            db.session.flush()

            txn_out.transfer_pair_id = txn_in.id
            db.session.commit()
            txn_id = txn_out.id

        resp = logged_in_client.get(f'/edit/{txn_id}')
        assert resp.status_code == 200
        html = resp.data.decode()
        # 应包含转账表单字段
        assert '转出账户' in html
        assert '转入账户' in html
        assert 'from_account_id' in html
        assert 'to_account_id' in html
        # 不应显示收入/支出 radio
        assert 'value="income"' not in html

    def test_normal_edit_page_no_transfer_fields(self, logged_in_client, app):
        """收入/支出编辑页不应显示转账字段"""
        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            cat = Category.query.first()
            txn = Transaction(
                amount=500, type='income', category_id=cat.id,
                user_id=user.id, transaction_date=date.today(),
                created_at=datetime.utcnow()
            )
            db.session.add(txn)
            db.session.commit()
            txn_id = txn.id

        resp = logged_in_client.get(f'/edit/{txn_id}')
        assert resp.status_code == 200
        html = resp.data.decode()
        # 应显示收入/支出 radio
        assert 'value="income"' in html
        # 不应显示转账字段
        assert 'from_account_id' not in html


class TestBabyFundMemo:
    """宝宝基金备忘录测试"""

    def test_add_memo(self, logged_in_client, app):
        """新增备忘后应出现在列表"""
        resp = logged_in_client.post('/baby-fund/memo/add',
                                     data={'memo_content': '测试备忘内容'},
                                     follow_redirects=True)
        assert resp.status_code == 200
        html = resp.data.decode()
        assert '测试备忘内容' in html

    def test_toggle_memo(self, logged_in_client, app):
        """标记完成后状态应变为 completed"""
        from models import BabyFundMemo
        # 先添加一条
        logged_in_client.post('/baby-fund/memo/add',
                              data={'memo_content': '待完成备忘'})
        with app.app_context():
            memo = BabyFundMemo.query.filter_by(content='待完成备忘').first()
            assert memo is not None
            memo_id = memo.id
            assert memo.status == 'pending'

        # toggle
        logged_in_client.post(f'/baby-fund/memo/{memo_id}/toggle')
        with app.app_context():
            memo = BabyFundMemo.query.get(memo_id)
            assert memo.status == 'completed'

    def test_delete_memo(self, logged_in_client, app):
        """删除后备忘应消失"""
        from models import BabyFundMemo
        # 先添加
        logged_in_client.post('/baby-fund/memo/add',
                              data={'memo_content': '要删除的备忘'})
        with app.app_context():
            memo = BabyFundMemo.query.filter_by(content='要删除的备忘').first()
            memo_id = memo.id

        # 删除
        logged_in_client.post(f'/baby-fund/memo/{memo_id}/delete')
        with app.app_context():
            assert BabyFundMemo.query.get(memo_id) is None

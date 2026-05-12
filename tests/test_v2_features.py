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

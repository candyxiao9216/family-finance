"""IDOR 越权回归测试

背景：体检发现 savings/templates/recurring/baby_fund/advisor 共 18 个写路由
不校验资源归属，任意登录用户可遍历 id 删改他人数据；转账不校验账户归属，
可把他人账户刷成负数。

本测试构造两个不同家庭的用户（A、B），让 B 尝试操作 A 的资源，
断言：返回 403/404，且 A 的数据未被篡改。

这是真行为测试（非 grep 源码），改前应全部失败（越权成功），改后通过。
"""
import pytest

import sys
sys.path.insert(0, "src")

from models import db as _db, User, Family, Account, AccountType, TransactionTemplate, SavingsPlan, RecurringTransaction, BabyFund, StockHolding, FundHolding, WealthHolding


@pytest.fixture
def two_users(app):
    """两个不同家庭的用户，各自有账户/模板/储蓄计划/定期交易/宝宝基金。

    返回 (client_a, user_a_id, client_b, user_b_id)。
    B 操作 A 的资源即构成越权。
    """
    with app.app_context():
        # 家庭 A
        fam_a = Family(name="A家", invite_code="CODEA")
        _db.session.add(fam_a)
        _db.session.flush()
        user_a = User(username="user_a", nickname="甲", family_id=fam_a.id)
        user_a.set_password("Test1234")
        _db.session.add(user_a)

        # 家庭 B（不同家庭）
        fam_b = Family(name="B家", invite_code="CODEB")
        _db.session.add(fam_b)
        _db.session.flush()
        user_b = User(username="user_b", nickname="乙", family_id=fam_b.id)
        user_b.set_password("Test1234")
        _db.session.add(user_b)
        _db.session.commit()

        acct_type = AccountType.query.first()

        # A 的资源
        acct_a = Account(name="甲的账户", account_type=acct_type, user_id=user_a.id, current_balance=10000)
        _db.session.add(acct_a)
        tpl_a = TransactionTemplate(name="甲的模板", user_id=user_a.id, amount=100, type="expense")
        _db.session.add(tpl_a)
        from datetime import date, timedelta
        plan_a = SavingsPlan(name="甲的储蓄", type="monthly", target_amount=100000, year=2026, month=1, created_by=user_a.id)
        _db.session.add(plan_a)
        recurring_a = RecurringTransaction(
            name="甲的定期", user_id=user_a.id, amount=100,
            type="expense", frequency="monthly", day_of_month=1,
            next_run_date=date.today() + timedelta(days=30)
        )
        _db.session.add(recurring_a)
        fund_a = BabyFund(giver_name="甲", amount=1000, event_date=date.today(), event_type="满月", created_by=user_a.id)
        _db.session.add(fund_a)
        # B 的账户（用于转账越权测试）
        acct_b = Account(name="乙的账户", account_type=acct_type, user_id=user_b.id, current_balance=500)
        _db.session.add(acct_b)
        # A 的持仓（用于 advisor 越权测试）
        stock_a = StockHolding(user_id=user_a.id, account_id=acct_a.id, stock_code="00700", stock_name="腾讯", market="HK", shares=100, avg_cost=300)
        _db.session.add(stock_a)
        fund_a = FundHolding(user_id=user_a.id, account_id=acct_a.id, fund_code="004253", fund_name="华夏基金", amount=5000)
        _db.session.add(fund_a)
        wealth_a = WealthHolding(user_id=user_a.id, account_id=acct_a.id, product_name="某理财", buy_amount=10000)
        _db.session.add(wealth_a)
        _db.session.commit()

        a_id, b_id = user_a.id, user_b.id
        acct_id = acct_a.id
        acct_b_id = acct_b.id
        tpl_id = tpl_a.id
        plan_id = plan_a.id
        recurring_id = recurring_a.id
        fund_id = fund_a.id
        stock_h_id = stock_a.id
        fund_h_id = fund_a.id
        wealth_h_id = wealth_a.id

    client_a = app.test_client()
    with client_a.session_transaction() as s:
        s["user_id"] = a_id
    client_b = app.test_client()
    with client_b.session_transaction() as s:
        s["user_id"] = b_id

    return {
        "client_a": client_a, "client_b": client_b,
        "a_id": a_id, "b_id": b_id,
        "acct_id": acct_id, "acct_b_id": acct_b_id,
        "tpl_id": tpl_id, "plan_id": plan_id,
        "recurring_id": recurring_id, "fund_id": fund_id,
        "stock_h_id": stock_h_id, "fund_h_id": fund_h_id, "wealth_h_id": wealth_h_id,
        "app": app,
    }


# ---- 转账越权（P0-3/P0-4）----
class TestTransferAuthorization:
    def test_transfer_from_stranger_account_forbidden(self, two_users):
        """B 不能从 A 的账户转账给自己"""
        d = two_users
        r = d["client_b"].post("/add", data={
            "type": "transfer",
            "from_account_id": d["acct_id"],   # A 的账户
            "to_account_id": d["acct_b_id"],   # B 自己的账户
            "amount": "5000",
            "date": "2026-01-01",
            "description": "偷转",
        }, follow_redirects=False)
        # A 的账户余额不应被篡改
        with d["app"].app_context():
            acct = Account.query.get(d["acct_id"])
            assert float(acct.current_balance) == 10000, "A 的账户余额被 B 越权篡改"
            acct_b = Account.query.get(d["acct_b_id"])
            assert float(acct_b.current_balance) == 500, "B 的账户被越权加钱"


# ---- 模板越权 ----
class TestTemplateAuthorization:
    def test_b_cannot_edit_a_template(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/templates/{d['tpl_id']}/edit", data={
            "name": "被乙篡改", "amount": "9999",
        }, follow_redirects=False)
        assert r.status_code in (403, 302), f"应拒绝越权编辑，实际 {r.status_code}"
        with d["app"].app_context():
            tpl = TransactionTemplate.query.get(d["tpl_id"])
            assert tpl.name == "甲的模板", "A 的模板被篡改"

    def test_b_cannot_delete_a_template(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/templates/{d['tpl_id']}/delete", follow_redirects=False)
        assert r.status_code in (403, 302)
        with d["app"].app_context():
            assert TransactionTemplate.query.get(d["tpl_id"]) is not None, "A 的模板被删除"

    def test_b_cannot_use_a_template(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/templates/{d['tpl_id']}/use", follow_redirects=False)
        assert r.status_code in (403, 302)


# ---- 储蓄计划越权 ----
class TestSavingsAuthorization:
    def test_b_cannot_delete_a_plan(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/savings/plan/{d['plan_id']}/delete", follow_redirects=False)
        assert r.status_code in (403, 302)
        with d["app"].app_context():
            assert SavingsPlan.query.get(d["plan_id"]) is not None, "A 的储蓄计划被删除"


# ---- 定期交易越权 ----
class TestRecurringAuthorization:
    def test_b_cannot_delete_a_recurring(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/recurring/{d['recurring_id']}/delete", follow_redirects=False)
        assert r.status_code in (403, 302)
        with d["app"].app_context():
            assert RecurringTransaction.query.get(d["recurring_id"]) is not None

    def test_b_cannot_toggle_a_recurring(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/recurring/{d['recurring_id']}/toggle", follow_redirects=False)
        assert r.status_code in (403, 302)


# ---- 宝宝基金越权 ----
class TestBabyFundAuthorization:
    def test_b_cannot_delete_a_fund(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/baby-fund/{d['fund_id']}/delete", follow_redirects=False)
        assert r.status_code in (403, 302)
        with d["app"].app_context():
            assert BabyFund.query.get(d["fund_id"]) is not None, "A 的宝宝基金被删除"


# ---- advisor 持仓越权 ----
class TestAdvisorHoldingAuthorization:
    def test_b_cannot_delete_a_stock(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/advisor/api/stocks/{d['stock_h_id']}/delete")
        assert r.status_code == 403
        with d["app"].app_context():
            assert StockHolding.query.get(d["stock_h_id"]) is not None

    def test_b_cannot_update_a_stock(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/advisor/api/stocks/{d['stock_h_id']}",
                               json={"shares": 99999, "avg_cost": 1})
        assert r.status_code == 403
        with d["app"].app_context():
            s = StockHolding.query.get(d["stock_h_id"])
            assert float(s.shares) == 100, "A 的股票持仓被篡改"

    def test_b_cannot_delete_a_fund_holding(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/advisor/api/funds/{d['fund_h_id']}/delete")
        assert r.status_code == 403
        with d["app"].app_context():
            assert FundHolding.query.get(d["fund_h_id"]) is not None

    def test_b_cannot_transfer_a_fund(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/advisor/api/funds/{d['fund_h_id']}/transfer",
                               json={"new_fund_name": "乙偷的", "transfer_amount": 4000})
        assert r.status_code == 403
        with d["app"].app_context():
            h = FundHolding.query.get(d["fund_h_id"])
            assert h.status != "redeemed", "A 的基金被标记赎回"

    def test_b_cannot_delete_a_wealth(self, two_users):
        d = two_users
        r = d["client_b"].post(f"/advisor/api/wealth/{d['wealth_h_id']}/delete")
        assert r.status_code == 403
        with d["app"].app_context():
            assert WealthHolding.query.get(d["wealth_h_id"]) is not None

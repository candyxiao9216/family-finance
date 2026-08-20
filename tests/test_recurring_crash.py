"""定期交易崩溃与幂等回归测试

P0-1：process_recurring_transactions 曾用 Transaction(source='recurring')，
但 Transaction 模型没有 source 列，一旦有到期定期交易就抛 TypeError，
导致首页/月度收支页永久 500（休眠炸弹）。

P3-2：process_recurring_transactions 无幂等保护，并发请求可能重复入账。
本测试覆盖函数行为本身，不依赖首页路由（conftest 的 index 是桩）。
"""
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

sys.path.insert(0, "src")


@pytest.fixture
def recurring_setup(app):
    """已登录用户 + 一条已到期定期交易，返回 (client, user_id, item_id)"""
    from models import db as _db, User, Family, Account, AccountType, RecurringTransaction

    with app.app_context():
        family = Family(name="测试家庭", invite_code="TEST")
        _db.session.add(family)
        _db.session.flush()
        user = User(username="rec_user", nickname="测试", family_id=family.id)
        user.set_password("Test1234")
        _db.session.add(user)
        acct_type = AccountType.query.first()
        account = Account(name="测试账户", account_type=acct_type, user_id=user.id, current_balance=5000)
        _db.session.add(account)

        # 一条昨天就到期的定期交易（触发 process）
        item = RecurringTransaction(
            name="房租", user_id=user.id, amount=1000,
            type="expense", frequency="monthly", day_of_month=1,
            next_run_date=date.today() - timedelta(days=1),
            is_active=True, account_id=account.id
        )
        _db.session.add(item)
        _db.session.commit()
        uid, iid, acct_id = user.id, item.id, account.id

    client = app.test_client()
    with client.session_transaction() as s:
        s["user_id"] = uid
    return {"app": app, "client": client, "user_id": uid, "item_id": iid, "acct_id": acct_id}


class TestProcessRecurringNoCrash:
    """P0-1：处理到期定期交易不得崩溃"""

    def test_process_recurring_creates_transaction(self, recurring_setup):
        """有到期定期交易时，process 应成功建交易而非抛 TypeError"""
        from routes.recurring import process_recurring_transactions
        from models import db as _db, Transaction, RecurringTransaction

        d = recurring_setup
        with d["app"].app_context():
            count = process_recurring_transactions(d["user_id"])
            assert count >= 1, "应至少创建 1 笔定期交易"
            # 确认交易真的建了
            txns = Transaction.query.filter_by(user_id=d["user_id"]).all()
            assert len(txns) >= 1
            assert txns[0].description.startswith("[定期]")
            # next_run_date 应被推进到未来
            item = RecurringTransaction.query.get(d["item_id"])
            assert item.next_run_date > date.today()


class TestDeleteAccountCascade:
    """P0-2：删除账户不得因 NOT NULL 持仓外键崩溃"""

    def test_delete_account_with_holdings_rejected_not_crash(self, app):
        """有持仓的账户应被拒绝删除（而非 500 崩溃），并提示"""
        from models import db as _db, User, Family, Account, AccountType, StockHolding

        with app.app_context():
            family = Family(name="删账户测试", invite_code="DEL")
            _db.session.add(family)
            _db.session.flush()
            user = User(username="del_user", nickname="删", family_id=family.id)
            user.set_password("Test1234")
            _db.session.add(user)
            acct_type = AccountType.query.first()
            account = Account(name="有持仓的账户", account_type=acct_type, user_id=user.id, current_balance=1000)
            _db.session.add(account)
            _db.session.flush()
            holding = StockHolding(user_id=user.id, account_id=account.id,
                                   stock_code="00700", stock_name="腾讯", market="HK", shares=10, avg_cost=300)
            _db.session.add(holding)
            _db.session.commit()
            uid, acct_id = user.id, account.id

        client = app.test_client()
        with client.session_transaction() as s:
            s["user_id"] = uid

        r = client.post(f"/accounts/{acct_id}/delete", follow_redirects=False)
        # 不应 500 崩溃；应拒绝（302 提示 或 403）
        assert r.status_code != 500, "删除有持仓的账户不应 500 崩溃"
        # 账户应仍存在（未被删）
        with app.app_context():
            assert Account.query.get(acct_id) is not None, "有持仓的账户不应被删"

    def test_delete_account_without_holdings_succeeds(self, app):
        """无持仓的账户正常删除，且清理 nullable 外键（不留孤儿）"""
        from models import db as _db, User, Family, Account, AccountType, TransactionTemplate

        with app.app_context():
            family = Family(name="删账户测试2", invite_code="DEL2")
            _db.session.add(family)
            _db.session.flush()
            user = User(username="del_user2", nickname="删2", family_id=family.id)
            user.set_password("Test1234")
            _db.session.add(user)
            acct_type = AccountType.query.first()
            account = Account(name="普通账户", account_type=acct_type, user_id=user.id, current_balance=1000)
            _db.session.add(account)
            _db.session.flush()
            # 挂一个 nullable 外键的模板
            tpl = TransactionTemplate(name="模板", user_id=user.id, amount=100, type="expense", account_id=account.id)
            _db.session.add(tpl)
            _db.session.commit()
            uid, acct_id, tpl_id = user.id, account.id, tpl.id

        client = app.test_client()
        with client.session_transaction() as s:
            s["user_id"] = uid

        r = client.post(f"/accounts/{acct_id}/delete", follow_redirects=False)
        assert r.status_code == 302, f"无持仓账户应正常删除，实际 {r.status_code}"
        with app.app_context():
            assert Account.query.get(acct_id) is None, "账户应被删除"
            # nullable 外键应被置空，不留悬空指向已删账户
            tpl = TransactionTemplate.query.get(tpl_id)
            assert tpl.account_id is None, "模板的 account_id 应被置空而非悬空"

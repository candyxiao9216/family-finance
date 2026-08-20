"""转账写 AccountBalance 一致性测试（P1-1）

背景：转账在 add / edit / delete 三处各写一遍余额与快照逻辑，导致
- edit 路径删旧 AccountBalance 用"回滚后余额"匹配，条件永远不成立，
  旧记录删不掉；且只改余额不插新记录 → 快照历史与 current_balance 脱钩
- 这是 v2.1.13/14 修过的 transfer 覆盖问题第三次重现（前两次在快照写入路径）

本测试守护不变量：add/edit/delete 后，AccountBalance 记录与
Account.current_balance 必须一致，且同月 transfer 记录数正确。
"""
from datetime import date
from decimal import Decimal

import pytest

import sys
sys.path.insert(0, "src")

from models import db as _db, User, Family, Account, AccountType, AccountBalance


@pytest.fixture
def transfer_setup(app):
    """已登录用户 + 两个账户（A 余额 10000，B 余额 5000）"""
    with app.app_context():
        family = Family(name="转账测试", invite_code="TF")
        _db.session.add(family)
        _db.session.flush()
        user = User(username="tf_user", nickname="转", family_id=family.id)
        user.set_password("Test1234")
        _db.session.add(user)
        acct_type = AccountType.query.first()
        acct_a = Account(name="A", account_type=acct_type, user_id=user.id, current_balance=10000)
        acct_b = Account(name="B", account_type=acct_type, user_id=user.id, current_balance=5000)
        _db.session.add_all([acct_a, acct_b])
        _db.session.commit()
        uid, a_id, b_id = user.id, acct_a.id, acct_b.id

    client = app.test_client()
    with client.session_transaction() as s:
        s["user_id"] = uid
    return {"app": app, "client": client, "uid": uid, "a_id": a_id, "b_id": b_id}


def _transfer_balances(app, account_id, month=None):
    """返回某账户某月（默认本月）的 transfer AccountBalance 记录数"""
    with app.app_context():
        q = AccountBalance.query.filter_by(account_id=account_id, source='transfer')
        if month:
            q = q.filter_by(record_month=month)
        return q.all()


class TestTransferAddConsistency:
    def test_add_transfer_inserts_two_balance_records(self, transfer_setup):
        """新增转账：两个账户各插一条 transfer 记录，余额正确更新"""
        d = transfer_setup
        r = d["client"].post("/add", data={
            "type": "transfer",
            "from_account_id": d["a_id"],
            "to_account_id": d["b_id"],
            "amount": "2000",
            "date": "2026-01-15",
            "description": "测试转账",
        }, follow_redirects=False)
        assert r.status_code == 302
        with d["app"].app_context():
            a = Account.query.get(d["a_id"])
            b = Account.query.get(d["b_id"])
            assert float(a.current_balance) == 8000
            assert float(b.current_balance) == 7000
            # 每账户一条 transfer 记录
            assert len(_transfer_balances(d["app"], d["a_id"])) == 1
            assert len(_transfer_balances(d["app"], d["b_id"])) == 1


class TestTransferEditConsistency:
    def test_edit_transfer_amount_updates_balance_and_records(self, transfer_setup):
        """编辑转账金额：旧 AccountBalance 应被替换，余额与记录一致（P1-1 核心）"""
        d = transfer_setup
        # 先建一笔 2000 的转账
        d["client"].post("/add", data={
            "type": "transfer", "from_account_id": d["a_id"], "to_account_id": d["b_id"],
            "amount": "2000", "date": "2026-01-15", "description": "原转账",
        }, follow_redirects=False)
        with d["app"].app_context():
            txn = _db.session.query(_db.metadata.tables['transactions']).filter_by(
                type='transfer_out').first()
            txn_id = txn.id

        # 改成 3000
        r = d["client"].post(f"/edit/{txn_id}", data={
            "type": "transfer", "from_account_id": d["a_id"], "to_account_id": d["b_id"],
            "amount": "3000", "date": "2026-01-15", "description": "改后转账",
        }, follow_redirects=False)
        assert r.status_code == 302

        with d["app"].app_context():
            a = Account.query.get(d["a_id"])
            b = Account.query.get(d["b_id"])
            # 余额应反映 3000，而非 2000
            assert float(a.current_balance) == 7000, f"A 余额应为 7000，实际 {a.current_balance}"
            assert float(b.current_balance) == 8000, f"B 余额应为 8000，实际 {b.current_balance}"
            # 关键：transfer 记录数应仍是 1（旧的被替换，不应残留成 2）
            a_records = _transfer_balances(d["app"], d["a_id"])
            b_records = _transfer_balances(d["app"], d["b_id"])
            assert len(a_records) == 1, f"A 的 transfer 记录应为 1 条，实际 {len(a_records)}"
            assert len(b_records) == 1, f"B 的 transfer 记录应为 1 条，实际 {len(b_records)}"
            # 记录的 change_amount 应是新金额
            assert float(a_records[0].change_amount) == -3000
            assert float(b_records[0].change_amount) == 3000


class TestTransferDeleteConsistency:
    def test_delete_transfer_rolls_back_balance_and_records(self, transfer_setup):
        """删除转账：余额回滚，transfer 记录被删"""
        d = transfer_setup
        d["client"].post("/add", data={
            "type": "transfer", "from_account_id": d["a_id"], "to_account_id": d["b_id"],
            "amount": "2000", "date": "2026-01-15", "description": "待删转账",
        }, follow_redirects=False)
        with d["app"].app_context():
            txn = _db.session.query(_db.metadata.tables['transactions']).filter_by(
                type='transfer_out').first()
            txn_id = txn.id

        r = d["client"].post(f"/delete/{txn_id}", follow_redirects=False)
        assert r.status_code == 302

        with d["app"].app_context():
            a = Account.query.get(d["a_id"])
            b = Account.query.get(d["b_id"])
            # 余额应回到初始
            assert float(a.current_balance) == 10000
            assert float(b.current_balance) == 5000
            # transfer 记录应被删
            assert len(_transfer_balances(d["app"], d["a_id"])) == 0
            assert len(_transfer_balances(d["app"], d["b_id"])) == 0

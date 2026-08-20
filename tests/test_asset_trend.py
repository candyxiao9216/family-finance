"""资产趋势 API 重复求和测试（P1-2）

背景：AccountBalance 同账户同月可有多行（1 行 snapshot + N 行 transfer），
balance 字段是「变更后快照余额」非增量。reports.api_trend 直接 SUM(balance)
会把同一笔钱数 N 遍，资产曲线翻倍。account.py:59 和 monthly_todo.py:157
都正确用了 source=='snapshot' 过滤，唯独此 API 漏了。

错误数据还会经 _get_ai_summary 喂给 AI 月度总结并长期缓存。
"""
import pytest

import sys
sys.path.insert(0, "src")

from models import db as _db, User, Family, Account, AccountType, AccountBalance


@pytest.fixture
def trend_setup(app):
    """已登录用户 + 一个账户：本月有一条 snapshot(余额 900) + 一条 transfer(余额 800)"""
    with app.app_context():
        family = Family(name="趋势测试", invite_code="TR")
        _db.session.add(family)
        _db.session.flush()
        user = User(username="tr_user", nickname="趋", family_id=family.id)
        user.set_password("Test1234")
        _db.session.add(user)
        acct_type = AccountType.query.filter_by(category='savings').first()
        account = Account(name="测试账户", account_type=acct_type, user_id=user.id,
                          current_balance=800, type_id=acct_type.id)
        _db.session.add(account)
        _db.session.flush()
        from datetime import date
        this_month = date.today().replace(day=1)
        # 快照记录：余额 900
        _db.session.add(AccountBalance(
            account_id=account.id, balance=900, change_amount=900,
            record_month=this_month, source='snapshot', recorded_by=user.id
        ))
        # 转账记录：余额 800（transfer 后）
        _db.session.add(AccountBalance(
            account_id=account.id, balance=800, change_amount=-100,
            record_month=this_month, source='transfer', recorded_by=user.id
        ))
        _db.session.commit()
        uid, acct_id = user.id, account.id

    client = app.test_client()
    with client.session_transaction() as s:
        s["user_id"] = uid
    return {"app": app, "client": client, "uid": uid, "acct_id": acct_id}


class TestAssetTrendNoDoubleCount:
    def test_trend_does_not_sum_transfer_and_snapshot(self, trend_setup):
        """资产趋势应只取 snapshot，不把 transfer 重复相加"""
        d = trend_setup
        r = d["client"].get("/reports/api/asset-trend?months=3")
        assert r.status_code == 200
        data = r.get_json()
        # 真实资产应取 snapshot 的 900，而非 900+800=1700
        assert data.get("savings"), f"应有 savings 数据，实际 {data}"
        # savings 各月之和不应包含 transfer
        total_savings = sum(float(x) for x in data["savings"])
        assert total_savings == 900.0, (
            f"资产应只计 snapshot=900，实际 {total_savings}（疑似把 transfer 重复相加）"
        )

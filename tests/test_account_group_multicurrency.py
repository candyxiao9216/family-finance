"""分组汇总多币种换算测试

验证：同一分组下存在不同币种子账户时，分组汇总行的各金额列
（上月余额、理论变化、预计余额）均统一换算为分组显示币种后再相加。
"""
import pytest
from unittest.mock import patch
from datetime import date
from dateutil.relativedelta import relativedelta
from models import db, Account, AccountType, AccountBalance, AccountGroup, User


FIXED_RATES = {'CNY': 1.0, 'HKD': 0.923, 'USD': 7.25}


@pytest.fixture
def multi_currency_client(app):
    """含 CNY + USD 双币种账户同一分组的测试客户端"""
    with app.app_context():
        user = User(username='mc_user', nickname='多币种测试')
        user.set_password('Test1234')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        savings_type = AccountType.query.filter_by(category='savings').first()

        group = AccountGroup(user_id=user_id, name='测试分组', display_order=0)
        db.session.add(group)
        db.session.flush()

        # CNY 账户（排第一，决定分组显示币种）
        acct_cny = Account(
            user_id=user_id, name='人民币卡', type_id=savings_type.id,
            currency='CNY', initial_balance=10000, current_balance=10000,
            group_id=group.id
        )
        # USD 账户
        acct_usd = Account(
            user_id=user_id, name='美元卡', type_id=savings_type.id,
            currency='USD', initial_balance=1000, current_balance=1000,
            group_id=group.id
        )
        db.session.add_all([acct_cny, acct_usd])
        db.session.commit()

        # 写入上月快照
        prev_month = (date.today().replace(day=1) - relativedelta(months=1))
        snap_cny = AccountBalance(
            account_id=acct_cny.id, balance=10000,
            record_month=prev_month, source='snapshot'
        )
        snap_usd = AccountBalance(
            account_id=acct_usd.id, balance=1000,
            record_month=prev_month, source='snapshot'
        )
        db.session.add_all([snap_cny, snap_usd])
        db.session.commit()

        ids = (user_id, acct_cny.id, acct_usd.id)

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = ids[0]

    return client, ids


def test_group_prev_converts_usd_to_cny(multi_currency_client):
    """分组上月余额 = CNY子项 + USD子项×汇率，而非裸相加"""
    client, _ = multi_currency_client

    with patch('routes.account._get_exchange_rates', return_value=FIXED_RATES):
        resp = client.get('/accounts/')

    assert resp.status_code == 200
    html = resp.data.decode('utf-8')

    # 正确值：10000 + 1000 * 7.25 = 17,250 CNY
    assert '17,250' in html or '17250' in html, \
        "分组上月余额应折算为 17250 CNY，但未在页面中找到"

    # 错误值（裸加）不应出现在分组区域
    assert '11,000' not in html and '11000' not in html, \
        "检测到裸加结果 11000，说明 USD 未按汇率换算"


def test_group_single_currency_unchanged(app):
    """单币种分组（全 CNY）汇总值不变——回归测试"""
    with app.app_context():
        user = User(username='sc_user', nickname='单币种测试')
        user.set_password('Test1234')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        savings_type = AccountType.query.filter_by(category='savings').first()
        group = AccountGroup(user_id=user_id, name='全CNY分组', display_order=0)
        db.session.add(group)
        db.session.flush()

        a1 = Account(
            user_id=user_id, name='CNY卡1', type_id=savings_type.id,
            currency='CNY', initial_balance=5000, current_balance=5000,
            group_id=group.id
        )
        a2 = Account(
            user_id=user_id, name='CNY卡2', type_id=savings_type.id,
            currency='CNY', initial_balance=3000, current_balance=3000,
            group_id=group.id
        )
        db.session.add_all([a1, a2])
        db.session.commit()

        prev_month = (date.today().replace(day=1) - relativedelta(months=1))
        db.session.add_all([
            AccountBalance(account_id=a1.id, balance=5000,
                           record_month=prev_month, source='snapshot'),
            AccountBalance(account_id=a2.id, balance=3000,
                           record_month=prev_month, source='snapshot'),
        ])
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    with patch('routes.account._get_exchange_rates', return_value=FIXED_RATES):
        resp = client.get('/accounts/')

    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    # 全 CNY 分组：5000 + 3000 = 8000
    assert '8,000' in html or '8000' in html, \
        "单币种分组合计应为 8000 CNY"

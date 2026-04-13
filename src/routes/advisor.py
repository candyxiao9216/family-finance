"""
财务顾问路由模块
页面路由 + 持仓 CRUD + 行情 API + AI 分析 API
"""
import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal

from flask import Blueprint, render_template, request, session, url_for, flash, redirect, jsonify, send_file

from models import (db, Account, AccountType, AccountBalance, User,
                    StockHolding, FundHolding, WealthHolding,
                    Transaction, SavingsPlan, SavingsRecord, AiAdviceHistory)

advisor_bp = Blueprint('advisor', __name__, url_prefix='/advisor')


# ============ 辅助函数 ============

def _get_current_user():
    """获取当前登录用户"""
    user_id = session.get('user_id')
    return User.query.get(user_id) if user_id else None


def _get_family_user_ids():
    """获取家庭成员 ID 列表（仅用于不区分视图的场景）"""
    user = _get_current_user()
    if user and user.family:
        return [m.id for m in user.family.members]
    return [user.id] if user else []


def _get_user_ids_by_view():
    """根据'我的/家庭'视图获取 user_ids，返回 (user_ids, current_view, family)"""
    user = _get_current_user()
    if not user:
        return [], 'personal', None
    family = user.family
    current_view = request.args.get('view', 'family' if family else 'personal')
    if current_view == 'family' and family:
        return [m.id for m in family.members], 'family', family
    return [user.id], 'personal', family


def _calc_asset_allocation(user_ids=None):
    """聚合资产配置：储蓄从Account表，基金从FundHolding，股票从StockHolding(市值)，理财从WealthHolding"""
    from sqlalchemy import func
    if user_ids is None:
        user_ids = _get_family_user_ids()

    # 简单汇率
    exchange_rates = {'CNY': 1.0, 'HKD': 0.92, 'USD': 7.25}

    # 储蓄：从 Account 表按 category=savings 聚合
    savings_rows = db.session.query(
        func.sum(Account.current_balance), Account.currency
    ).join(AccountType).filter(
        AccountType.category == 'savings',
        Account.user_id.in_(user_ids)
    ).group_by(Account.currency).all()

    savings_total = 0
    for amount, currency in savings_rows:
        savings_total += float(amount or 0) * exchange_rates.get(currency, 1.0)

    # 基金：从 FundHolding.amount 聚合（排除已赎回）
    fund_rows = db.session.query(
        func.sum(FundHolding.amount), FundHolding.currency
    ).filter(
        FundHolding.user_id.in_(user_ids),
        db.or_(FundHolding.status == 'holding', FundHolding.status.is_(None))
    ).group_by(FundHolding.currency).all()

    fund_total = 0
    for amount, currency in fund_rows:
        fund_total += float(amount or 0) * exchange_rates.get(currency, 1.0)

    # 股票：从 StockHolding 计算市值（尝试拿实时价，失败用成本价）
    stock_holdings = StockHolding.query.filter(StockHolding.user_id.in_(user_ids)).all()
    stock_total = 0
    if stock_holdings:
        from services.market_data import MarketDataService
        quotes = MarketDataService.get_batch_stock_quotes(stock_holdings)
        for h in stock_holdings:
            quote = quotes.get(h.id, {})
            price = quote.get('price', 0) if not quote.get('error') else 0
            if not price:
                price = abs(h.avg_cost)  # 无行情时用成本价估算
            mv = price * h.shares
            stock_total += mv * exchange_rates.get(h.currency, 1.0)

    # 理财：从 WealthHolding.current_amount 聚合
    wealth_total = float(db.session.query(
        func.sum(WealthHolding.current_amount)
    ).filter(WealthHolding.user_id.in_(user_ids)).scalar() or 0)

    total = savings_total + fund_total + stock_total + wealth_total

    def _pct(v):
        return round(v / total * 100, 1) if total > 0 else 0

    return {
        'savings': {'amount': savings_total, 'pct': _pct(savings_total)},
        'fund': {'amount': fund_total, 'pct': _pct(fund_total)},
        'stock': {'amount': stock_total, 'pct': _pct(stock_total)},
        'wealth': {'amount': wealth_total, 'pct': _pct(wealth_total)},
        'total': total,
    }


# ============ 页面路由 ============

@advisor_bp.route('/')
def dashboard():
    """总览仪表盘"""
    user_ids, current_view, family = _get_user_ids_by_view()
    allocation = _calc_asset_allocation(user_ids)

    # 各类持仓数量
    stock_count = StockHolding.query.filter(StockHolding.user_id.in_(user_ids)).count()
    fund_count = FundHolding.query.filter(
        FundHolding.user_id.in_(user_ids),
        db.or_(FundHolding.status == 'holding', FundHolding.status.is_(None))
    ).count()
    wealth_count = WealthHolding.query.filter(WealthHolding.user_id.in_(user_ids)).count()

    return render_template('advisor/dashboard.html',
                           allocation=allocation,
                           stock_count=stock_count,
                           fund_count=fund_count,
                           wealth_count=wealth_count,
                           current_tab='dashboard',
                           current_view=current_view,
                           family=family,
                           page_title='财务顾问')


@advisor_bp.route('/stocks')
def stock_analysis():
    """股票分析页"""
    user_ids, current_view, family = _get_user_ids_by_view()
    holdings = StockHolding.query.filter(
        StockHolding.user_id.in_(user_ids)
    ).order_by(StockHolding.account_id, StockHolding.stock_code).all()

    # 获取股票账户列表
    stock_accounts = Account.query.join(AccountType).filter(
        AccountType.category == 'stock',
        Account.user_id.in_(user_ids)
    ).all()

    return render_template('advisor/stocks.html',
                           holdings=holdings,
                           stock_accounts=stock_accounts,
                           current_tab='stocks',
                           current_view=current_view,
                           family=family,
                           page_title='股票分析')


@advisor_bp.route('/funds')
def fund_analysis():
    """基金分析页"""
    user_ids, current_view, family = _get_user_ids_by_view()
    holdings = FundHolding.query.filter(
        FundHolding.user_id.in_(user_ids)
    ).order_by(FundHolding.account_id, FundHolding.fund_code).all()

    return render_template('advisor/funds.html',
                           holdings=holdings,
                           current_tab='funds',
                           current_view=current_view,
                           family=family,
                           page_title='基金分析')


@advisor_bp.route('/wealth')
def wealth_analysis():
    """理财产品分析页"""
    user_ids, current_view, family = _get_user_ids_by_view()
    holdings = WealthHolding.query.filter(
        WealthHolding.user_id.in_(user_ids)
    ).order_by(WealthHolding.account_id, WealthHolding.product_name).all()

    return render_template('advisor/wealth.html',
                           holdings=holdings,
                           current_tab='wealth',
                           current_view=current_view,
                           family=family,
                           page_title='理财产品')


@advisor_bp.route('/savings')
def savings_advice():
    """储蓄建议页"""
    user_ids, current_view, family = _get_user_ids_by_view()

    # 汇总储蓄数据
    from sqlalchemy import func, extract
    now = datetime.now()

    # 银行储蓄总额
    total_savings = db.session.query(
        func.sum(Account.current_balance)
    ).join(AccountType).filter(
        AccountType.category == 'savings',
        Account.user_id.in_(user_ids)
    ).scalar() or 0

    # 本月收支
    monthly_income = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id.in_(user_ids),
        Transaction.type == 'income',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month
    ).scalar() or 0

    monthly_expense = db.session.query(
        func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id.in_(user_ids),
        Transaction.type == 'expense',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month
    ).scalar() or 0

    # 年度储蓄目标
    savings_target = db.session.query(
        func.sum(SavingsPlan.target_amount)
    ).filter(
        SavingsPlan.year == now.year,
        SavingsPlan.type == 'annual'
    ).scalar() or 0

    savings_data = {
        'total_savings': float(total_savings),
        'monthly_income': float(monthly_income),
        'monthly_expense': float(monthly_expense),
        'monthly_surplus': float(monthly_income) - float(monthly_expense),
        'savings_target': float(savings_target)
    }

    return render_template('advisor/savings.html',
                           savings_data=savings_data,
                           current_tab='savings',
                           current_view=current_view,
                           family=family,
                           page_title='储蓄建议')


@advisor_bp.route('/history')
def advice_history():
    """AI 分析历史记录页"""
    advice_type = request.args.get('type', '')

    if advice_type:
        records = AiAdviceHistory.query.filter_by(
            advice_type=advice_type
        ).order_by(AiAdviceHistory.generated_at.desc()).limit(50).all()
    else:
        records = AiAdviceHistory.query.order_by(
            AiAdviceHistory.generated_at.desc()
        ).limit(50).all()

    user = _get_current_user()
    family = user.family if user else None

    return render_template('advisor/history.html',
                           records=records,
                           current_type=advice_type,
                           current_tab='history',
                           current_view=request.args.get('view', 'family' if family else 'personal'),
                           family=family,
                           page_title='AI 分析历史')


# ============ 持仓 CRUD API ============

@advisor_bp.route('/api/stocks', methods=['POST'])
def add_stock():
    """添加股票持仓"""
    user_id = session.get('user_id')
    data = request.json or request.form

    holding = StockHolding(
        user_id=user_id,
        account_id=int(data['account_id']),
        stock_code=data['stock_code'].strip(),
        stock_name=data['stock_name'].strip(),
        market=data.get('market', 'HK'),
        shares=float(data['shares']),
        avg_cost=float(data['avg_cost']),
        currency=data.get('currency', 'HKD'),
        notes=data.get('notes', '')
    )
    db.session.add(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'id': holding.id})
    flash('股票持仓已添加', 'success')
    return redirect(url_for('advisor.stock_analysis'))


@advisor_bp.route('/api/stocks/<int:id>', methods=['POST'])
def update_stock(id):
    """更新股票持仓"""
    holding = StockHolding.query.get_or_404(id)
    data = request.json or request.form

    if 'shares' in data:
        holding.shares = float(data['shares'])
    if 'avg_cost' in data:
        holding.avg_cost = float(data['avg_cost'])
    if 'notes' in data:
        holding.notes = data['notes']

    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash('持仓已更新', 'success')
    return redirect(url_for('advisor.stock_analysis'))


@advisor_bp.route('/api/stocks/<int:id>/delete', methods=['POST'])
def delete_stock(id):
    """删除股票持仓"""
    holding = StockHolding.query.get_or_404(id)
    db.session.delete(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash('持仓已删除', 'success')
    return redirect(url_for('advisor.stock_analysis'))


@advisor_bp.route('/api/funds', methods=['POST'])
def add_fund():
    """添加基金持仓"""
    user_id = session.get('user_id')
    data = request.json or request.form

    holding = FundHolding(
        user_id=user_id,
        account_id=int(data['account_id']),
        fund_code=data['fund_code'].strip(),
        fund_name=data['fund_name'].strip(),
        fund_type=data.get('fund_type', ''),
        shares=float(data.get('shares', 0)) if data.get('shares') else None,
        amount=float(data.get('amount', 0)) if data.get('amount') else None,
        avg_cost=float(data.get('avg_cost', 0)) if data.get('avg_cost') else None,
        profit=float(data.get('profit', 0)) if data.get('profit') else None,
        profit_rate=data.get('profit_rate', ''),
        currency=data.get('currency', 'CNY'),
        notes=data.get('notes', '')
    )
    db.session.add(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'id': holding.id})
    flash('基金持仓已添加', 'success')
    return redirect(url_for('advisor.fund_analysis'))


@advisor_bp.route('/api/funds/<int:id>/delete', methods=['POST'])
def delete_fund(id):
    """删除基金持仓"""
    holding = FundHolding.query.get_or_404(id)
    db.session.delete(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash('基金持仓已删除', 'success')
    return redirect(url_for('advisor.fund_analysis'))


@advisor_bp.route('/api/funds/<int:fund_id>/transfer', methods=['POST'])
def transfer_fund(fund_id):
    """基金转投：标记旧基金已赎回，创建新基金持仓"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '请先登录'}), 401

    old_holding = FundHolding.query.get_or_404(fund_id)
    data = request.json or {}

    new_fund_name = (data.get('new_fund_name') or '').strip()
    new_fund_code = (data.get('new_fund_code') or '').strip()
    transfer_amount = data.get('transfer_amount')

    if not new_fund_name:
        return jsonify({'success': False, 'error': '请填写新基金名称'}), 400
    if not transfer_amount or float(transfer_amount) <= 0:
        return jsonify({'success': False, 'error': '请填写有效的转投金额'}), 400

    # 1. 标记旧基金为已赎回
    old_holding.status = 'redeemed'
    old_holding.notes = (old_holding.notes or '') + f'\n转投至 {new_fund_name} ¥{float(transfer_amount):,.2f}'

    # 2. 创建新基金持仓（继承同平台 account_id）
    new_holding = FundHolding(
        user_id=old_holding.user_id,
        account_id=old_holding.account_id,
        fund_code=new_fund_code or 'TBD',
        fund_name=new_fund_name,
        fund_type=old_holding.fund_type,
        amount=float(transfer_amount),
        currency=old_holding.currency,
        status='holding',
        notes=f'由 {old_holding.fund_name} 转投而来'
    )
    db.session.add(new_holding)
    db.session.commit()

    return jsonify({'success': True, 'new_fund_id': new_holding.id})


@advisor_bp.route('/api/wealth', methods=['POST'])
def add_wealth():
    """添加理财产品"""
    user_id = session.get('user_id')
    data = request.json or request.form

    holding = WealthHolding(
        user_id=user_id,
        account_id=int(data['account_id']),
        product_name=data['product_name'].strip(),
        manager=data.get('manager', ''),
        buy_amount=float(data['buy_amount']),
        current_amount=float(data.get('current_amount', 0)) if data.get('current_amount') else None,
        total_profit=float(data.get('total_profit', 0)) if data.get('total_profit') else None,
        annual_rate=float(data.get('annual_rate', 0)) if data.get('annual_rate') else None,
        buy_date=datetime.strptime(data['buy_date'], '%Y-%m-%d').date() if data.get('buy_date') else None,
        expire_date=datetime.strptime(data['expire_date'], '%Y-%m-%d').date() if data.get('expire_date') else None,
        product_type=data.get('product_type', 'fixed'),
        currency=data.get('currency', 'CNY'),
        notes=data.get('notes', '')
    )
    db.session.add(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'id': holding.id})
    flash('理财产品已添加', 'success')
    return redirect(url_for('advisor.wealth_analysis'))


@advisor_bp.route('/api/wealth/<int:id>/delete', methods=['POST'])
def delete_wealth(id):
    """删除理财产品"""
    holding = WealthHolding.query.get_or_404(id)
    db.session.delete(holding)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash('理财产品已删除', 'success')
    return redirect(url_for('advisor.wealth_analysis'))


# ============ 行情 API ============

@advisor_bp.route('/api/stock/search')
def search_stock():
    """搜索股票"""
    keyword = request.args.get('q', '').strip()
    market = request.args.get('market', 'HK')
    if not keyword:
        return jsonify([])

    from services.market_data import MarketDataService
    results = MarketDataService.search_stock(keyword, market)
    return jsonify(results)


@advisor_bp.route('/api/stock/quote/<market>/<code>')
def stock_quote(market, code):
    """获取股票实时行情"""
    from services.market_data import MarketDataService
    quote = MarketDataService.get_stock_quote(code, market)
    return jsonify(quote)


@advisor_bp.route('/api/stock/batch-quotes')
def batch_stock_quotes():
    """批量获取持仓股票行情"""
    user_ids, _, _ = _get_user_ids_by_view()
    holdings = StockHolding.query.filter(StockHolding.user_id.in_(user_ids)).all()

    from services.market_data import MarketDataService
    quotes = MarketDataService.get_batch_stock_quotes(holdings)

    # 转为 JSON 可序列化格式
    return jsonify({str(k): v for k, v in quotes.items()})


@advisor_bp.route('/api/fund/nav/<code>')
def fund_nav(code):
    """获取基金最新净值"""
    from services.market_data import MarketDataService
    nav = MarketDataService.get_fund_nav(code)
    return jsonify(nav)


# ============ AI 分析 API ============

def _should_refresh():
    """检查请求是否要求跳过缓存"""
    return request.args.get('refresh') == '1'

def _ai_response(result, advice_type=None, user_id=None):
    """统一 AI 返回格式 + 写历史"""
    from services.ai_advisor import AiAdvisor
    if isinstance(result, tuple) and len(result) == 3:
        text, generated_at, from_cache = result
    else:
        text, generated_at, from_cache = str(result), None, False

    # 非缓存命中 + 有 advice_type → 写历史
    if not from_cache and advice_type and user_id and text and not text.startswith('❌') and not text.startswith('💡'):
        advisor = AiAdvisor()
        AiAdvisor.save_history(user_id, advice_type, text, advisor.model)

    return jsonify({
        'advice': text,
        'generated_at': generated_at.strftime('%Y-%m-%d %H:%M') if generated_at else None,
        'from_cache': from_cache,
    })


@advisor_bp.route('/api/ai/comprehensive')
def ai_comprehensive():
    """AI 综合分析（总览页）"""
    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    user_id = session.get('user_id')
    user_ids, _, _ = _get_user_ids_by_view()

    allocation = _calc_asset_allocation(user_ids)

    # 股票摘要
    stocks = StockHolding.query.filter(StockHolding.user_id.in_(user_ids)).all()
    if stocks:
        from services.market_data import MarketDataService
        quotes = MarketDataService.get_batch_stock_quotes(stocks)
        stock_lines = []
        for h in stocks:
            q = quotes.get(h.id, {})
            price = q.get('price', 0) if not q.get('error') else 0
            pnl = ((price - h.avg_cost) / abs(h.avg_cost) * 100) if h.avg_cost and h.avg_cost != 0 else 0
            stock_lines.append(f"- {h.stock_name}({h.stock_code}): 现价{price}, 盈亏{pnl:+.1f}%")
        stocks_summary = f"共{len(stocks)}只股票:\n" + "\n".join(stock_lines)
    else:
        stocks_summary = "暂无股票持仓"

    # 基金摘要
    funds = FundHolding.query.filter(FundHolding.user_id.in_(user_ids)).all()
    if funds:
        fund_lines = [f"- {h.fund_name}: {h.fund_type or '未知'}, ¥{h.amount or 0:,.0f}, 收益率{h.profit_rate or '未知'}" for h in funds]
        funds_summary = f"共{len(funds)}只基金:\n" + "\n".join(fund_lines)
    else:
        funds_summary = "暂无基金持仓"

    # 理财摘要
    wealth = WealthHolding.query.filter(WealthHolding.user_id.in_(user_ids)).all()
    if wealth:
        w_lines = [f"- {h.product_name}: ¥{h.current_amount or h.buy_amount:,.0f}, 年化{(h.annual_rate or 0)*100:.2f}%" for h in wealth]
        wealth_summary = f"共{len(wealth)}个理财产品:\n" + "\n".join(w_lines)
    else:
        wealth_summary = "暂无理财产品"

    # 储蓄摘要
    from sqlalchemy import func, extract
    now = datetime.now()
    total_savings = db.session.query(func.sum(Account.current_balance)).join(AccountType).filter(
        AccountType.category == 'savings', Account.user_id.in_(user_ids)).scalar() or 0
    monthly_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id.in_(user_ids), Transaction.type == 'income',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month).scalar() or 0
    monthly_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id.in_(user_ids), Transaction.type == 'expense',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month).scalar() or 0
    savings_summary = f"银行存款¥{float(total_savings):,.0f}, 月收入¥{float(monthly_income):,.0f}, 月支出¥{float(monthly_expense):,.0f}, 月结余¥{float(monthly_income)-float(monthly_expense):,.0f}"

    result = advisor.analyze_comprehensive({
        'allocation': allocation,
        'stocks_summary': stocks_summary,
        'funds_summary': funds_summary,
        'wealth_summary': wealth_summary,
        'savings_summary': savings_summary,
    }, skip_cache=_should_refresh())
    return _ai_response(result, 'comprehensive', user_id)


@advisor_bp.route('/api/ai/allocation')
def ai_allocation_advice():
    """AI 资产配置建议（保留兼容）"""
    return ai_comprehensive()


@advisor_bp.route('/api/ai/stock/<int:holding_id>')
def ai_stock_advice(holding_id):
    """AI 单只股票建议"""
    holding = StockHolding.query.get_or_404(holding_id)

    from services.market_data import MarketDataService
    quote = MarketDataService.get_stock_quote(holding.stock_code, holding.market)

    if 'error' in quote:
        return jsonify({'advice': f'⚠️ 无法获取行情: {quote["error"]}', 'generated_at': None, 'from_cache': False})

    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    result = advisor.analyze_stock(quote, {
        'shares': holding.shares,
        'avg_cost': holding.avg_cost,
        'currency': holding.currency
    }, skip_cache=_should_refresh())
    return _ai_response(result)


@advisor_bp.route('/api/ai/fund/<int:holding_id>')
def ai_fund_advice(holding_id):
    """AI 基金建议"""
    holding = FundHolding.query.get_or_404(holding_id)

    from services.market_data import MarketDataService
    nav_data = MarketDataService.get_fund_nav(holding.fund_code)

    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    result = advisor.analyze_fund(nav_data, {
        'fund_code': holding.fund_code,
        'fund_name': holding.fund_name,
        'fund_type': holding.fund_type,
        'shares': holding.shares,
        'amount': holding.amount,
        'avg_cost': holding.avg_cost,
        'profit': holding.profit,
        'profit_rate': holding.profit_rate
    }, skip_cache=_should_refresh())
    return _ai_response(result)


@advisor_bp.route('/api/ai/stocks-overall')
def ai_stocks_overall():
    """AI 股票整体分析"""
    user_id = session.get('user_id')
    user_ids, _, _ = _get_user_ids_by_view()
    holdings = StockHolding.query.filter(StockHolding.user_id.in_(user_ids)).all()

    if not holdings:
        return jsonify({'advice': '暂无股票持仓数据', 'generated_at': None, 'from_cache': False})

    from services.market_data import MarketDataService
    quotes = MarketDataService.get_batch_stock_quotes(holdings)

    stock_data = []
    for h in holdings:
        quote = quotes.get(h.id, {})
        price = quote.get('price', 0) if not quote.get('error') else 0
        change_pct = quote.get('change_pct', 0) if not quote.get('error') else 0
        market_value = price * h.shares if price else abs(h.avg_cost) * h.shares
        stock_data.append({
            'stock_code': h.stock_code, 'stock_name': h.stock_name, 'market': h.market,
            'shares': h.shares, 'avg_cost': h.avg_cost, 'current_price': price,
            'change_pct': change_pct, 'market_value': market_value,
            'currency': h.currency, 'notes': h.notes,
            'account_name': h.account.name if h.account else '',
        })

    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    result = advisor.analyze_stocks_overall(stock_data, skip_cache=_should_refresh())
    return _ai_response(result, 'stocks', user_id)


@advisor_bp.route('/api/ai/funds-overall')
def ai_funds_overall():
    """AI 基金整体分析"""
    user_id = session.get('user_id')
    user_ids, _, _ = _get_user_ids_by_view()
    holdings = FundHolding.query.filter(
        FundHolding.user_id.in_(user_ids),
        db.or_(FundHolding.status == 'holding', FundHolding.status.is_(None))
    ).all()

    fund_data = []
    for h in holdings:
        fund_data.append({
            'fund_code': h.fund_code, 'fund_name': h.fund_name, 'fund_type': h.fund_type,
            'shares': h.shares, 'amount': h.amount or 0, 'avg_cost': h.avg_cost,
            'profit': h.profit, 'profit_rate': h.profit_rate,
            'currency': h.currency, 'notes': h.notes,
            'account_name': h.account.name if h.account else '',
        })

    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    result = advisor.analyze_funds_overall(fund_data, skip_cache=_should_refresh())
    return _ai_response(result, 'funds', user_id)


@advisor_bp.route('/api/ai/wealth')
def ai_wealth_advice():
    """AI 理财产品建议"""
    user_id = session.get('user_id')
    user_ids, _, _ = _get_user_ids_by_view()
    holdings = WealthHolding.query.filter(WealthHolding.user_id.in_(user_ids)).all()

    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    wealth_data = []
    for h in holdings:
        wealth_data.append({
            'product_name': h.product_name, 'manager': h.manager,
            'buy_amount': h.buy_amount or 0, 'current_amount': h.current_amount or 0,
            'total_profit': h.total_profit, 'annual_rate': h.annual_rate,
            'buy_date': str(h.buy_date) if h.buy_date else '',
            'expire_date': str(h.expire_date) if h.expire_date else '',
            'product_type': h.product_type, 'notes': h.notes,
            'account_name': h.account.name if h.account else '',
        })
    result = advisor.analyze_wealth(wealth_data, skip_cache=_should_refresh())
    return _ai_response(result, 'wealth', user_id)


@advisor_bp.route('/api/ai/savings')
def ai_savings_advice():
    """AI 储蓄建议"""
    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    user_id = session.get('user_id')
    user_ids, _, _ = _get_user_ids_by_view()
    from sqlalchemy import func, extract
    now = datetime.now()

    total_savings = db.session.query(func.sum(Account.current_balance)).join(AccountType).filter(
        AccountType.category == 'savings', Account.user_id.in_(user_ids)).scalar() or 0
    monthly_income = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id.in_(user_ids), Transaction.type == 'income',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month).scalar() or 0
    monthly_expense = db.session.query(func.sum(Transaction.amount)).filter(
        Transaction.user_id.in_(user_ids), Transaction.type == 'expense',
        extract('year', Transaction.transaction_date) == now.year,
        extract('month', Transaction.transaction_date) == now.month).scalar() or 0

    result = advisor.analyze_savings({
        'total_savings': float(total_savings),
        'monthly_income': float(monthly_income),
        'monthly_expense': float(monthly_expense),
        'monthly_surplus': float(monthly_income) - float(monthly_expense),
        'savings_target': 0
    }, skip_cache=_should_refresh())
    return _ai_response(result, 'savings', user_id)


# ============ AI 历史记录 API ============

@advisor_bp.route('/api/ai/history/<advice_type>')
def ai_history_list(advice_type):
    """获取某类型的历史分析列表"""
    from services.ai_advisor import AiAdvisor
    records = AiAdvisor.get_history(advice_type, limit=20)
    return jsonify({'records': records})


@advisor_bp.route('/api/ai/history/<advice_type>/<int:record_id>')
def ai_history_detail(advice_type, record_id):
    """获取单条历史分析详情"""
    from services.ai_advisor import AiAdvisor
    detail = AiAdvisor.get_history_detail(record_id)
    if not detail:
        return jsonify({'error': '记录不存在'}), 404
    return jsonify(detail)


# ============ 持仓批量导入 ============

HOLDING_TYPES = {
    'stock': '股票',
    'fund': '基金',
    'wealth': '理财',
    'savings': '储蓄',
}

# Excel 列名 → 模型字段映射（支持多种别名）
EXCEL_FIELD_MAP = {
    'stock': {
        '股票代码': 'stock_code', '代码': 'stock_code',
        '股票名称': 'stock_name', '名称': 'stock_name',
        '市场': 'market',
        '持股数量': 'shares', '持有股数': 'shares',
        '买入均价': 'avg_cost', '买入均价(摊薄成本)': 'avg_cost', '买入均价（摊薄成本）': 'avg_cost', '摊薄成本': 'avg_cost',
        '币种': 'currency',
        '账户名': 'account_name', '所属账户': 'account_name',
        '备注': 'notes',
    },
    'fund': {
        '基金代码': 'fund_code', '代码': 'fund_code',
        '基金名称': 'fund_name', '名称': 'fund_name',
        '基金类型': 'fund_type', '类型': 'fund_type',
        '持有份额': 'shares', '份额': 'shares',
        '持有金额': 'amount', '金额': 'amount',
        '买入均价': 'avg_cost', '买入均价(净值)': 'avg_cost', '买入均价（净值）': 'avg_cost',
        '最新净值': 'latest_nav', '净值': 'latest_nav',
        '持有收益': 'profit', '收益': 'profit',
        '收益率': 'profit_rate', '持有收益率': 'profit_rate',
        '币种': 'currency',
        '账户名': 'account_name', '所属账户': 'account_name',
        '备注': 'notes',
    },
    'wealth': {
        '产品名称': 'product_name', '名称': 'product_name',
        '管理机构': 'manager',
        '买入金额': 'buy_amount',
        '当前金额': 'current_amount',
        '累计收益': 'total_profit',
        '年化收益率': 'annual_rate',
        '买入日期': 'buy_date',
        '到期日期': 'expire_date',
        '产品类型': 'product_type',
        '币种': 'currency',
        '账户名': 'account_name', '所属账户': 'account_name',
        '备注': 'notes',
    },
    'savings': {
        '账户名': 'account_name', '所属账户': 'account_name',
        '当前余额': 'balance', '余额': 'balance',
        '币种': 'currency',
        '备注': 'notes',
    },
}

# 截图识别的 JSON schema 提示
VISION_PROMPTS = {
    'stock': '''请从这张股票持仓截图中提取数据，返回严格的 JSON 数组：
[{"stock_code":"00700","stock_name":"腾讯控股","market":"HK","shares":100,"avg_cost":350.5,"currency":"HKD"}]
market 只能是 HK/A/US。只返回 JSON 数组，不要其他文字。''',
    'fund': '''请从这张基金持仓截图中提取数据，返回严格的 JSON 数组：
[{"fund_code":"004253","fund_name":"基金名称","fund_type":"混合型基金","shares":1000,"amount":15000,"avg_cost":1.5,"profit":500,"profit_rate":"+3.4%","currency":"CNY"}]
只返回 JSON 数组，不要其他文字。''',
    'wealth': '''请从这张理财产品持仓截图中提取数据，返回严格的 JSON 数组：
[{"product_name":"产品名称","manager":"管理机构","buy_amount":50000,"current_amount":50500,"total_profit":500,"annual_rate":3.5,"buy_date":"2025-01-15","expire_date":"2025-07-15","product_type":"fixed","currency":"CNY"}]
product_type 只能是 fixed/flexible/closed。annual_rate 是百分比数字（如 3.5 表示 3.5%）。只返回 JSON 数组，不要其他文字。''',
    'savings': '''请从这张储蓄/银行账户截图中提取数据，返回严格的 JSON 数组：
[{"account_name":"招行储蓄","balance":530000,"currency":"CNY"}]
只返回 JSON 数组，不要其他文字。''',
}


@advisor_bp.route('/import')
def import_page():
    """持仓批量导入页面"""
    user = _get_current_user()
    if not user:
        return redirect(url_for('auth.login'))

    # 获取用户的所有账户（用于前端下拉映射）
    accounts = Account.query.filter_by(user_id=user.id).all()
    account_list = [{'id': a.id, 'name': a.name, 'category': a.account_type.category} for a in accounts]

    return render_template('advisor/import.html',
                           accounts=account_list,
                           current_tab='import',
                           current_view=request.args.get('view', 'personal'),
                           family=user.family,
                           page_title='批量导入持仓')


@advisor_bp.route('/import/parse-excel', methods=['POST'])
def parse_excel_holdings():
    """解析 Excel/CSV 持仓文件"""
    import tempfile
    import pandas as pd

    user_id = session.get('user_id')
    holding_type = request.form.get('holding_type', '')
    if holding_type not in EXCEL_FIELD_MAP:
        return jsonify({'error': '无效的持仓类型'}), 400

    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '空文件名'}), 400

    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ('.xlsx', '.csv'):
        return jsonify({'error': '仅支持 .xlsx 和 .csv 格式'}), 400

    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    file.save(tmp.name)
    tmp.close()

    try:
        if ext.lower() == '.csv':
            for enc in ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']:
                try:
                    df = pd.read_csv(tmp.name, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return jsonify({'error': '无法识别文件编码'}), 400
        else:
            df = pd.read_excel(tmp.name)

        field_map = EXCEL_FIELD_MAP[holding_type]
        records = []
        for _, row in df.iterrows():
            record = {}
            for cn_col, en_field in field_map.items():
                val = row.get(cn_col)
                if pd.notna(val):
                    record[en_field] = str(val).strip() if isinstance(val, str) else val
                elif en_field not in record:
                    # 仅在字段尚未被其他别名填充时才设为 None
                    record[en_field] = None
            # 跳过完全空行
            if not any(v for v in record.values() if v is not None):
                continue

            # 数据后处理
            if holding_type == 'stock':
                # 市场名称标准化：港股→HK, A股/沪/深→A, 美股→US
                m = str(record.get('market', '') or '')
                if m in ('港股', 'HK', 'hk', '港'):
                    record['market'] = 'HK'
                elif m in ('A股', 'A', 'a', '沪', '深', '沪市', '深市'):
                    record['market'] = 'A'
                elif m in ('美股', 'US', 'us', '美'):
                    record['market'] = 'US'
                # 股票代码补零（港股5位，A股6位）
                code = str(record.get('stock_code', '') or '').strip()
                if record['market'] == 'HK' and code.isdigit() and len(code) < 5:
                    code = code.zfill(5)
                elif record['market'] == 'A' and code.isdigit() and len(code) < 6:
                    code = code.zfill(6)
                record['stock_code'] = code
                # 默认币种
                if not record.get('currency'):
                    record['currency'] = 'HKD' if record['market'] == 'HK' else ('USD' if record['market'] == 'US' else 'CNY')

            elif holding_type == 'fund':
                # 收益率格式标准化
                pr = record.get('profit_rate')
                if pr and isinstance(pr, (int, float)):
                    record['profit_rate'] = f"{pr:+.2f}%" if abs(pr) < 1 else f"{pr:+.2f}%"
                # 默认币种
                if not record.get('currency'):
                    record['currency'] = 'CNY'

            elif holding_type == 'wealth':
                # 年化收益率：如果是小数（如0.0295）保持不变，confirm时会处理
                # 默认币种
                if not record.get('currency'):
                    record['currency'] = 'CNY'

            records.append(record)

        # 账户映射 + 重复检测
        records = _map_accounts_and_detect_duplicates(records, holding_type, user_id)

        return jsonify({
            'records': records,
            'total': len(records),
            'holding_type': holding_type,
            'file_name': file.filename,
        })
    except Exception as e:
        return jsonify({'error': f'解析失败: {str(e)}'}), 400
    finally:
        os.unlink(tmp.name)


@advisor_bp.route('/import/parse-image', methods=['POST'])
def parse_image_holdings():
    """App 截图识别持仓数据"""
    import base64

    user_id = session.get('user_id')
    holding_type = request.form.get('holding_type', '')
    if holding_type not in VISION_PROMPTS:
        return jsonify({'error': '无效的持仓类型'}), 400

    if 'file' not in request.files:
        return jsonify({'error': '未找到图片'}), 400
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '空文件名'}), 400

    _, ext = os.path.splitext(file.filename)
    if ext.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        return jsonify({'error': '仅支持 jpg/png/webp 图片'}), 400

    # 读取图片并转 base64
    img_data = file.read()
    b64 = base64.b64encode(img_data).decode('utf-8')

    # 根据扩展名确定 MIME
    mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp'}
    image_mime = mime_map.get(ext.lower(), 'image/png')

    # 调用 AI Vision
    from services.ai_advisor import AiAdvisor
    advisor = AiAdvisor()
    if not advisor.available:
        return jsonify({'error': 'AI 服务未配置'}), 500

    result = advisor.call_vision(VISION_PROMPTS[holding_type], image_base64=b64, image_mime=image_mime)
    if not result or result.startswith('❌') or result.startswith('⏳'):
        return jsonify({'error': result or '图片识别失败'}), 500

    # 解析 AI 返回的 JSON
    try:
        # 去掉可能的 markdown 代码块标记
        text = result.strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        if text.startswith('json'):
            text = text[4:].strip()

        records = json.loads(text)
        if not isinstance(records, list):
            records = [records]
    except (json.JSONDecodeError, ValueError) as e:
        return jsonify({'error': f'AI 返回格式无法解析: {str(e)}', 'raw': result}), 400

    # 账户映射 + 重复检测
    records = _map_accounts_and_detect_duplicates(records, holding_type, user_id)

    return jsonify({
        'records': records,
        'total': len(records),
        'holding_type': holding_type,
        'file_name': file.filename,
    })


@advisor_bp.route('/import/confirm', methods=['POST'])
def confirm_import_holdings():
    """确认导入持仓数据"""
    user_id = session.get('user_id')
    data = request.get_json()
    if not data or 'records' not in data:
        return jsonify({'error': '无效数据'}), 400

    holding_type = data.get('holding_type', '')
    records = data['records']
    imported = 0
    skipped = 0

    for r in records:
        if r.get('skip'):
            skipped += 1
            continue
        account_id = r.get('account_id')
        if not account_id:
            skipped += 1
            continue

        try:
            if holding_type == 'stock':
                db.session.add(StockHolding(
                    user_id=user_id, account_id=int(account_id),
                    stock_code=str(r.get('stock_code', '')).strip(),
                    stock_name=str(r.get('stock_name', '')).strip(),
                    market=r.get('market', 'HK'),
                    shares=float(r.get('shares', 0)),
                    avg_cost=float(r.get('avg_cost', 0)),
                    currency=r.get('currency', 'HKD'),
                    notes=r.get('notes', ''),
                ))
            elif holding_type == 'fund':
                db.session.add(FundHolding(
                    user_id=user_id, account_id=int(account_id),
                    fund_code=str(r.get('fund_code', '')).strip(),
                    fund_name=str(r.get('fund_name', '')).strip(),
                    fund_type=r.get('fund_type', ''),
                    shares=float(r['shares']) if r.get('shares') else None,
                    amount=float(r['amount']) if r.get('amount') else None,
                    avg_cost=float(r['avg_cost']) if r.get('avg_cost') else None,
                    profit=float(r['profit']) if r.get('profit') else None,
                    profit_rate=r.get('profit_rate', ''),
                    currency=r.get('currency', 'CNY'),
                    notes=r.get('notes', ''),
                ))
            elif holding_type == 'wealth':
                bd = None
                if r.get('buy_date'):
                    try:
                        bd = datetime.strptime(str(r['buy_date'])[:10], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                ed = None
                if r.get('expire_date'):
                    try:
                        ed = datetime.strptime(str(r['expire_date'])[:10], '%Y-%m-%d').date()
                    except ValueError:
                        pass
                annual = r.get('annual_rate')
                if annual and float(annual) > 1:
                    annual = float(annual) / 100  # 百分比转小数
                db.session.add(WealthHolding(
                    user_id=user_id, account_id=int(account_id),
                    product_name=str(r.get('product_name', '')).strip(),
                    manager=r.get('manager', ''),
                    buy_amount=float(r.get('buy_amount', 0)),
                    current_amount=float(r.get('current_amount', 0)) if r.get('current_amount') else None,
                    total_profit=float(r.get('total_profit', 0)) if r.get('total_profit') else None,
                    annual_rate=float(annual) if annual else None,
                    buy_date=bd, expire_date=ed,
                    product_type=r.get('product_type', 'fixed'),
                    currency=r.get('currency', 'CNY'),
                    notes=r.get('notes', ''),
                ))
            elif holding_type == 'savings':
                # 储蓄：更新已有账户余额
                acct = db.session.get(Account, int(account_id))
                if acct:
                    acct.current_balance = Decimal(str(r.get('balance', 0)))
                    imported += 1
                    continue

            imported += 1
        except Exception as e:
            print(f"导入行失败: {e}")
            skipped += 1

    db.session.commit()
    return jsonify({'imported_count': imported, 'skipped_count': skipped, 'total': len(records)})


def _map_accounts_and_detect_duplicates(records, holding_type, user_id):
    """账户名映射 + 重复检测"""
    # 构建账户名 → id 映射
    accounts = Account.query.filter_by(user_id=user_id).all()
    acct_name_map = {}
    for a in accounts:
        acct_name_map[a.name] = a.id
        # 也支持模糊匹配（去掉"股票"/"基金"等后缀）
        short = a.name.replace('股票', '').replace('基金', '').replace('理财', '').replace('储蓄', '')
        if short:
            acct_name_map[short] = a.id

    # 加载已有持仓用于重复检测
    existing_keys = set()
    if holding_type == 'stock':
        for h in StockHolding.query.filter_by(user_id=user_id).all():
            existing_keys.add(f"{h.stock_code}|{h.account_id}")
    elif holding_type == 'fund':
        for h in FundHolding.query.filter_by(user_id=user_id).all():
            existing_keys.add(f"{h.fund_code}|{h.account_id}")
    elif holding_type == 'wealth':
        for h in WealthHolding.query.filter_by(user_id=user_id).all():
            existing_keys.add(f"{h.product_name}|{h.account_id}")
    elif holding_type == 'savings':
        for a in accounts:
            if a.account_type.category == 'savings':
                existing_keys.add(str(a.id))

    for r in records:
        # 账户映射
        acct_name = r.get('account_name', '')
        if acct_name and acct_name in acct_name_map:
            r['account_id'] = acct_name_map[acct_name]
            r['account_matched'] = True
        else:
            r['account_id'] = None
            r['account_matched'] = False

        # 重复检测
        r['is_duplicate'] = False
        aid = r.get('account_id', '')
        if holding_type == 'stock' and r.get('stock_code'):
            if f"{r['stock_code']}|{aid}" in existing_keys:
                r['is_duplicate'] = True
        elif holding_type == 'fund' and r.get('fund_code'):
            if f"{r['fund_code']}|{aid}" in existing_keys:
                r['is_duplicate'] = True
        elif holding_type == 'wealth' and r.get('product_name'):
            if f"{r['product_name']}|{aid}" in existing_keys:
                r['is_duplicate'] = True
        elif holding_type == 'savings' and aid:
            if str(aid) in existing_keys:
                r['is_duplicate'] = True
                r['is_update'] = True  # 储蓄是更新余额

    return records


@advisor_bp.route('/import/template/<holding_type>')
def download_holding_template(holding_type):
    """下载持仓导入模板"""
    if holding_type not in EXCEL_FIELD_MAP:
        flash('无效的模板类型', 'error')
        return redirect(url_for('advisor.import_page'))

    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'static', f'holding_{holding_type}_template.csv'
    )
    type_names = {'stock': '股票', 'fund': '基金', 'wealth': '理财', 'savings': '储蓄'}
    return send_file(template_path, as_attachment=True,
                     download_name=f'{type_names[holding_type]}持仓导入模板.csv')

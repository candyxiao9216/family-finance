"""
AI 财务顾问服务层
封装 MiniMax API，提供综合分析、股票、基金、理财、储蓄六类分析建议。
支持缓存返回时间戳 + 历史记录写入。
"""
import os
import json
import hashlib
import requests
from datetime import datetime, timedelta


# AI 建议缓存有效期（小时）
AI_CACHE_TTL_HOURS = 1


class AiAdvisor:
    """AI 财务顾问 — 支持智谱GLM多模型（文本/多模态/图像生成）"""

    # 智谱 API 基础 URL
    BASE_URL = 'https://open.bigmodel.cn/api/paas/v4'

    def __init__(self):
        self.api_key = os.environ.get('AI_API_KEY', '') or os.environ.get('MINIMAX_API_KEY', '')
        # 文本模型（财务分析用）— GLM-5 旗舰 / GLM-5-Turbo 快速
        self.model = os.environ.get('AI_MODEL', 'GLM-5')
        # 多模态模型（图片理解/OCR用）
        self.vision_model = os.environ.get('AI_VISION_MODEL', 'GLM-5V-Turbo')
        # 图像生成模型
        self.image_model = os.environ.get('AI_IMAGE_MODEL', 'GLM-Image')
        # 兼容自定义 URL
        self._custom_url = os.environ.get('AI_API_URL', '')

    @property
    def available(self):
        return bool(self.api_key)

    # ========== 分析方法 ==========

    def analyze_comprehensive(self, data, skip_cache=False):
        """
        综合分析：资产配置 + 各板块摘要，给出整体建议
        data: {allocation, stocks_summary, funds_summary, wealth_summary, savings_summary}
        返回: (advice_text, generated_at, from_cache)
        """
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"comprehensive_{datetime.now().strftime('%Y%m%d%H')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        alloc = data.get('allocation', {})
        prompt = f"""你是专业家庭财务总顾问。以下是一个家庭的完整财务状况：

## 资产配置（总计 ¥{alloc.get('total', 0):,.0f}）
- 银行储蓄: ¥{alloc.get('savings', {}).get('amount', 0):,.0f} ({alloc.get('savings', {}).get('pct', 0):.1f}%)
- 基金投资: ¥{alloc.get('fund', {}).get('amount', 0):,.0f} ({alloc.get('fund', {}).get('pct', 0):.1f}%)
- 股票投资: ¥{alloc.get('stock', {}).get('amount', 0):,.0f} ({alloc.get('stock', {}).get('pct', 0):.1f}%)
- 理财产品: ¥{alloc.get('wealth', {}).get('amount', 0):,.0f} ({alloc.get('wealth', {}).get('pct', 0):.1f}%)

## 股票持仓摘要
{data.get('stocks_summary', '暂无股票持仓')}

## 基金持仓摘要
{data.get('funds_summary', '暂无基金持仓')}

## 理财产品摘要
{data.get('wealth_summary', '暂无理财产品')}

## 储蓄情况
{data.get('savings_summary', '暂无储蓄数据')}

请给出综合财务分析：

## 一、财务健康度评分
给出 1-100 分的健康度评分，并说明扣分项。

## 二、各板块一句话点评
分别对储蓄、股票、基金、理财各写一句总结性评价。

## 三、最需要关注的 3 件事
按紧急程度排序，每件事说明原因和影响。

## 四、下一步行动清单
给出 5 条具体可执行的操作建议（具体到"赎回 XX 产品，转投 XX"的程度）。

## 五、目标规划
按当前资产规模，如何在 1 年内实现资产增长 10%-15%？给出路径。

中文回答，不要加免责声明，直接给具体结论。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_stock(self, stock_info, holding_info, skip_cache=False):
        """分析单只股票"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        price = stock_info.get('price', 0)
        cost = holding_info.get('avg_cost', 0)
        pnl_pct = ((price - cost) / cost * 100) if cost and cost != 0 else 0

        cache_key = f"stock_{stock_info.get('code')}_{datetime.now().strftime('%Y%m%d%H')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        prompt = f"""分析港股 {stock_info.get('name', '')}（{stock_info.get('code', '')}）：

**行情数据：**
- 当前价: {price} {holding_info.get('currency', 'HKD')}
- 今日涨跌幅: {stock_info.get('change_pct', 0):.2f}%
- 今日区间: {stock_info.get('low', 0)} - {stock_info.get('high', 0)}

**我的持仓：**
- 持有 {holding_info.get('shares', 0)} 股
- 买入均价: {cost}
- 当前盈亏: {pnl_pct:.1f}%

请给出：
1. 📊 短期趋势判断（看涨/看跌/震荡）
2. 💰 操作建议：**买入** / **持有** / **减仓** / **卖出**，明确给出方向
3. 📝 理由（简要说明，100字内）

中文回答，直接给结论，不要免责声明。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_fund(self, fund_info, holding_info, skip_cache=False):
        """分析单只基金"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"fund_{holding_info.get('fund_code')}_{datetime.now().strftime('%Y%m%d%H')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        prompt = f"""分析基金 {holding_info.get('fund_name', '')}（{holding_info.get('fund_code', '')}）：

**基金信息：**
- 类型: {holding_info.get('fund_type', '未知')}
- 最新净值: {fund_info.get('nav', '未知')}
- 净值日期: {fund_info.get('date', '未知')}

**我的持仓：**
- 持有 {holding_info.get('shares', 0):.2f} 份
- 持有金额: ¥{holding_info.get('amount', 0):,.2f}
- 买入均价: {holding_info.get('avg_cost', 0)}
- 持有收益: {holding_info.get('profit', 0):,.2f}
- 收益率: {holding_info.get('profit_rate', '未知')}

请给出：
1. 📊 该基金近期表现评价
2. 💰 操作建议：**加仓** / **持有** / **减仓** / **赎回**
3. 📝 理由（100字内）

如果建议赎回，请额外推荐 1-2 只**同平台**的替代基金，格式如下：
## 转投建议
- 推荐基金：基金名称（基金代码）
- 推荐理由：XXX
- 风险等级：与原基金相近/更低/更高

中文回答，直接给结论。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_stocks_overall(self, stock_holdings, skip_cache=False):
        """整体分析所有股票持仓"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"stocks_overall_{_hash_data([h.get('stock_code') for h in stock_holdings])}_{datetime.now().strftime('%Y%m%d%H')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        total_value = sum(h.get('market_value', 0) for h in stock_holdings)

        holdings_lines = []
        for i, h in enumerate(stock_holdings, 1):
            mv = h.get('market_value', 0)
            pct = (mv / total_value * 100) if total_value else 0
            cost = h.get('avg_cost', 0)
            price = h.get('current_price', 0)
            pnl_pct = ((price - cost) / abs(cost) * 100) if cost and cost != 0 else 0
            notes = h.get('notes', '') or ''
            line = (
                f"{i}. **{h.get('stock_name', '')}**（{h.get('stock_code', '')}.{h.get('market', '')}）\n"
                f"   现价: {price} | 成本: {cost} | 盈亏: {'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%\n"
                f"   持有: {h.get('shares', 0):.0f}股 | 市值: ¥{mv:,.0f} | 占比: {pct:.1f}%\n"
                f"   今日涨跌: {h.get('change_pct', 0):.2f}% | 账户: {h.get('account_name', '')}"
            )
            if notes:
                line += f"\n   备注: {notes}"
            holdings_lines.append(line)

        prompt = f"""你是专业股票投资顾问。以下是我的全部股票持仓（共{len(stock_holdings)}只，总市值约¥{total_value:,.0f}）：

{chr(10).join(holdings_lines)}

请按以下结构分析：

## 一、持仓总览
用表格汇总每只股票的市值占比、盈亏情况，评价整体集中度和行业分散程度。

## 二、逐只股票分析
对**每只股票**给出明确判定：
- 🟢 继续持有 / 加仓（说明理由 + 目标价位）
- 🟡 观望等待（说明关注的信号）
- 🔴 建议减仓 / 卖出（说明理由 + 止损/止盈价位）

## 三、推荐入场股票
基于当前持仓的集中度和行业分布，推荐 3-5 只**尚未持有**的港股和美股：
- 每只给出：股票名称（代码）、所属行业、推荐理由（2-3句）
- 优先推荐与现有持仓形成互补的行业/赛道
- 标注风险等级：稳健/中等/进取
- 说明建议配置比例（占总股票仓位的 %）

## 四、风险提示
当前持仓最大的 2-3 个风险点及对策。

中文回答，不要加免责声明，直接给具体结论和操作方向。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_funds_overall(self, fund_holdings, skip_cache=False):
        """整体分析所有基金持仓"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"funds_overall_{_hash_data([h.get('fund_name') for h in fund_holdings])}_{datetime.now().strftime('%Y%m%d')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        total_amount = sum(h.get('amount', 0) or 0 for h in fund_holdings)

        holdings_lines = []
        for i, h in enumerate(fund_holdings, 1):
            amt = h.get('amount', 0) or 0
            pct = (amt / total_amount * 100) if total_amount else 0
            profit = h.get('profit', 0) or 0
            profit_rate = h.get('profit_rate', '未知')
            currency = h.get('currency', 'CNY')
            line = (
                f"{i}. **{h.get('fund_name', '')}**（{h.get('fund_code', '')}）\n"
                f"   类型: {h.get('fund_type', '未知')} | 账户: {h.get('account_name', '')}\n"
                f"   持有金额: {'¥' if currency == 'CNY' else currency}{amt:,.0f} | 占比: {pct:.1f}%\n"
                f"   持有收益: {'+' if profit >= 0 else ''}{profit:,.0f} | 收益率: {profit_rate}"
            )
            holdings_lines.append(line)

        prompt = f"""你是专业基金投资顾问。以下是我的全部基金持仓（共{len(fund_holdings)}只，总金额约¥{total_amount:,.0f}）：

{chr(10).join(holdings_lines)}

请按以下结构分析：

## 一、持仓总览
用表格汇总每只基金的持仓占比和收益情况。评价类型分散度、币种分散度。

## 二、逐只基金分析
对**每只基金**给出明确判定：
- 🟢 继续持有 / 加仓（说明理由）
- 🟡 持有观望（说明关注点）
- 🔴 建议赎回（说明理由 + 推荐同平台替代基金名称和代码）

## 三、优化建议
给出 3-4 条具体的调整建议。

中文回答，不要加免责声明，直接给具体结论和操作方向。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_wealth(self, wealth_holdings, skip_cache=False):
        """分析理财产品配置"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"wealth_{_hash_data([h.get('product_name') for h in wealth_holdings])}_{datetime.now().strftime('%Y%m%d')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        total_amount = sum(h.get('current_amount', 0) or h.get('buy_amount', 0) for h in wealth_holdings)

        holdings_lines = []
        for i, h in enumerate(wealth_holdings, 1):
            cur = h.get('current_amount', 0) or h.get('buy_amount', 0)
            pct = (cur / total_amount * 100) if total_amount else 0
            profit = h.get('total_profit', 0) or 0
            annual = (h.get('annual_rate', 0) or 0) * 100
            ptype = {'fixed': '定期', 'flexible': '活期', 'closed': '封闭期'}.get(h.get('product_type', ''), h.get('product_type', ''))
            line = (
                f"{i}. **{h.get('product_name', '')}**\n"
                f"   管理人: {h.get('manager', '') or '未知'} | 账户: {h.get('account_name', '')} | 类型: {ptype}\n"
                f"   买入: ¥{h.get('buy_amount', 0):,.0f} → 当前: ¥{cur:,.0f} | 占比: {pct:.1f}%\n"
                f"   累计收益: {'+' if profit >= 0 else ''}{profit:,.0f} | 年化: {annual:.2f}%\n"
                f"   买入日期: {h.get('buy_date', '') or '未知'} | 到期日期: {h.get('expire_date', '') or '无固定期限'}"
            )
            if h.get('notes'):
                line += f"\n   备注: {h.get('notes')}"
            holdings_lines.append(line)

        prompt = f"""你是专业家庭理财顾问。以下是我持有的全部理财产品（共{len(wealth_holdings)}个，总金额¥{total_amount:,.0f}）：

{chr(10).join(holdings_lines)}

请按以下结构分析：

## 一、持仓总览
用表格汇总每个产品的占比和年化收益，指出集中度是否过高。

## 二、逐个产品分析
对**每个产品**给出明确判定：
- 🟢 继续持有（说明理由）
- 🟡 到期赎回（说明理由 + 替代方案）
- 🔴 建议抛售（说明理由 + 资金去向）

## 三、优化建议
给出 3 条具体的资金调整建议。

中文回答，不要加免责声明，直接给具体结论和操作方向。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    def analyze_savings(self, savings_data, skip_cache=False):
        """分析储蓄策略"""
        if not self.available:
            return '💡 AI 服务未配置', None, False

        cache_key = f"savings_{_hash_data(savings_data)}_{datetime.now().strftime('%Y%m%d')}"
        cached = self._get_cache(cache_key, skip_cache)
        if cached:
            return cached

        prompt = f"""作为财务顾问，根据以下储蓄情况给出建议：

**储蓄概况：**
- 银行存款总额: ¥{savings_data.get('total_savings', 0):,.0f}
- 月收入: ¥{savings_data.get('monthly_income', 0):,.0f}
- 月支出: ¥{savings_data.get('monthly_expense', 0):,.0f}
- 月结余: ¥{savings_data.get('monthly_surplus', 0):,.0f}
- 储蓄目标: ¥{savings_data.get('savings_target', 0):,.0f}/年

请给出：
1. 📊 储蓄率评估（与推荐标准对比）
2. 💰 储蓄策略建议（如何分配存款）
3. 📝 具体行动建议（2-3条）

中文回答，300字内。"""

        advice = self._call_api(prompt)
        if advice and not _is_error(advice):
            self._set_cache(cache_key, advice)
        return self._make_result(advice, cache_key)

    # ========== API 调用 ==========

    def _get_chat_url(self):
        """获取对话补全 API URL"""
        return self._custom_url or f'{self.BASE_URL}/chat/completions'

    def _get_images_url(self):
        """获取图像生成 API URL"""
        return f'{self.BASE_URL}/images/generations'

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def _extract_text(self, data):
        """从 API 响应中提取文本内容"""
        # OpenAI 兼容格式：choices[0].message.content
        choices = data.get('choices', [])
        if choices:
            return choices[0].get('message', {}).get('content', '')
        # Anthropic 兼容格式：content[0].text
        content = data.get('content', [])
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                return item.get('text', '')
        return None

    def _call_api(self, prompt):
        """调用文本模型（财务分析）"""
        if not self.available:
            return None

        try:
            resp = requests.post(
                self._get_chat_url(),
                headers=self._headers(),
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': '你是专业的家庭财务顾问，给出务实、具体、可操作的建议。不要加免责声明。'},
                        {'role': 'user', 'content': prompt},
                    ],
                    'max_tokens': 2000,
                },
                timeout=120
            )
            resp.raise_for_status()
            text = self._extract_text(resp.json())
            if text:
                return text
            print(f"AI 未知响应格式: {json.dumps(resp.json(), ensure_ascii=False)[:500]}")
            return '❌ AI 返回格式异常，请重试'
        except requests.exceptions.Timeout:
            return '⏳ AI 分析超时，请稍后重试'
        except requests.exceptions.HTTPError as e:
            return f'❌ AI 服务错误: {e.response.status_code}'
        except Exception as e:
            return f'❌ AI 服务异常: {str(e)}'

    def call_vision(self, prompt, image_url=None, image_base64=None):
        """
        调用多模态模型（图片理解/OCR）
        支持传入 image_url 或 image_base64（二选一）
        返回: 文本字符串 或 None
        """
        if not self.available:
            return None

        # 构建多模态消息
        content_parts = [{'type': 'text', 'text': prompt}]
        if image_base64:
            content_parts.append({
                'type': 'image_url',
                'image_url': {'url': f'data:image/png;base64,{image_base64}'}
            })
        elif image_url:
            content_parts.append({
                'type': 'image_url',
                'image_url': {'url': image_url}
            })

        try:
            resp = requests.post(
                self._get_chat_url(),
                headers=self._headers(),
                json={
                    'model': self.vision_model,
                    'messages': [
                        {'role': 'user', 'content': content_parts}
                    ],
                    'max_tokens': 4000,
                },
                timeout=120
            )
            resp.raise_for_status()
            return self._extract_text(resp.json())
        except requests.exceptions.Timeout:
            return '⏳ 图片识别超时，请稍后重试'
        except requests.exceptions.HTTPError as e:
            return f'❌ 图片识别服务错误: {e.response.status_code}'
        except Exception as e:
            return f'❌ 图片识别异常: {str(e)}'

    def call_image_gen(self, prompt, size='1024x1024'):
        """
        调用图像生成模型（CogView-4）
        返回: 图片 URL 列表 或 None
        """
        if not self.available:
            return None

        try:
            resp = requests.post(
                self._get_images_url(),
                headers=self._headers(),
                json={
                    'model': self.image_model,
                    'prompt': prompt,
                    'size': size,
                },
                timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            images = data.get('data', [])
            return [img.get('url') for img in images if img.get('url')]
        except Exception as e:
            print(f"图像生成失败: {e}")
            return None

    # ========== 缓存（返回三元组） ==========

    def _get_cache(self, key, skip_cache=False):
        """从数据库获取缓存，命中返回 (text, generated_at, True)，未命中返回 None"""
        if skip_cache:
            return None
        try:
            from models import AiAdviceCache
            record = AiAdviceCache.query.filter_by(advice_key=key).first()
            if record and (datetime.now() - record.generated_at) < timedelta(hours=AI_CACHE_TTL_HOURS):
                return (record.advice_text, record.generated_at, True)
            return None
        except Exception:
            return None

    def _set_cache(self, key, text):
        """写入缓存"""
        try:
            from models import AiAdviceCache, db
            record = AiAdviceCache.query.filter_by(advice_key=key).first()
            now = datetime.now()
            if record:
                record.advice_text = text
                record.model_used = self.model
                record.generated_at = now
            else:
                db.session.add(AiAdviceCache(
                    advice_key=key, advice_text=text,
                    model_used=self.model, generated_at=now
                ))
            db.session.commit()
        except Exception as e:
            print(f"AI 缓存写入失败: {e}")
            try:
                from models import db
                db.session.rollback()
            except Exception:
                pass

    def _make_result(self, advice, cache_key):
        """构造统一返回格式 (text, generated_at, from_cache)"""
        if not advice:
            return ('❌ AI 分析失败', None, False)
        # 查刚写入的缓存获取时间
        try:
            from models import AiAdviceCache
            record = AiAdviceCache.query.filter_by(advice_key=cache_key).first()
            return (advice, record.generated_at if record else datetime.now(), False)
        except Exception:
            return (advice, datetime.now(), False)

    # ========== 历史记录 ==========

    @staticmethod
    def save_history(user_id, advice_type, advice_text, model_used=None):
        """保存 AI 分析到历史记录"""
        try:
            from models import AiAdviceHistory, db
            db.session.add(AiAdviceHistory(
                user_id=user_id,
                advice_type=advice_type,
                advice_text=advice_text,
                model_used=model_used,
                generated_at=datetime.now()
            ))
            db.session.commit()
        except Exception as e:
            print(f"AI 历史写入失败: {e}")
            try:
                from models import db
                db.session.rollback()
            except Exception:
                pass

    @staticmethod
    def get_history(advice_type, limit=20):
        """获取历史记录列表"""
        try:
            from models import AiAdviceHistory
            records = AiAdviceHistory.query.filter_by(
                advice_type=advice_type
            ).order_by(AiAdviceHistory.generated_at.desc()).limit(limit).all()
            return [{
                'id': r.id,
                'advice_type': r.advice_type,
                'preview': r.advice_text[:80].replace('\n', ' ') + ('...' if len(r.advice_text) > 80 else ''),
                'model_used': r.model_used,
                'generated_at': r.generated_at.strftime('%Y-%m-%d %H:%M'),
            } for r in records]
        except Exception:
            return []

    @staticmethod
    def get_history_detail(record_id):
        """获取单条历史详情"""
        try:
            from models import AiAdviceHistory
            r = AiAdviceHistory.query.get(record_id)
            if not r:
                return None
            return {
                'id': r.id,
                'advice_type': r.advice_type,
                'advice_text': r.advice_text,
                'model_used': r.model_used,
                'generated_at': r.generated_at.strftime('%Y-%m-%d %H:%M'),
            }
        except Exception:
            return None


def _hash_data(data):
    """生成数据指纹用于缓存 key"""
    return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:12]


def _is_error(text):
    """判断 AI 返回是否为错误信息（不应缓存）"""
    if not text:
        return True
    return text.startswith('❌') or text.startswith('⏳') or text.startswith('💡')

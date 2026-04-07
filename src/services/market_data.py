"""
行情数据服务层
使用新浪财经接口获取股票行情（国内稳定可用），AKShare 获取基金净值。
"""
import json
import re
import requests
from datetime import datetime, timedelta


# 行情缓存有效期（分钟）
CACHE_TTL_MINUTES = 5

# 新浪财经请求头
SINA_HEADERS = {
    'Referer': 'https://finance.sina.com.cn',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


class MarketDataService:
    """行情数据服务"""

    @staticmethod
    def get_stock_quote(stock_code, market='HK'):
        """获取单只股票实时行情（新浪财经，带缓存）"""
        cache_key = f"stock_{market}_{stock_code}"
        cached = MarketDataService._get_cache(cache_key)
        if cached:
            return cached

        try:
            if market == 'HK':
                result = _fetch_sina_hk(stock_code)
            elif market == 'A':
                result = _fetch_sina_a(stock_code)
            elif market == 'US':
                result = _fetch_sina_us(stock_code)
            else:
                return {'error': f'不支持的市场: {market}'}

            if result and 'error' not in result:
                result['market'] = market
                result['updated_at'] = datetime.now().isoformat()
                result['stale'] = False
                MarketDataService._set_cache(cache_key, result)
                return result
            return result or {'error': '获取行情失败'}

        except Exception as e:
            stale = MarketDataService._get_cache(cache_key, ignore_ttl=True)
            if stale:
                stale['stale'] = True
                return stale
            return {'error': f'获取行情失败: {str(e)}'}

    @staticmethod
    def get_batch_stock_quotes(holdings):
        """批量获取股票行情（新浪支持批量请求）"""
        results = {}
        if not holdings:
            return results

        # 构建新浪批量查询代码列表
        sina_codes = []
        code_map = {}  # sina_code -> [holdings]（同一股票可能有多条持仓）
        for h in holdings:
            if h.market == 'HK':
                sc = f'rt_hk{h.stock_code}'
            elif h.market == 'A':
                # A股需要判断沪深：6开头=sh，其他=sz
                prefix = 'sh' if h.stock_code.startswith('6') else 'sz'
                sc = f'{prefix}{h.stock_code}'
            elif h.market == 'US':
                sc = f'gb_{h.stock_code.lower()}'
            else:
                continue
            if sc not in code_map:
                sina_codes.append(sc)  # 去重，同一代码只请求一次
                code_map[sc] = []
            code_map[sc].append(h)

        if not sina_codes:
            return results

        try:
            url = f'https://hq.sinajs.cn/list={",".join(sina_codes)}'
            resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
            resp.encoding = 'gbk'

            for line in resp.text.strip().split('\n'):
                if '=' not in line:
                    continue
                var_part, val_part = line.split('=', 1)
                # 提取 sina_code: var hq_str_rt_hk00700="..."
                sc = var_part.split('_str_')[1].strip() if '_str_' in var_part else ''
                holding_list = code_map.get(sc)
                if not holding_list:
                    continue

                data_str = val_part.strip(' ";\n')
                if not data_str:
                    for h in holding_list:
                        results[h.id] = {'error': '无数据'}
                    continue

                market = holding_list[0].market
                if market == 'HK':
                    quote = _parse_sina_hk(holding_list[0].stock_code, data_str)
                elif market == 'A':
                    quote = _parse_sina_a(holding_list[0].stock_code, data_str)
                else:
                    quote = {'error': '解析失败'}

                if quote and 'error' not in quote:
                    quote['market'] = market
                    quote['updated_at'] = datetime.now().isoformat()
                    quote['stale'] = False
                    cache_key = f"stock_{market}_{holding_list[0].stock_code}"
                    MarketDataService._set_cache(cache_key, quote)

                # 同一股票的所有持仓都赋值
                for h in holding_list:
                    results[h.id] = quote

        except Exception as e:
            for h in holdings:
                if h.id not in results:
                    cache_key = f"stock_{h.market}_{h.stock_code}"
                    stale = MarketDataService._get_cache(cache_key, ignore_ttl=True)
                    if stale:
                        stale['stale'] = True
                        results[h.id] = stale
                    else:
                        results[h.id] = {'error': f'获取失败: {str(e)}'}

        return results

    @staticmethod
    def get_fund_nav(fund_code):
        """获取基金最新净值（AKShare，带缓存）"""
        cache_key = f"fund_{fund_code}"
        cached = MarketDataService._get_cache(cache_key)
        if cached:
            return cached

        # 海外基金代码不走 AKShare
        if not fund_code.isdigit() or len(fund_code) != 6:
            return {'code': fund_code, 'nav': None, 'note': '海外基金暂不支持实时净值'}

        try:
            import akshare as ak
            df = ak.fund_open_fund_info_em(fund=fund_code, indicator="单位净值走势")
            if df.empty:
                return {'code': fund_code, 'error': '未找到基金数据'}

            latest = df.iloc[-1]
            result = {
                'code': fund_code,
                'nav': _safe_float(latest.get('单位净值')),
                'date': str(latest.get('净值日期', '')),
                'updated_at': datetime.now().isoformat(),
                'stale': False
            }
            MarketDataService._set_cache(cache_key, result)
            return result

        except Exception as e:
            stale = MarketDataService._get_cache(cache_key, ignore_ttl=True)
            if stale:
                stale['stale'] = True
                return stale
            return {'code': fund_code, 'error': f'获取净值失败: {str(e)}'}

    @staticmethod
    def search_stock(keyword, market='HK'):
        """搜索股票（AKShare 备选，新浪不支持搜索）"""
        try:
            import akshare as ak
            if market == 'HK':
                df = ak.stock_hk_spot_em()
            elif market == 'A':
                df = ak.stock_zh_a_spot_em()
            elif market == 'US':
                df = ak.stock_us_spot_em()
            else:
                return []

            mask = df['代码'].str.contains(keyword, na=False) | \
                   df['名称'].str.contains(keyword, na=False)
            matched = df[mask][['代码', '名称']].head(20)
            return [{'code': row['代码'], 'name': row['名称']} for _, row in matched.iterrows()]

        except Exception as e:
            print(f"AKShare搜索失败，回退到空结果: {e}")
            return []

    # ========== 缓存 ==========

    @staticmethod
    def _get_cache(key, ignore_ttl=False):
        try:
            from models import MarketDataCache
            record = MarketDataCache.query.filter_by(data_key=key).first()
            if not record:
                return None
            if not ignore_ttl:
                if (datetime.now() - record.fetched_at) >= timedelta(minutes=CACHE_TTL_MINUTES):
                    return None
            return json.loads(record.data_json)
        except Exception:
            return None

    @staticmethod
    def _set_cache(key, data):
        try:
            from models import MarketDataCache, db
            record = MarketDataCache.query.filter_by(data_key=key).first()
            now = datetime.now()
            if record:
                record.data_json = json.dumps(data, ensure_ascii=False)
                record.fetched_at = now
            else:
                record = MarketDataCache(data_key=key, data_json=json.dumps(data, ensure_ascii=False), fetched_at=now)
                db.session.add(record)
            db.session.commit()
        except Exception as e:
            print(f"缓存写入失败: {e}")
            try:
                from models import db
                db.session.rollback()
            except Exception:
                pass


# ========== 新浪财经解析函数 ==========

def _fetch_sina_hk(code):
    """新浪港股行情"""
    url = f'https://hq.sinajs.cn/list=rt_hk{code}'
    resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
    resp.encoding = 'gbk'
    data_str = resp.text.split('"')[1] if '"' in resp.text else ''
    if not data_str:
        return {'error': f'港股 {code} 无数据'}
    return _parse_sina_hk(code, data_str)


def _parse_sina_hk(code, data_str):
    """解析新浪港股数据
    格式: 英文名,中文名,开盘价,最高价,最低价,收盘价(前收),现价,涨跌额,涨跌幅,买入价,卖出价,成交额,成交量,...
    """
    parts = data_str.split(',')
    if len(parts) < 13:
        return {'error': f'港股 {code} 数据格式异常'}

    return {
        'code': code,
        'name': parts[1],
        'price': _safe_float(parts[6]),
        'change_amount': _safe_float(parts[7]),
        'change_pct': _safe_float(parts[8]),
        'open': _safe_float(parts[2]),
        'high': _safe_float(parts[3]),
        'low': _safe_float(parts[4]),
        'prev_close': _safe_float(parts[5]),
        'turnover': _safe_float(parts[11]),
        'volume': _safe_int(parts[12]),
    }


def _fetch_sina_a(code):
    """新浪A股行情"""
    prefix = 'sh' if code.startswith('6') else 'sz'
    url = f'https://hq.sinajs.cn/list={prefix}{code}'
    resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
    resp.encoding = 'gbk'
    data_str = resp.text.split('"')[1] if '"' in resp.text else ''
    if not data_str:
        return {'error': f'A股 {code} 无数据'}
    return _parse_sina_a(code, data_str)


def _parse_sina_a(code, data_str):
    """解析新浪A股数据
    格式: 名称,今开,昨收,现价,最高,最低,...,成交量,成交额,...
    """
    parts = data_str.split(',')
    if len(parts) < 32:
        return {'error': f'A股 {code} 数据格式异常'}

    price = _safe_float(parts[3])
    prev_close = _safe_float(parts[2])
    change_amount = price - prev_close
    change_pct = (change_amount / prev_close * 100) if prev_close else 0

    return {
        'code': code,
        'name': parts[0],
        'price': price,
        'change_amount': round(change_amount, 3),
        'change_pct': round(change_pct, 2),
        'open': _safe_float(parts[1]),
        'high': _safe_float(parts[4]),
        'low': _safe_float(parts[5]),
        'prev_close': prev_close,
        'volume': _safe_int(parts[8]),
        'turnover': _safe_float(parts[9]),
    }


def _fetch_sina_us(code):
    """新浪美股行情"""
    url = f'https://hq.sinajs.cn/list=gb_{code.lower()}'
    resp = requests.get(url, headers=SINA_HEADERS, timeout=10)
    resp.encoding = 'gbk'
    data_str = resp.text.split('"')[1] if '"' in resp.text else ''
    if not data_str:
        return {'error': f'美股 {code} 无数据'}

    parts = data_str.split(',')
    if len(parts) < 10:
        return {'error': f'美股 {code} 数据格式异常'}

    return {
        'code': code,
        'name': parts[0],
        'price': _safe_float(parts[1]),
        'change_pct': _safe_float(parts[2]),
        'change_amount': _safe_float(parts[4]),
        'volume': _safe_int(parts[10]) if len(parts) > 10 else 0,
    }


def _safe_float(val):
    try:
        if val is None or val == '' or val == '-':
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val):
    try:
        if val is None or val == '' or val == '-':
            return 0
        return int(float(val))
    except (ValueError, TypeError):
        return 0

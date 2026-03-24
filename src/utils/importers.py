"""文件解析器 - 支持微信账单、支付宝账单、标准模板CSV、Excel文件"""
import csv
import os
import re
from datetime import datetime


def sanitize_cell(value):
    """清理单元格值，防止 CSV 注入攻击

    去除开头的 =, +, -, @ 字符
    """
    if value is None:
        return ''
    value = str(value).strip()
    while value and value[0] in ('=', '+', '-', '@'):
        value = value[1:]
    return value


def _read_csv_lines(filepath):
    """读取 CSV 文件，自动检测编码"""
    for encoding in ('utf-8', 'utf-8-sig', 'gbk', 'gb18030'):
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.readlines()
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f'无法识别文件编码: {filepath}')


def _parse_date(date_str):
    """解析日期字符串，返回 YYYY-MM-DD 格式"""
    date_str = str(date_str).strip()
    # 处理 datetime 格式 '2026-03-01 12:00:00'
    if ' ' in date_str:
        date_str = date_str.split(' ')[0]
    # 处理斜杠格式 '2026/03/01'
    date_str = date_str.replace('/', '-')
    return date_str


def _map_type(raw_type):
    """映射交易类型"""
    raw_type = str(raw_type).strip()
    if raw_type in ('支出',):
        return 'expense'
    elif raw_type in ('收入',):
        return 'income'
    return None


def _clean_amount(amount_str):
    """清理金额字符串，去除货币符号"""
    amount_str = str(amount_str).strip()
    # 去除 ¥ 符号和空格
    amount_str = amount_str.replace('¥', '').replace('￥', '').replace(',', '').strip()
    try:
        return float(amount_str)
    except (ValueError, TypeError):
        return 0.0


def parse_template_csv(filepath):
    """解析标准模板 CSV 文件

    列格式: 日期,类型,金额,分类,描述
    """
    lines = _read_csv_lines(filepath)
    reader = csv.DictReader(lines)

    results = []
    for row in reader:
        tx_type = _map_type(row.get('类型', ''))
        if tx_type is None:
            continue

        results.append({
            'date': _parse_date(row.get('日期', '')),
            'type': tx_type,
            'amount': _clean_amount(row.get('金额', '0')),
            'category_name': sanitize_cell(row.get('分类', '')),
            'description': sanitize_cell(row.get('描述', '')),
            'order_no': None,
        })

    return results


def parse_wechat_csv(filepath):
    """解析微信支付账单 CSV 文件

    微信账单前 16 行为概要信息，第 17 行为表头
    """
    lines = _read_csv_lines(filepath)

    # 跳过前 16 行概要
    data_lines = lines[16:]
    if not data_lines:
        return []

    reader = csv.DictReader(data_lines)

    results = []
    for row in reader:
        raw_type = row.get('收/支', '').strip()
        tx_type = _map_type(raw_type)
        if tx_type is None:
            continue

        amount = _clean_amount(row.get('金额(元)', '0'))
        description_parts = []
        if row.get('交易对方', '').strip():
            description_parts.append(sanitize_cell(row.get('交易对方', '')))
        if row.get('商品', '').strip():
            description_parts.append(sanitize_cell(row.get('商品', '')))
        description = ' '.join(description_parts) if description_parts else ''

        order_no = row.get('交易单号', '').strip()

        results.append({
            'date': _parse_date(row.get('交易时间', '')),
            'type': tx_type,
            'amount': amount,
            'category_name': sanitize_cell(row.get('交易类型', '')),
            'description': description,
            'order_no': sanitize_cell(order_no) if order_no else None,
        })

    return results


def parse_alipay_csv(filepath):
    """解析支付宝账单 CSV 文件

    支付宝账单前几行为概要信息，需找到包含'交易时间'的表头行
    """
    lines = _read_csv_lines(filepath)

    # 找到表头行
    header_idx = None
    for i, line in enumerate(lines):
        if '交易时间' in line:
            header_idx = i
            break

    if header_idx is None:
        return []

    data_lines = lines[header_idx:]
    reader = csv.DictReader(data_lines)

    results = []
    for row in reader:
        raw_type = row.get('收/支', '').strip()
        tx_type = _map_type(raw_type)
        if tx_type is None:
            continue

        amount = _clean_amount(row.get('金额', '0'))

        description_parts = []
        if row.get('交易对方', '').strip():
            description_parts.append(sanitize_cell(row.get('交易对方', '')))
        if row.get('商品说明', '').strip():
            description_parts.append(sanitize_cell(row.get('商品说明', '')))
        description = ' '.join(description_parts) if description_parts else ''

        order_no = row.get('交易订单号', '').strip()

        results.append({
            'date': _parse_date(row.get('交易时间', '')),
            'type': tx_type,
            'amount': amount,
            'category_name': sanitize_cell(row.get('交易分类', '')),
            'description': description,
            'order_no': sanitize_cell(order_no) if order_no else None,
        })

    return results


def parse_excel(filepath):
    """解析 Excel (.xlsx) 文件

    列格式同标准模板: 日期,类型,金额,分类,描述
    """
    import openpyxl

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return []

    # 第一行为表头
    headers = [str(h).strip() if h else '' for h in rows[0]]

    results = []
    for row in rows[1:]:
        if not row or all(cell is None for cell in row):
            continue

        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(row):
                row_dict[header] = row[i]

        tx_type = _map_type(row_dict.get('类型', ''))
        if tx_type is None:
            continue

        date_val = row_dict.get('日期', '')
        if hasattr(date_val, 'strftime'):
            date_str = date_val.strftime('%Y-%m-%d')
        else:
            date_str = _parse_date(str(date_val))

        amount = row_dict.get('金额', 0)
        if isinstance(amount, str):
            amount = _clean_amount(amount)
        else:
            amount = float(amount) if amount else 0.0

        results.append({
            'date': date_str,
            'type': tx_type,
            'amount': amount,
            'category_name': sanitize_cell(row_dict.get('分类', '')),
            'description': sanitize_cell(row_dict.get('描述', '')),
            'order_no': None,
        })

    wb.close()
    return results


def detect_source_type(filepath):
    """检测文件来源类型

    Returns: 'wechat', 'alipay', 'template'
    """
    lines = _read_csv_lines(filepath)
    # 检查前 5 行
    head = ''.join(lines[:5])

    if '微信' in head:
        return 'wechat'
    elif '支付宝' in head:
        return 'alipay'
    else:
        return 'template'


def map_category(raw_name, categories):
    """将原始分类名映射到系统分类 ID

    Args:
        raw_name: 原始分类名称
        categories: 分类列表 [{'id': int, 'name': str}, ...]

    Returns: 分类 ID 或 None
    """
    if not raw_name or not categories:
        return None

    raw_name = str(raw_name).strip()

    # 精确匹配
    for cat in categories:
        if cat['name'] == raw_name:
            return cat['id']

    # 模糊匹配：原始名称包含分类名
    for cat in categories:
        if cat['name'] in raw_name:
            return cat['id']

    return None

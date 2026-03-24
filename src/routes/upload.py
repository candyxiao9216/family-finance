"""批量导入路由模块"""
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, redirect, render_template, request, session, url_for, flash, jsonify, send_file
from sqlalchemy import func

from models import db, User, Transaction, Category, ImportRecord
from utils.importers import (
    parse_template_csv, parse_wechat_csv, parse_alipay_csv,
    parse_excel, detect_source_type, map_category
)

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

ALLOWED_EXTENSIONS = {'.csv', '.xlsx'}


def _allowed_file(filename):
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


def _detect_duplicates(records, user_id):
    """检测重复记录"""
    # 查询近6个月的交易
    six_months_ago = (datetime.now() - timedelta(days=180)).date()
    existing_txns = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.transaction_date >= six_months_ago
    ).all()

    # 构建去重键集合
    existing_keys = set()
    existing_orders = set()
    for t in existing_txns:
        desc = t.description or ''
        # 提取订单号
        if '[单号:' in desc:
            start = desc.index('[单号:') + 4
            end = desc.index(']', start)
            existing_orders.add(desc[start:end])
        # 组合键
        key = f"{t.transaction_date}|{float(t.amount)}|{desc}"
        existing_keys.add(key)

    # 标记重复
    for record in records:
        record['is_duplicate'] = False
        if record.get('order_no') and record['order_no'] in existing_orders:
            record['is_duplicate'] = True
        elif not record.get('order_no'):
            desc = record.get('description', '') or ''
            key = f"{record['date']}|{record['amount']}|{desc}"
            if key in existing_keys:
                record['is_duplicate'] = True

    return records


@upload_bp.route('/')
def upload_page():
    """导入页面"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    family = user.family if user else None
    current_view = request.args.get('view', 'personal')

    # 导入历史
    history = ImportRecord.query.filter_by(user_id=user_id).order_by(
        ImportRecord.import_time.desc()
    ).limit(10).all()

    return render_template('upload.html',
                           history=history,
                           current_view=current_view,
                           family=family,
                           username=session.get('nickname', session.get('username', '用户')))


@upload_bp.route('/parse', methods=['POST'])
def parse_file():
    """解析上传文件，返回预览数据"""
    user_id = session.get('user_id')

    if 'file' not in request.files:
        return jsonify({'error': '未找到文件'}), 400

    file = request.files['file']
    if not file.filename or not _allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式，仅支持 .csv 和 .xlsx'}), 400

    source_type = request.form.get('source_type', '')

    # 保存临时文件
    _, ext = os.path.splitext(file.filename)
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    file.save(tmp.name)
    tmp.close()

    try:
        # 解析
        if ext.lower() == '.xlsx':
            records = parse_excel(tmp.name)
            source_type = source_type or 'template'
        elif source_type == 'wechat':
            records = parse_wechat_csv(tmp.name)
        elif source_type == 'alipay':
            records = parse_alipay_csv(tmp.name)
        else:
            # 自动检测
            if not source_type:
                source_type = detect_source_type(tmp.name)
            if source_type == 'wechat':
                records = parse_wechat_csv(tmp.name)
            elif source_type == 'alipay':
                records = parse_alipay_csv(tmp.name)
            else:
                records = parse_template_csv(tmp.name)
                source_type = 'template'

        # 分类映射
        categories = Category.query.filter(
            (Category.user_id == None) | (Category.user_id == user_id)
        ).all()
        cat_list = [{'id': c.id, 'name': c.name} for c in categories]

        for record in records:
            cat_name = record.get('category_name')
            record['category_id'] = map_category(cat_name, cat_list)

        # 去重检测
        records = _detect_duplicates(records, user_id)

        duplicate_count = sum(1 for r in records if r.get('is_duplicate'))

        return jsonify({
            'records': records,
            'total': len(records),
            'duplicate_count': duplicate_count,
            'source_type': source_type,
            'file_name': file.filename,
            'categories': cat_list
        })

    except Exception as e:
        return jsonify({'error': f'解析失败: {str(e)}'}), 400

    finally:
        os.unlink(tmp.name)


@upload_bp.route('/confirm', methods=['POST'])
def confirm_import():
    """确认导入"""
    user_id = session.get('user_id')
    data = request.get_json()

    if not data or 'records' not in data:
        return jsonify({'error': '无效的导入数据'}), 400

    records = data['records']
    source_type = data.get('source_type', 'template')
    file_name = data.get('file_name', 'unknown')

    imported = 0
    skipped = 0

    for record in records:
        if record.get('skip'):
            skipped += 1
            continue

        try:
            txn_date = datetime.strptime(record['date'], '%Y-%m-%d').date()
        except (ValueError, KeyError):
            skipped += 1
            continue

        # 构建 description（含订单号）
        desc = record.get('description', '') or ''
        if record.get('order_no'):
            desc = f"{desc} [单号:{record['order_no']}]".strip()

        txn = Transaction(
            user_id=user_id,
            amount=Decimal(str(record['amount'])),
            type=record['type'],
            category_id=record.get('category_id'),
            description=desc or None,
            transaction_date=txn_date
        )
        db.session.add(txn)
        imported += 1

    # 记录导入历史
    import_record = ImportRecord(
        user_id=user_id,
        file_name=file_name,
        total_rows=len(records),
        imported_count=imported,
        skipped_count=skipped,
        duplicate_count=data.get('duplicate_count', 0),
        source_type=source_type,
        status='completed' if imported > 0 else 'failed'
    )
    db.session.add(import_record)
    db.session.commit()

    return jsonify({
        'imported_count': imported,
        'skipped_count': skipped,
        'total': len(records)
    })


@upload_bp.route('/template')
def download_template():
    """下载标准导入模板"""
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'static', 'import_template.csv'
    )
    return send_file(template_path, as_attachment=True, download_name='导入模板.csv')

"""批量导入路由测试"""
import sys
import os
import io
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from decimal import Decimal
from datetime import date as dt_date
from flask import Flask
from models import db, User, Category, Transaction, ImportRecord
from config import BASE_DIR
import json


def _create_test_app():
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db.name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret'
    app.config['TESTING'] = True
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
    app.static_folder = str(BASE_DIR / 'src' / 'static')
    app.template_folder = str(BASE_DIR / 'src' / 'templates')

    db.init_app(app)
    return app, temp_db.name


def test_upload_parse_template():
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='importer', nickname='导入者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    csv_content = '日期,类型,金额,分类,描述\n2026-03-01,支出,35.50,餐饮,午餐\n'
    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'test.csv'),
            'source_type': 'template'}

    resp = client.post('/upload/parse', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert len(json_data['records']) == 1
    assert json_data['records'][0]['amount'] == 35.50

    print("✅ test_upload_parse_template passed")
    os.unlink(db_path)


def test_upload_confirm():
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='confirmer', nickname='确认者')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        cat_id = cat.id
        user_id = user.id

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    resp = client.post('/upload/confirm',
                       data=json.dumps({
                           'records': [
                               {'date': '2026-03-01', 'type': 'expense', 'amount': 35.50,
                                'description': '午餐', 'category_id': cat_id}
                           ],
                           'source_type': 'template',
                           'file_name': 'test.csv'
                       }),
                       content_type='application/json')
    assert resp.status_code == 200
    json_data = resp.get_json()
    assert json_data['imported_count'] == 1

    with app.app_context():
        assert Transaction.query.count() == 1
        assert ImportRecord.query.count() == 1

    print("✅ test_upload_confirm passed")
    os.unlink(db_path)


def test_upload_detect_duplicate():
    app, db_path = _create_test_app()
    from routes.upload import upload_bp
    app.register_blueprint(upload_bp)

    with app.app_context():
        db.create_all()
        cat = Category(name='餐饮', type='expense', is_default=True)
        db.session.add(cat)
        user = User(username='dedup', nickname='去重测试')
        user.set_password('pass123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id

        existing = Transaction(
            user_id=user_id, amount=Decimal('35.50'), type='expense',
            category_id=cat.id, description='午餐 [单号:TX001]',
            transaction_date=dt_date(2026, 3, 1)
        )
        db.session.add(existing)
        db.session.commit()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id

    # WeChat CSV with duplicate order TX001 and new TX003
    header = '\n'.join([f'概要行{i}' for i in range(16)]) + '\n'
    csv_content = header + '交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n'
    csv_content += '2026-03-01 12:00:00,商户消费,肯德基,午餐,支出,¥35.50,微信支付,支付成功,TX001,,\n'
    csv_content += '2026-03-03 12:00:00,商户消费,麦当劳,午餐,支出,¥28.00,微信支付,支付成功,TX003,,\n'

    data = {'file': (io.BytesIO(csv_content.encode('utf-8')), 'wechat.csv'),
            'source_type': 'wechat'}
    resp = client.post('/upload/parse', data=data, content_type='multipart/form-data')
    json_data = resp.get_json()

    duplicates = [r for r in json_data['records'] if r.get('is_duplicate')]
    assert len(duplicates) == 1
    assert duplicates[0]['order_no'] == 'TX001'

    print("✅ test_upload_detect_duplicate passed")
    os.unlink(db_path)


if __name__ == '__main__':
    test_upload_parse_template()
    test_upload_confirm()
    test_upload_detect_duplicate()

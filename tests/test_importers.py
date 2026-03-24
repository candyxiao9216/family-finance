"""文件解析器测试"""
import sys
import os
import tempfile
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.importers import parse_template_csv, parse_wechat_csv, parse_alipay_csv, sanitize_cell, parse_excel, detect_source_type, map_category


def test_sanitize_cell():
    assert sanitize_cell('=cmd|xxx') == "cmd|xxx"
    assert sanitize_cell('+cmd') == "cmd"
    assert sanitize_cell('-cmd') == "cmd"
    assert sanitize_cell('@cmd') == "cmd"
    assert sanitize_cell('正常文本') == '正常文本'
    assert sanitize_cell(None) == ''
    print("✅ test_sanitize_cell passed")


def test_parse_template_csv():
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    writer = csv.writer(tmp)
    writer.writerow(['日期', '类型', '金额', '分类', '描述'])
    writer.writerow(['2026-03-01', '支出', '35.50', '餐饮', '午餐'])
    writer.writerow(['2026-03-02', '收入', '50000', '工资', '3月工资'])
    tmp.close()

    result = parse_template_csv(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    assert result[0]['category_name'] == '餐饮'
    assert result[1]['type'] == 'income'
    print("✅ test_parse_template_csv passed")
    os.unlink(tmp.name)


def test_parse_wechat_csv():
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    for i in range(16):
        tmp.write(f'概要行{i}\n')
    tmp.write('交易时间,交易类型,交易对方,商品,收/支,金额(元),支付方式,当前状态,交易单号,商户单号,备注\n')
    tmp.write('2026-03-01 12:00:00,商户消费,肯德基,午餐,支出,¥35.50,微信支付,支付成功,TX001,,\n')
    tmp.write('2026-03-02 09:00:00,转账,张三,,收入,¥1000.00,微信支付,已收钱,TX002,,\n')
    tmp.close()

    result = parse_wechat_csv(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    assert result[0]['order_no'] == 'TX001'
    assert result[1]['type'] == 'income'
    assert result[1]['amount'] == 1000.0
    print("✅ test_parse_wechat_csv passed")
    os.unlink(tmp.name)


def test_parse_alipay_csv():
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp.write('支付宝交易记录\n')
    tmp.write('账号:xxx\n')
    tmp.write('起始日期:2026-03-01\n')
    tmp.write('终止日期:2026-03-31\n')
    tmp.write('\n')
    tmp.write('交易时间,交易分类,交易对方,对方账号,商品说明,收/支,金额,收/付款方式,交易状态,交易订单号,商家订单号,备注\n')
    tmp.write('2026-03-01 12:00:00,餐饮美食,饿了么,,午餐外卖,支出,25.00,花呗,交易成功,ALI001,,\n')
    tmp.close()

    result = parse_alipay_csv(tmp.name)
    assert len(result) == 1
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 25.0
    assert result[0]['order_no'] == 'ALI001'
    print("✅ test_parse_alipay_csv passed")
    os.unlink(tmp.name)


def test_parse_excel():
    import openpyxl
    tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
    tmp.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['日期', '类型', '金额', '分类', '描述'])
    ws.append(['2026-03-01', '支出', 35.50, '餐饮', '午餐'])
    ws.append(['2026-03-02', '收入', 50000, '工资', '3月工资'])
    wb.save(tmp.name)

    result = parse_excel(tmp.name)
    assert len(result) == 2
    assert result[0]['type'] == 'expense'
    assert result[0]['amount'] == 35.50
    print("✅ test_parse_excel passed")
    os.unlink(tmp.name)


def test_detect_source_type():
    # WeChat
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp.write('微信支付账单明细\n')
    for i in range(15):
        tmp.write(f'行{i}\n')
    tmp.write('交易时间,交易类型,交易对方\n')
    tmp.close()
    assert detect_source_type(tmp.name) == 'wechat'
    os.unlink(tmp.name)

    # Alipay
    tmp2 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp2.write('支付宝交易记录\n')
    tmp2.close()
    assert detect_source_type(tmp2.name) == 'alipay'
    os.unlink(tmp2.name)

    # Template
    tmp3 = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8')
    tmp3.write('日期,类型,金额,分类,描述\n')
    tmp3.close()
    assert detect_source_type(tmp3.name) == 'template'
    os.unlink(tmp3.name)

    print("✅ test_detect_source_type passed")


def test_map_category():
    categories = [
        {'id': 1, 'name': '餐饮'},
        {'id': 2, 'name': '交通'},
        {'id': 3, 'name': '工资'},
    ]

    assert map_category('餐饮', categories) == 1
    assert map_category('餐饮美食', categories) == 1
    assert map_category('交通出行', categories) == 2
    assert map_category('娱乐休闲', categories) is None
    assert map_category(None, categories) is None
    print("✅ test_map_category passed")


if __name__ == '__main__':
    test_sanitize_cell()
    test_parse_template_csv()
    test_parse_wechat_csv()
    test_parse_alipay_csv()
    test_parse_excel()
    test_detect_source_type()
    test_map_category()

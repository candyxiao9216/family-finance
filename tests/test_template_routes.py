"""测试快捷模板路由 (src/routes/template.py)"""
import pytest
from models import db, TransactionTemplate


class TestTemplateList:
    """GET /templates 列表页"""

    def test_list_page_returns_200(self, logged_in_client):
        """已登录用户访问快捷模板列表返回 200"""
        resp = logged_in_client.get('/templates/')
        assert resp.status_code == 200
        assert '快捷模板'.encode() in resp.data or b'template' in resp.data


class TestAddTemplate:
    """POST /templates/add 创建模板"""

    def test_create_template_success(self, logged_in_client, app):
        """成功创建快捷模板"""
        resp = logged_in_client.post('/templates/add', data={
            'name': '午餐',
            'amount': '30.00',
            'type': 'expense',
            'description': '工作日午餐'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '模板创建成功'.encode() in resp.data

        # 验证数据库
        with app.app_context():
            tpl = TransactionTemplate.query.filter_by(name='午餐').first()
            assert tpl is not None
            assert float(tpl.amount) == 30.00
            assert tpl.type == 'expense'

    def test_create_template_missing_fields(self, logged_in_client):
        """缺少必填字段返回错误"""
        resp = logged_in_client.post('/templates/add', data={
            'name': '午餐',
            # 缺少 amount 和 type
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '请填写所有必填字段'.encode() in resp.data


class TestDeleteTemplate:
    """POST /templates/<id>/delete 删除模板"""

    def test_delete_template_success(self, logged_in_client, app):
        """成功删除快捷模板"""
        # 先创建一个模板
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            tpl = TransactionTemplate(
                user_id=user.id,
                name='待删除',
                amount=10.00,
                type='expense'
            )
            db.session.add(tpl)
            db.session.commit()
            tpl_id = tpl.id

        resp = logged_in_client.post(f'/templates/{tpl_id}/delete', follow_redirects=True)
        assert resp.status_code == 200
        assert '模板已删除'.encode() in resp.data

        # 验证已删除
        with app.app_context():
            assert TransactionTemplate.query.get(tpl_id) is None

    def test_delete_nonexistent_template(self, logged_in_client):
        """删除不存在的模板返回 404"""
        resp = logged_in_client.post('/templates/99999/delete')
        assert resp.status_code == 404


class TestUseTemplate:
    """POST /templates/<id>/use 使用模板"""

    def test_use_template_increments_count(self, logged_in_client, app):
        """使用模板递增 use_count"""
        # 创建模板
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            tpl = TransactionTemplate(
                user_id=user.id,
                name='常用模板',
                amount=50.00,
                type='expense',
                use_count=0
            )
            db.session.add(tpl)
            db.session.commit()
            tpl_id = tpl.id

        # 使用一次
        resp = logged_in_client.post(f'/templates/{tpl_id}/use')
        assert resp.status_code == 204

        # 验证 use_count
        with app.app_context():
            tpl = TransactionTemplate.query.get(tpl_id)
            assert tpl.use_count == 1

        # 再使用一次
        resp = logged_in_client.post(f'/templates/{tpl_id}/use')
        assert resp.status_code == 204

        with app.app_context():
            tpl = TransactionTemplate.query.get(tpl_id)
            assert tpl.use_count == 2

    def test_use_nonexistent_template(self, logged_in_client):
        """使用不存在的模板返回 204（静默忽略）"""
        resp = logged_in_client.post('/templates/99999/use')
        assert resp.status_code == 204


class TestEditTemplate:
    """POST /templates/<id>/edit 编辑模板"""

    def test_edit_template_success(self, logged_in_client, app):
        """成功编辑快捷模板"""
        # 创建模板
        with app.app_context():
            from models import User
            user = User.query.filter_by(username='testuser').first()
            tpl = TransactionTemplate(
                user_id=user.id,
                name='原名称',
                amount=20.00,
                type='expense'
            )
            db.session.add(tpl)
            db.session.commit()
            tpl_id = tpl.id

        resp = logged_in_client.post(f'/templates/{tpl_id}/edit', data={
            'name': '新名称',
            'amount': '88.88',
            'type': 'income'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert '模板已更新'.encode() in resp.data

        with app.app_context():
            tpl = TransactionTemplate.query.get(tpl_id)
            assert tpl.name == '新名称'
            assert float(tpl.amount) == 88.88
            assert tpl.type == 'income'

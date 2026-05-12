"""分类管理路由测试"""
import pytest
from models import db, Category, User


class TestCategoryListPage:
    """分类管理页面"""

    def test_category_page_200(self, logged_in_client):
        """登录后访问分类管理页面返回 200"""
        resp = logged_in_client.get('/categories/')
        assert resp.status_code == 200
        assert '分类管理' in resp.data.decode('utf-8')

    def test_category_page_shows_defaults(self, logged_in_client):
        """分类页面展示系统预设分类"""
        resp = logged_in_client.get('/categories/')
        html = resp.data.decode('utf-8')
        # 系统预设分类应该显示（与 models.py DEFAULT_CATEGORIES 一致）
        assert '工资' in html
        assert '奖金' in html

    def test_category_page_unauth_redirect(self, client):
        """未登录访问分类页重定向到登录"""
        resp = client.get('/categories/')
        assert resp.status_code == 302
        assert '/auth/login' in resp.headers['Location']


class TestCategoryAdd:
    """添加分类"""

    def test_add_income_category_success(self, logged_in_client, app):
        """添加收入分类成功"""
        resp = logged_in_client.post('/categories/add', data={
            'name': '投资收益',
            'type': 'income'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '添加成功' in resp.data.decode('utf-8')

        with app.app_context():
            cat = Category.query.filter_by(name='投资收益').first()
            assert cat is not None
            assert cat.type == 'income'
            assert cat.is_default is False

    def test_add_expense_category_success(self, logged_in_client, app):
        """添加支出分类成功"""
        resp = logged_in_client.post('/categories/add', data={
            'name': '娱乐消费',
            'type': 'expense'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '添加成功' in resp.data.decode('utf-8')

        with app.app_context():
            cat = Category.query.filter_by(name='娱乐消费').first()
            assert cat is not None
            assert cat.type == 'expense'

    def test_add_duplicate_category_fails(self, logged_in_client):
        """添加重复分类失败"""
        # 第一次添加
        logged_in_client.post('/categories/add', data={
            'name': '自定义分类',
            'type': 'expense'
        })
        # 重复添加
        resp = logged_in_client.post('/categories/add', data={
            'name': '自定义分类',
            'type': 'expense'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '已存在' in resp.data.decode('utf-8')

    def test_add_same_name_different_type_ok(self, logged_in_client, app):
        """同名不同类型的分类可以共存"""
        logged_in_client.post('/categories/add', data={
            'name': '转账',
            'type': 'income'
        })
        resp = logged_in_client.post('/categories/add', data={
            'name': '转账',
            'type': 'expense'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '添加成功' in resp.data.decode('utf-8')

        with app.app_context():
            cats = Category.query.filter_by(name='转账').all()
            assert len(cats) == 2

    def test_add_category_missing_name(self, logged_in_client):
        """分类名称为空时失败"""
        resp = logged_in_client.post('/categories/add', data={
            'name': '',
            'type': 'expense'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '请输入分类名称' in resp.data.decode('utf-8')

    def test_add_category_invalid_type(self, logged_in_client):
        """分类类型无效时失败"""
        resp = logged_in_client.post('/categories/add', data={
            'name': '测试',
            'type': 'invalid'
        }, follow_redirects=True)

        assert resp.status_code == 200
        assert '请输入分类名称' in resp.data.decode('utf-8')


class TestCategoryDelete:
    """删除分类"""

    def test_delete_user_category_success(self, logged_in_client, app):
        """删除用户自定义分类成功"""
        # 先创建
        logged_in_client.post('/categories/add', data={
            'name': '待删除分类',
            'type': 'expense'
        })

        with app.app_context():
            cat = Category.query.filter_by(name='待删除分类').first()
            cat_id = cat.id

        resp = logged_in_client.post(f'/categories/delete/{cat_id}', follow_redirects=True)

        assert resp.status_code == 200
        assert '已删除' in resp.data.decode('utf-8')

        with app.app_context():
            deleted = Category.query.get(cat_id)
            assert deleted is None

    def test_delete_system_category_allowed(self, logged_in_client, app):
        """系统预设分类可以被删除（user_id=None 时允许所有人删除）"""
        with app.app_context():
            # 系统分类的 user_id 为 None
            system_cat = Category.query.filter_by(is_default=True).first()
            cat_id = system_cat.id
            cat_name = system_cat.name

        resp = logged_in_client.post(f'/categories/delete/{cat_id}', follow_redirects=True)

        assert resp.status_code == 200
        assert '已删除' in resp.data.decode('utf-8')

        with app.app_context():
            deleted = Category.query.get(cat_id)
            assert deleted is None

    def test_delete_others_category_forbidden(self, app):
        """不能删除其他用户的自定义分类"""
        with app.app_context():
            # 创建用户 A 和用户 B
            user_a = User(username='cat_owner', nickname='分类所有者')
            user_a.set_password('Test1234')
            user_b = User(username='cat_visitor', nickname='访客')
            user_b.set_password('Test1234')
            db.session.add_all([user_a, user_b])
            db.session.commit()

            # 用户 A 创建分类
            cat = Category(name='A的分类', type='expense', is_default=False, user_id=user_a.id)
            db.session.add(cat)
            db.session.commit()
            cat_id = cat.id
            visitor_id = user_b.id

        # 用户 B 尝试删除
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = visitor_id

        resp = client.post(f'/categories/delete/{cat_id}', follow_redirects=True)
        html = resp.data.decode('utf-8')
        assert '无权删除' in html

        # 确认分类还在
        with app.app_context():
            cat = Category.query.get(cat_id)
            assert cat is not None

    def test_delete_nonexistent_category_404(self, logged_in_client):
        """删除不存在的分类返回 404"""
        resp = logged_in_client.post('/categories/delete/99999')
        assert resp.status_code == 404

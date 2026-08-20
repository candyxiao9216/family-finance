"""测试基础设施：before_request 全局登录闸在测试 app 中必须生效（P1-8）

背景：conftest 的 create_test_app 此前未注册 main.require_login，
导致专门为守护认证边界写的回归测试（test_before_request_whitelist.py）
守护的是「函数内部自检」而非全局闸——把 require_login 整个删掉测试也全绿，
认证边界零覆盖。

本测试直接验证不变量：未登录访问任意受保护蓝图路由必须被全局 before_request
拦截跳登录。选用一个「函数内部没有自检 session」的端点作为探针，确保拦截
确实来自 before_request 而非函数体。
"""
import pytest

import sys
sys.path.insert(0, "src")


class TestBeforeRequestEnforced:
    def test_unauthenticated_blocked_by_global_gate(self, app):
        """未登录访问受保护路由必须 302 跳登录（来自全局 before_request）"""
        client = app.test_client()
        # /accounts/ 路由内部会 User.query.get(None)，未登录时若全局闸生效应在
        # 进入函数体前就被 302 拦下；若全局闸缺失则进入函数体后行为不可预期。
        r = client.get("/accounts/", follow_redirects=False)
        assert r.status_code == 302, f"未登录应被全局闸拦为 302，实际 {r.status_code}"
        assert "/auth/login" in (r.headers.get("Location") or ""), "应跳转到登录页"

    def test_unauthenticated_blocked_on_multiple_blueprints(self, app):
        """多个 blueprint 的受保护路由均被全局闸拦（非单点巧合）"""
        client = app.test_client()
        for path in ["/savings/", "/recurring/", "/baby-fund/", "/reports/"]:
            r = client.get(path, follow_redirects=False)
            assert r.status_code == 302, (
                f"未登录访问 {path} 应被全局闸拦为 302，实际 {r.status_code}"
            )

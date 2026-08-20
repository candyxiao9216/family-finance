"""308 重定向与 session 持久化回归测试

背景：
- accounts.html / reports.html 的「我的/家庭」按钮写的是
  /accounts?view=xxx、/reports?view=xxx（无尾斜杠）。
- 对应路由是 @bp.route('/') 即 /accounts/、/reports/（带尾斜杠）。
- Flask strict_slashes 对无尾斜杠访问返回 308 Permanent Redirect，
  被浏览器永久缓存，叠加 session 失效后表现为「点家庭就跳登录」。
- auth.py 注册路径自动登录时未设 session.permanent，注册用户
  拿到的是非持久 session，寿命短、易丢。

详见 access.log 复现：2026-08-20 09:55:56 GET /accounts?view=family -> 308。
"""


def _register(client, username="repro_user"):
    return client.post(
        "/auth/register",
        data={"username": username, "password": "pass1234", "nickname": "Repro"},
        follow_redirects=False,
    )


class TestNo308OnViewSwitchLinks:
    """带尾斜杠的 view 切换链接不应返回 308"""

    def test_accounts_personal_link_no_308(self, app):
        client = app.test_client()
        _register(client)
        r = client.get("/accounts/?view=personal", follow_redirects=False)
        assert r.status_code != 308

    def test_accounts_family_link_no_308(self, app):
        client = app.test_client()
        _register(client)
        r = client.get("/accounts/?view=family", follow_redirects=False)
        assert r.status_code != 308

    def test_reports_family_link_no_308(self, app):
        client = app.test_client()
        _register(client)
        r = client.get("/reports/?view=family", follow_redirects=False)
        assert r.status_code != 308


class TestTemplateLinksUseTrailingSlash:
    """模板里的 view-btn 必须用带尾斜杠路径，避免 308 永久重定向被浏览器缓存"""

    def test_accounts_html_uses_trailing_slash(self):
        from pathlib import Path

        content = Path("src/templates/accounts.html").read_text(encoding="utf-8")
        assert "/accounts?view=" not in content, (
            "accounts.html 仍有无尾斜杠的 /accounts?view= 链接，"
            "会触发 Flask 308 永久重定向被浏览器缓存。应改为 /accounts/?view="
        )

    def test_reports_html_uses_trailing_slash(self):
        from pathlib import Path

        content = Path("src/templates/reports.html").read_text(encoding="utf-8")
        assert "/reports?view=" not in content, (
            "reports.html 仍有无尾斜杠的 /reports?view= 链接。应改为 /reports/?view="
        )


class TestRegisterSessionPersistent:
    """注册后自动登录的 session 必须是 persistent，与 login 路径一致"""

    def test_register_auto_login_works(self, app):
        """注册成功后应自动登录，访问受保护页面不跳登录"""
        client = app.test_client()
        r = _register(client)
        assert r.status_code == 302, f"注册应返回 302 跳首页，实际 {r.status_code}"
        # 注册后访问受保护页面，不应跳登录
        r2 = client.get("/accounts/", follow_redirects=False)
        assert not (
            r2.status_code == 302
            and "/auth/login" in (r2.headers.get("Location") or "")
        ), "注册后访问受保护页面不应跳登录"

    def test_register_sets_session_permanent_flag(self):
        """注册路径代码必须含 session.permanent = True（代码守护，防回归）"""
        from pathlib import Path

        auth_src = Path("src/routes/auth.py").read_text(encoding="utf-8")
        register_section = auth_src.split("def register(")[1]
        auto_login_idx = register_section.find("自动登录")
        assert auto_login_idx != -1, "找不到注册的自动登录段"
        section = register_section[auto_login_idx : auto_login_idx + 400]
        assert "session.permanent" in section, (
            "注册自动登录段缺少 session.permanent = True，"
            "注册用户 session 非 persistent，寿命短易丢。"
        )

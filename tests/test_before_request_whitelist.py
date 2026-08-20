"""before_request 白名单回归测试

背景：family.family_info 和 family.family_members 曾在 before_request
白名单里（跳过全局登录闸），靠函数内部自检 session 兜底。虽然当时
不构成泄露，但白名单冗余会在未来被误改时埋下隐患——若有人删掉函数
内部的 session 检查，白名单仍放行，就真泄露家庭信息了。

本测试守护不变量：未登录访问这两个接口，必须被全局 before_request
拦截并跳转登录页，而非进入函数体。
"""


def test_family_info_requires_login(app):
    """未登录访问 /family/info 必须跳登录，不能渲染页面"""
    client = app.test_client()
    r = client.get("/family/info", follow_redirects=False)
    assert r.status_code == 302, f"应 302 跳登录，实际 {r.status_code}"
    assert "/auth/login" in (r.headers.get("Location") or ""), (
        "未登录访问 /family/info 应跳转到 /auth/login"
    )


def test_family_members_requires_login(app):
    """未登录访问 /family/members 必须跳登录，不能渲染页面"""
    client = app.test_client()
    r = client.get("/family/members", follow_redirects=False)
    assert r.status_code == 302, f"应 302 跳登录，实际 {r.status_code}"
    assert "/auth/login" in (r.headers.get("Location") or ""), (
        "未登录访问 /family/members 应跳转到 /auth/login"
    )


def test_whitelist_no_longer_contains_family_routes():
    """白名单不得再含 family.family_info / family.family_members（防回归）"""
    from pathlib import Path

    content = Path("src/main.py").read_text(encoding="utf-8")
    # 找 before_request 里的 allowed_routes 定义
    idx = content.find("allowed_routes")
    assert idx != -1, "找不到 allowed_routes 定义"
    section = content[idx : idx + 300]
    assert "family.family_info" not in section, (
        "before_request 白名单仍含 family.family_info，应删除"
    )
    assert "family.family_members" not in section, (
        "before_request 白名单仍含 family.family_members，应删除"
    )

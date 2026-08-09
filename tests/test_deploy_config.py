"""部署脚本配置校验测试

背景：deploy.sh 原先生成的 nginx 配置使用 `listen 80` + `server_name _`，
在与其他项目共用 nginx 的服务器上会抢占默认站点，导致：
  1. 裸 IP 访问被本项目截获（或反之，本项目被其他站点截获）
  2. 其他项目的路由被打乱

本测试守护这条不变量，防止未来有人图省事改回去。
不测试"脚本里有某个字符串"这种同义反复，只测真实踩过的坑。
"""
import re
from pathlib import Path

import pytest

DEPLOY_SH = Path(__file__).resolve().parent.parent / "scripts" / "deploy.sh"
PUSH_DEPLOY_SH = Path(__file__).resolve().parent.parent / "scripts" / "push-deploy.sh"


def _extract_nginx_config(script_text):
    """从 deploy.sh 中抽出 NGINX_EOF heredoc 包裹的 nginx 配置文本"""
    match = re.search(
        r"<<\s*[\"']?NGINX_EOF[\"']?\s*\n(.*?)\nNGINX_EOF",
        script_text,
        re.DOTALL,
    )
    assert match, "未能在 deploy.sh 中找到 NGINX_EOF 配置段"
    return match.group(1)


def _split_server_blocks(nginx_config):
    """按 `server {` 切分出各个 server 块的内容"""
    blocks = []
    for chunk in nginx_config.split("server {")[1:]:
        # 取到该块闭合处为止（配置为固定缩进风格，行首 } 即为块结束）
        end = chunk.find("\n}")
        blocks.append(chunk[: end if end != -1 else len(chunk)])
    return blocks


@pytest.fixture(scope="module")
def server_blocks():
    return _split_server_blocks(_extract_nginx_config(DEPLOY_SH.read_text()))


def test_nginx_has_server_blocks(server_blocks):
    """基本健全性：至少要有 IP 入口和域名入口两个块"""
    assert len(server_blocks) >= 2, f"期望至少 2 个 server 块，实际 {len(server_blocks)}"


def test_port_80_block_never_uses_wildcard_server_name(server_blocks):
    """回归：监听 80 的块不得使用 `server_name _`（会抢占同机其他站点的默认站点）"""
    for block in server_blocks:
        listens_80 = re.search(r"^\s*listen\s+80\s*;", block, re.MULTILINE)
        if not listens_80:
            continue
        wildcard = re.search(r"^\s*server_name\s+_\s*;", block, re.MULTILINE)
        assert not wildcard, (
            "deploy.sh 的 nginx 配置中出现 `listen 80` + `server_name _` 组合。\n"
            "这会抢占默认站点、打乱同机其他项目的路由。\n"
            "80 端口的块必须绑定具体域名，IP 直连请使用 8080 端口。"
        )


def test_ip_entry_uses_port_8080(server_blocks):
    """IP 直连入口应监听 8080，且允许使用通配 server_name"""
    ip_blocks = [
        b for b in server_blocks if re.search(r"^\s*listen\s+8080\s*;", b, re.MULTILINE)
    ]
    assert ip_blocks, "未找到监听 8080 的 IP 直连入口块"
    assert any(
        re.search(r"^\s*server_name\s+_\s*;", b, re.MULTILINE) for b in ip_blocks
    ), "8080 块应使用 `server_name _` 以便任意 Host（含裸 IP）都能访问"


def test_all_blocks_proxy_to_gunicorn(server_blocks):
    """每个 server 块都必须反代到本项目的 gunicorn 端口，避免配置漏写"""
    for i, block in enumerate(server_blocks):
        assert "proxy_pass http://127.0.0.1:5001" in block, (
            f"第 {i + 1} 个 server 块缺少指向 127.0.0.1:5001 的 proxy_pass"
        )


def test_static_files_are_not_cached(server_blocks):
    """回归 CLAUDE.md 经验教训 #2：静态文件不得设长缓存，否则 CSS 改了不生效"""
    for i, block in enumerate(server_blocks):
        if "location /static" not in block:
            continue
        assert not re.search(r"expires\s+\d+[dhm]", block), (
            f"第 {i + 1} 个 server 块的 /static 设置了长缓存 expires。\n"
            "见 CLAUDE.md 经验教训 #2：开发阶段静态文件不缓存，应使用 `expires off`。"
        )


def test_deploy_does_not_remove_default_site():
    """回归：不得删除 sites-enabled/default，那会影响同机其他站点的兜底行为"""
    text = DEPLOY_SH.read_text()
    assert not re.search(r"rm\s+-f\s+/etc/nginx/sites-enabled/default", text), (
        "deploy.sh 不应删除 /etc/nginx/sites-enabled/default（会影响其他项目）"
    )


def test_deploy_reloads_nginx_instead_of_restart():
    """nginx 用 reload 热加载，restart 会中断同机其他站点的连接"""
    text = DEPLOY_SH.read_text()
    assert "systemctl reload nginx" in text, "deploy.sh 应使用 systemctl reload nginx"
    assert "systemctl restart nginx" not in text, (
        "deploy.sh 不应 restart nginx（会中断其他站点连接），请用 reload"
    )


def test_deploy_creates_env_before_database_init():
    """回归：create_app() 缺 SECRET_KEY 会拒绝启动，.env 必须在初始化数据库前生成"""
    text = DEPLOY_SH.read_text()
    env_pos = text.find("SECRET_KEY=$(openssl rand")
    assert env_pos != -1, "deploy.sh 未生成随机 SECRET_KEY（.env 不在 git 中，clone 后缺失会导致启动失败）"
    init_pos = text.find("init_database(app)")
    assert init_pos != -1, "未找到 init_database 调用"
    assert env_pos < init_pos, ".env 生成必须在 init_database 之前，否则应用拒绝启动"


def test_deploy_does_not_overwrite_existing_env():
    """幂等：.env 已存在时不得覆盖，否则重跑会换掉 SECRET_KEY 导致所有人掉线"""
    text = DEPLOY_SH.read_text()
    assert re.search(r"if\s+\[\s+!\s+-f\s+\S*\.env\s+\]", text), (
        "deploy.sh 生成 .env 前应检查文件是否已存在，避免覆盖既有 SECRET_KEY"
    )


def test_push_deploy_health_check_targets_own_service():
    """回归：部署验证必须打 :8080，裸 IP 的 80 端口是其他项目，会产生假绿灯"""
    text = PUSH_DEPLOY_SH.read_text()
    assert 'SERVER_IP}:8080' in text, (
        "push-deploy.sh 的健康检查应指向 http://${SERVER_IP}:8080。\n"
        "裸 IP 会打到同机其他项目，导致本项目挂了也报「部署成功」。"
    )
    assert not re.search(r'curl[^\n]*"http://\$\{SERVER_IP\}"', text), (
        "push-deploy.sh 仍在用裸 IP 做健康检查（假绿灯）"
    )

"""统一权限边界 helper

背景：IDOR 体检发现 savings/template/recurring/baby_fund/advisor 共 18 个写路由
完全不校验资源归属，任意登录用户可遍历 id 删改他人数据。同时「本人 OR 同家庭」
的判定逻辑此前散落在 main.py / account.py 各处手写，加上 _get_family_member_ids
的 3 个变体重复实现，导致修一处漏四处。

本模块提供单一入口 assert_owner_or_family，统一所有资源写路径的归属校验。

判定语义（与现有 main.py:311 edit_transaction / account.py:210 add_snapshot 一致）：
资源属于本人 → 放行；资源属于同一家庭成员 → 放行；否则越权。
"""
from models import db, User


def get_family_member_ids(user, include_self=True):
    """返回 user 的家庭成员 id 集合。

    用于「家庭视图下可见哪些用户的数据」的查询过滤，替代各 blueprint
    里重复实现的 _get_family_member_ids。user 为 None 或无家庭时返回仅含本人
    （或空）。
    """
    if not user:
        return []
    if user.family:
        ids = [m.id for m in user.family.members]
        if not include_self and user.id in ids:
            ids = [i for i in ids if i != user.id]
        return ids
    return [user.id] if include_self else []


def is_owner_or_family(resource, user, user_id, field='user_id'):
    """资源是否属于本人或同一家庭成员。

    Args:
        resource: 带 user_id（或指定 field）的 ORM 对象
        user: 当前登录用户（User 实例）
        user_id: 当前登录用户 id（用于「本人」快路径，避免再查库）
        field: 资源归属字段名，默认 'user_id'；savings/baby_fund 用 'created_by'

    Returns:
        True 表示放行（本人或同家庭），False 表示越权。
    """
    owner_id = getattr(resource, field, None)
    if owner_id is None:
        return False
    if owner_id == user_id:
        return True
    if not user or not user.family_id:
        return False
    owner = User.query.get(owner_id)
    return bool(owner and owner.family_id == user.family_id)

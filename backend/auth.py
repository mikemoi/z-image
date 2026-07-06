"""单用户鉴权:请求头带 token,和环境变量里的比对。"""
import secrets

from fastapi import Header, HTTPException, status
from config import AUTH_TOKEN


async def require_token(authorization: str | None = Header(default=None)):
    """
    校验 Authorization 头。接受两种写法:
      Authorization: Bearer <token>
      Authorization: <token>
    不带或不匹配 → 401。
    """
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, AUTH_TOKEN):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

    return True

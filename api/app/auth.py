"""Cognito JWT check. Fails closed: with no pool configured, every request is refused."""

from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url)


def decode_token(token: str, s: Settings, signing_key: Any = None) -> dict[str, Any]:
    issuer = f"https://cognito-idp.{s.cognito_region}.amazonaws.com/{s.cognito_user_pool_id}"
    key = (
        signing_key
        or _jwks_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token).key
    )
    claims: dict[str, Any] = jwt.decode(
        token, key, algorithms=["RS256"], issuer=issuer, options={"verify_aud": False}
    )
    if claims.get("token_use") != "access" or claims.get("client_id") != s.cognito_client_id:
        raise jwt.InvalidTokenError("wrong token type or client")
    return claims


def require_user(request: Request, s: Annotated[Settings, Depends(get_settings)]) -> str:
    """Any signed-in teacher (or admin). Returns the username."""
    if s.auth_mode == "dev":
        return "dev-user"
    if not s.cognito_user_pool_id or not s.cognito_client_id:
        raise HTTPException(503, "auth not configured")
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    try:
        claims = decode_token(header[7:], s)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid token") from exc
    return str(claims.get("username", claims["sub"]))


def require_admin(request: Request, s: Annotated[Settings, Depends(get_settings)]) -> str:
    """Returns the reviewer's username. Only members of the admin group get through."""
    if s.auth_mode == "dev":
        return "dev-admin"
    if not s.cognito_user_pool_id or not s.cognito_client_id:
        raise HTTPException(503, "auth not configured")
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    try:
        claims = decode_token(header[7:], s)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid token") from exc
    if s.admin_group not in claims.get("cognito:groups", []):
        raise HTTPException(403, "admin group required")
    return str(claims.get("username", claims["sub"]))

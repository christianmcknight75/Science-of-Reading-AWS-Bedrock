"""Token verification, written so Phase 5 only swaps the issuer, client id and JWKS URL.

Tokens are verified the way Cognito access tokens are: RS256 only, signature from the issuer's
JWKS (by `kid`), `iss` must match, `client_id` must be our app client (an `aud`, if present, too),
`token_use` must be "access", `exp` is required. In `local` mode the issuer is a dev signer
(`LocalIssuer`) whose JWKS we read directly instead of over HTTP; every other check is identical.

Modes (settings.auth_mode):
  cognito  default; fails closed (503) until a pool and client are configured
  local    local dev issuer + the real users table (development and tests)
  dev      no authentication at all: everyone is an admin (local development only)
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import jwt
import psycopg
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, HTTPException, Request
from psycopg.rows import dict_row

from .config import Settings, get_settings

DEV_ISSUER = "http://localhost:8000/dev-issuer"
DEV_CLIENT_ID = "reading-helper-local"


def issuer(s: Settings) -> str:
    if s.auth_issuer:
        return s.auth_issuer
    if s.auth_mode == "local":
        return DEV_ISSUER
    return f"https://cognito-idp.{s.cognito_region}.amazonaws.com/{s.cognito_user_pool_id}"


def client_id(s: Settings) -> str:
    return s.cognito_client_id or (DEV_CLIENT_ID if s.auth_mode == "local" else "")


def jwks_url(s: Settings) -> str:
    return s.auth_jwks_url or issuer(s) + "/.well-known/jwks.json"


# ------------------------------------------------------------------ local dev issuer
class LocalIssuer:
    """Signs tokens for local development. Never used with auth_mode cognito."""

    def __init__(self, key_path: Path) -> None:
        if key_path.exists():
            loaded = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
            if not isinstance(loaded, rsa.RSAPrivateKey):
                raise ValueError("dev issuer key must be an RSA key")
            self._key = loaded
        else:
            self._key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            key_path.parent.mkdir(parents=True, exist_ok=True)
            pem = self._key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(pem)
        public = self._key.public_key()
        der = public.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.kid = hashlib.sha256(der).hexdigest()[:16]
        self._public = public

    def sign(self, claims: dict[str, Any]) -> str:
        return jwt.encode(claims, self._key, algorithm="RS256", headers={"kid": self.kid})

    def jwks(self) -> dict[str, Any]:
        jwk = jwt.algorithms.RSAAlgorithm.to_jwk(self._public, as_dict=True)
        return {"keys": [{**jwk, "kid": self.kid, "use": "sig", "alg": "RS256"}]}

    def key_for(self, kid: str | None) -> Any:
        if kid != self.kid:
            raise jwt.InvalidTokenError("unknown key id")
        return self._public


@lru_cache
def _local_issuer(path: str) -> LocalIssuer:
    return LocalIssuer(Path(path))


def local_issuer(s: Settings) -> LocalIssuer:
    return _local_issuer(s.dev_issuer_key_path)


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url)


def _signing_key(token: str, s: Settings) -> Any:
    if s.auth_mode == "local":
        return local_issuer(s).key_for(jwt.get_unverified_header(token).get("kid"))
    return _jwks_client(jwks_url(s)).get_signing_key_from_jwt(token).key


def decode_token(token: str, s: Settings, signing_key: Any = None) -> dict[str, Any]:
    cid = client_id(s)
    claims: dict[str, Any] = jwt.decode(
        token,
        signing_key or _signing_key(token, s),
        algorithms=["RS256"],
        issuer=issuer(s),
        options={"verify_aud": False, "require": ["exp", "iss", "sub"]},
    )
    aud = claims.get("aud")
    aud_ok = aud is None or aud == cid or (isinstance(aud, list) and cid in aud)
    if (
        not cid
        or claims.get("token_use") != "access"
        or claims.get("client_id") != cid
        or not aud_ok
    ):
        raise jwt.InvalidTokenError("wrong token type or client")
    return claims


# ------------------------------------------------------------------ database access for auth
class LazyDb:
    """Connects only when asked, so dev mode and the no-database tests never open a connection."""

    def __init__(self, url: str, conn: Any = None) -> None:
        self._url = url
        self._conn = conn
        self._own = conn is None

    def conn(self) -> psycopg.Connection[dict[str, Any]]:
        if self._conn is None:
            self._conn = psycopg.connect(self._url, row_factory=dict_row)
        return self._conn  # type: ignore[no-any-return]

    def close(self) -> None:
        if self._own and self._conn is not None:
            self._conn.close()


def auth_db(s: Annotated[Settings, Depends(get_settings)]) -> Iterator[LazyDb]:
    db = LazyDb(s.database_url)
    try:
        yield db
    finally:
        db.close()


Db = Annotated[LazyDb, Depends(auth_db)]


def _bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(401, "Please sign in.")
    return header[7:]


def _verify(request: Request, s: Settings) -> dict[str, Any]:
    if not client_id(s) or (s.auth_mode == "cognito" and not s.cognito_user_pool_id):
        raise HTTPException(503, "Sign-in is not set up yet.")
    token = _bearer(request)
    try:
        return decode_token(token, s)
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "Please sign in again.") from exc


def _check_active(claims: dict[str, Any], db: LazyDb, *, admin: bool = False) -> dict[str, Any]:
    """The token is genuine; is the person still allowed in, and not signed out?"""
    conn = db.conn()
    jti = claims.get("jti")
    if jti and conn.execute("SELECT 1 FROM revoked_tokens WHERE jti = %s", (jti,)).fetchone():
        raise HTTPException(401, "You have signed out. Please sign in again.")
    sub = str(claims["sub"])
    row = conn.execute(
        """SELECT user_id::text AS user_id, name, email, district, role, status FROM users
           WHERE user_id::text = %s OR cognito_sub = %s""",
        (sub, sub),
    ).fetchone()
    if not row or row["status"] != "active":
        raise HTTPException(403, "Your access is not active. Please contact your district lead.")
    if admin and row["role"] != "admin":
        raise HTTPException(403, "Administrator access is needed for this.")
    return dict(row)


def current_user(
    request: Request, s: Annotated[Settings, Depends(get_settings)], db: Db
) -> dict[str, Any]:
    """The signed-in person (a dict with user_id, name, email, district, role, status)."""
    if s.auth_mode == "dev":
        return {
            "user_id": "dev",
            "name": "Dev User",
            "email": "dev@localhost",
            "district": "local",
            "role": "admin",
            "status": "active",
            "jti": None,
            "exp": None,
        }
    claims = _verify(request, s)
    user = _check_active(claims, db)
    return {**user, "jti": claims.get("jti"), "exp": claims.get("exp")}


def require_user(request: Request, s: Annotated[Settings, Depends(get_settings)], db: Db) -> str:
    """Any signed-in teacher or admin. Returns the username (their school email)."""
    if s.auth_mode == "dev":
        return "dev-user"
    claims = _verify(request, s)
    _check_active(claims, db)
    return str(claims.get("username", claims["sub"]))


def require_admin(request: Request, s: Annotated[Settings, Depends(get_settings)], db: Db) -> str:
    """Returns the reviewer's username. Only members of the admin group get through."""
    if s.auth_mode == "dev":
        return "dev-admin"
    claims = _verify(request, s)
    if s.admin_group not in claims.get("cognito:groups", []):
        raise HTTPException(403, "admin group required")
    _check_active(claims, db, admin=True)
    return str(claims.get("username", claims["sub"]))

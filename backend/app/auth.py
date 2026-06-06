"""Basic bearer-token authentication for the local MVP."""
from __future__ import annotations

import base64
import hmac
import hashlib
import json
import os
import secrets
import time
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


TOKEN_TTL_SECONDS = 60 * 60 * 8
security = HTTPBearer(auto_error=False)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _secret() -> str:
    return os.getenv("AUTH_TOKEN_SECRET", "local-dev-auth-secret")


def _username() -> str:
    return os.getenv("AUTH_USERNAME", "admin")


def _password() -> str:
    return os.getenv("AUTH_PASSWORD", "admin123")


def _role() -> str:
    return os.getenv("AUTH_ROLE", "admin")


def authenticate_user(username: str, password: str) -> dict[str, str] | None:
    """Validate the configured local account."""
    if secrets.compare_digest(username, _username()) and secrets.compare_digest(password, _password()):
        return {"username": username, "role": _role()}
    return None


def create_access_token(user: dict[str, str]) -> tuple[str, int]:
    expires_at = int(time.time()) + TOKEN_TTL_SECONDS
    payload = {
        "sub": user["username"],
        "role": user.get("role", "user"),
        "exp": expires_at,
    }
    payload_part = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_secret().encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64encode(signature)}", TOKEN_TTL_SECONDS


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload_part, signature_part = token.split(".", 1)
        expected = hmac.new(_secret().encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
        supplied = _b64decode(signature_part)
        if not hmac.compare_digest(expected, supplied):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(payload_part).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    token = request.cookies.get("auth_token")
    if credentials is not None and credentials.scheme.lower() == "bearer":
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(token)

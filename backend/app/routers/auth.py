"""Login and current-user routes."""
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.auth import TOKEN_TTL_SECONDS, authenticate_user, create_access_token, get_current_user


router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict[str, str]


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, response: Response):
    user = authenticate_user(data.username, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token, expires_in = create_access_token(user)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=TOKEN_TTL_SECONDS,
        samesite="lax",
    )
    return {
        "access_token": token,
        "expires_in": expires_in,
        "user": user,
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("auth_token")
    return {"ok": True}

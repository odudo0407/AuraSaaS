"""Authentication API for local demo accounts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, decode_access_token_lenient, hash_password, verify_password
from app.database import get_db
from app.models.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="This email is already registered.")

    user = User(
        username=body.username,
        email=email,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {
        "code": 0,
        "data": TokenResponse(
            access_token=token,
            username=user.username,
            email=user.email,
        ).model_dump(),
        "message": "Account created.",
    }


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password.")

    token = create_access_token({"sub": str(user.id)})
    return {
        "code": 0,
        "data": TokenResponse(
            access_token=token,
            username=user.username,
            email=user.email,
        ).model_dump(),
        "message": "Signed in.",
    }


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    return {"code": 0, "data": None, "message": "Signed out."}


@router.post("/refresh")
def refresh_token(authorization: str | None = None, db: Session = Depends(get_db)):
    """Issue a new token using an existing (even expired) token."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(status_code=400, detail="Token required")

    payload = decode_access_token_lenient(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_token = create_access_token({"sub": str(user.id)})
    return {
        "code": 0,
        "data": TokenResponse(
            access_token=new_token,
            username=user.username,
            email=user.email,
        ).model_dump(),
        "message": "Token refreshed.",
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {
        "code": 0,
        "data": UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url or "",
        ).model_dump(),
        "message": "ok",
    }


@router.delete("/account")
def delete_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(user)
    db.commit()
    return {"code": 0, "data": None, "message": "Account deleted."}

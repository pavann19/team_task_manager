"""Authentication routes: register, login, me, users list."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.db.session import get_db
from app.db.models import User
from app.schemas.user import UserRegister, UserLogin, UserOut, TokenOut
from app.schemas.common import APIResponse
from app.api.deps import get_current_user
from app.core.rate_limit import limiter

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user."""
    # Normalize email
    normalized_email = payload.email.strip().lower()

    # Check duplicates
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    if db.query(User).filter(User.email == normalized_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        username=payload.username,
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: %s (role=%s)", user.username, user.role.value)

    token = create_access_token(subject=user.id)
    user_out = UserOut.model_validate(user)
    return APIResponse(
        success=True,
        message="User registered successfully",
        data=TokenOut(access_token=token, user=user_out).model_dump(),
    )


@router.post("/login", response_model=APIResponse)
@limiter.limit("5/minute")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Authenticate and return a JWT token."""
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    logger.info("User logged in: %s", user.username)

    token = create_access_token(subject=user.id)
    user_out = UserOut.model_validate(user)
    return APIResponse(
        success=True,
        message="Login successful",
        data=TokenOut(access_token=token, user=user_out).model_dump(),
    )


@router.get("/me", response_model=APIResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    user_out = UserOut.model_validate(current_user)
    return APIResponse(
        success=True,
        message="Current user retrieved",
        data=user_out.model_dump(),
    )


@router.get("/users", response_model=APIResponse)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all users (for task assignment dropdown)."""
    users = db.query(User).all()
    return APIResponse(
        success=True,
        message="Users retrieved",
        data=[UserOut.model_validate(u).model_dump() for u in users],
    )

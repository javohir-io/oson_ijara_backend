from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..deps import absolute_url, get_current_user

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_user_out(user: models.User, request: Request) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        avatar_url=absolute_url(request, user.avatar_path),
        created_at=user.created_at,
    )


@router.post("/register", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu elektron pochta allaqachon ro'yxatdan o'tgan")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=security.get_password_hash(payload.password),
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = security.create_access_token(subject=user.email)
    return schemas.Token(access_token=token, user=_to_user_out(user, request))


@router.post("/login", response_model=schemas.Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # OAuth2PasswordRequestForm sends the identifier as "username" — we treat
    # it as the user's email address.
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email yoki parol noto'g'ri")

    token = security.create_access_token(subject=user.email)
    return schemas.Token(access_token=token, user=_to_user_out(user, request))


@router.get("/me", response_model=schemas.UserOut)
def me(request: Request, current_user: models.User = Depends(get_current_user)):
    return _to_user_out(current_user, request)

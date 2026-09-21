from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tizimga kirish talab qilinadi",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    email = decode_token(token)
    if email is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User | None:
    if token is None:
        return None
    email = decode_token(token)
    if email is None:
        return None
    return db.query(models.User).filter(models.User.email == email).first()


def absolute_url(request: Request, relative_path: str | None) -> str | None:
    """Turn a stored relative upload path (e.g. 'avatars/1_pic.jpg') into a
    full URL the Flutter app can load directly, e.g.
    'http://localhost:8000/uploads/avatars/1_pic.jpg'."""
    if not relative_path:
        return None
    base = str(request.base_url).rstrip("/")
    return f"{base}/uploads/{relative_path}"

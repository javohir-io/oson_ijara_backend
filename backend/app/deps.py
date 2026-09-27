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


def get_current_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin huquqi talab qilinadi")
    return current_user


def get_user_from_token(token: str | None, db: Session) -> models.User | None:
    """Same lookup as get_current_user, but callable directly with a raw
    token string — used by the WebSocket endpoint, which authenticates via
    a '?token=' query param instead of an Authorization header (browsers'
    WebSocket API can't set custom headers)."""
    if not token:
        return None
    email = decode_token(token)
    if email is None:
        return None
    return db.query(models.User).filter(models.User.email == email).first()


def absolute_url(request: Request, relative_path: str | None) -> str | None:
    """Turn a stored upload reference into a full URL the Flutter app can
    load directly. Handles both local disk storage (a path relative to
    UPLOAD_DIR, e.g. 'avatars/1_pic.jpg' -> served from this app's own
    /uploads mount) and Cloudflare R2 storage (already a full URL, returned
    as-is)."""
    if not relative_path:
        return None
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return relative_path
    base = str(request.base_url).rstrip("/")
    return f"{base}/uploads/{relative_path}"

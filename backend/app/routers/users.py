from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from ..deps import absolute_url, get_current_user
from ..utils.files import delete_upload, save_upload
from .properties import _to_property_out  # reuse the same serializer

router = APIRouter(prefix="/users", tags=["Users"])


def _to_user_out(user: models.User, request: Request) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        avatar_url=absolute_url(request, user.avatar_path),
        created_at=user.created_at,
    )


@router.put("/me", response_model=schemas.UserOut)
def update_me(
    payload: schemas.UserUpdate,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.email is not None:
        current_user.email = payload.email
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.password:
        current_user.hashed_password = security.get_password_hash(payload.password)

    db.commit()
    db.refresh(current_user)
    return _to_user_out(current_user, request)


@router.post("/me/avatar", response_model=schemas.UserOut)
def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_upload(current_user.avatar_path)
    current_user.avatar_path = save_upload(file, "avatars")
    db.commit()
    db.refresh(current_user)
    return _to_user_out(current_user, request)


@router.get("/me/saved", response_model=list[schemas.PropertyOut])
def my_saved_properties(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    properties = [link.property for link in current_user.saved]
    return [_to_property_out(p, request, current_user) for p in properties]

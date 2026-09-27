from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import absolute_url, get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/stats", response_model=schemas.AdminStatsOut)
def stats(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin),
):
    return schemas.AdminStatsOut(
        total_users=db.query(models.User).count(),
        total_properties=db.query(models.Property).count(),
        total_messages=db.query(models.Message).count(),
        total_saved=db.query(models.SavedProperty).count(),
    )


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(
    request: Request,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin),
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        schemas.UserOut(
            id=u.id,
            full_name=u.full_name,
            email=u.email,
            phone=u.phone,
            avatar_url=absolute_url(request, u.avatar_path),
            is_admin=u.is_admin,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="O'zingizni o'chira olmaysiz")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    db.delete(user)
    db.commit()
    return None


@router.delete("/properties/{property_id}", status_code=204)
def delete_any_property(
    property_id: int,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(get_current_admin),
):
    """Same as DELETE /properties/{id}, but bypasses the owner check —
    lets an admin moderate/remove any listing."""
    from ..utils.files import delete_upload

    property_ = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property_:
        raise HTTPException(status_code=404, detail="E'lon topilmadi")
    for img in property_.images:
        delete_upload(img.path)
    db.delete(property_)
    db.commit()
    return None

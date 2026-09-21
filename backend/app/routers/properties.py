from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import absolute_url, get_current_user, get_optional_user
from ..utils.files import delete_upload, save_upload

router = APIRouter(prefix="/properties", tags=["Properties"])


def _blank_to_none(value):
    """Treat an empty-string query param (e.g. '?min_price=' from a browser
    or a Postman param left checked-but-blank) the same as if it were
    omitted, instead of letting FastAPI raise a 422 trying to parse it."""
    return None if value in ("", None) else value


def _to_property_out(
    property_: models.Property, request: Request, current_user: models.User | None
) -> schemas.PropertyOut:
    is_saved = False
    if current_user is not None:
        is_saved = any(link.user_id == current_user.id for link in property_.saved_by)

    return schemas.PropertyOut(
        id=property_.id,
        title=property_.title,
        description=property_.description,
        location=property_.location,
        price=property_.price,
        price_unit=property_.price_unit,
        bedrooms=property_.bedrooms,
        bathrooms=property_.bathrooms,
        floor=property_.floor,
        area=property_.area,
        renovation=property_.renovation,
        amenities=property_.amenities or [],
        student_friendly=property_.student_friendly,
        created_at=property_.created_at,
        owner=schemas.OwnerOut(
            id=property_.owner.id,
            full_name=property_.owner.full_name,
            phone=property_.owner.phone,
            avatar_url=absolute_url(request, property_.owner.avatar_path),
        ),
        images=[
            schemas.PropertyImageOut(id=img.id, url=absolute_url(request, img.path))
            for img in property_.images
        ],
        is_saved=is_saved,
    )


@router.get("", response_model=schemas.PropertyListOut)
def list_properties(
    request: Request,
    q: str | None = Query(default=None, description="Search in title/location"),
    location: str | None = None,
    min_price: str | None = Query(default=None, description="Number, or leave blank/omit for no lower bound"),
    max_price: str | None = Query(default=None, description="Number, or leave blank/omit for no upper bound"),
    min_bedrooms: str | None = Query(default=None),
    min_bathrooms: str | None = Query(default=None),
    renovation: str | None = None,
    amenities: str | None = Query(default=None, description="Comma-separated amenity names"),
    student_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_optional_user),
):
    # Query params arrive as plain strings here so a blank value (e.g. an
    # unchecked-but-present Postman param, or '?min_price=' from a browser)
    # can't trigger a 422 — we normalize and cast them ourselves below.
    location = _blank_to_none(location)
    renovation = _blank_to_none(renovation)
    amenities = _blank_to_none(amenities)
    q = _blank_to_none(q)

    def _to_number(raw: str | None, cast, field_name: str):
        raw = _blank_to_none(raw)
        if raw is None:
            return None
        try:
            return cast(raw)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{field_name} must be a number")

    min_price_n = _to_number(min_price, float, "min_price")
    max_price_n = _to_number(max_price, float, "max_price")
    min_bedrooms_n = _to_number(min_bedrooms, int, "min_bedrooms")
    min_bathrooms_n = _to_number(min_bathrooms, int, "min_bathrooms")

    query = db.query(models.Property)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(models.Property.title.ilike(like), models.Property.location.ilike(like)))
    if location:
        query = query.filter(models.Property.location == location)
    if min_price_n is not None:
        query = query.filter(models.Property.price >= min_price_n)
    if max_price_n is not None:
        query = query.filter(models.Property.price <= max_price_n)
    if min_bedrooms_n is not None:
        query = query.filter(models.Property.bedrooms >= min_bedrooms_n)
    if min_bathrooms_n is not None:
        query = query.filter(models.Property.bathrooms >= min_bathrooms_n)
    if renovation:
        query = query.filter(models.Property.renovation == renovation)
    if student_only:
        query = query.filter(models.Property.student_friendly.is_(True))

    total = query.count()
    results = query.order_by(models.Property.created_at.desc()).offset(skip).limit(limit).all()

    if amenities:
        wanted = {a.strip().lower() for a in amenities.split(",") if a.strip()}
        results = [
            p for p in results if wanted.issubset({a.lower() for a in (p.amenities or [])})
        ]
        total = len(results)

    return schemas.PropertyListOut(
        total=total,
        items=[_to_property_out(p, request, current_user) for p in results],
    )


@router.get("/{property_id}", response_model=schemas.PropertyOut)
def get_property(
    property_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_optional_user),
):
    property_ = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property_:
        raise HTTPException(status_code=404, detail="E'lon topilmadi")
    return _to_property_out(property_, request, current_user)


@router.post("", response_model=schemas.PropertyOut, status_code=201)
def create_property(
    payload: schemas.PropertyCreate,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = models.Property(owner_id=current_user.id, **payload.model_dump())
    db.add(property_)
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, request, current_user)


def _get_owned_property(property_id: int, current_user: models.User, db: Session) -> models.Property:
    property_ = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property_:
        raise HTTPException(status_code=404, detail="E'lon topilmadi")
    if property_.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Bu e'lonni tahrirlash huquqingiz yo'q")
    return property_


@router.put("/{property_id}", response_model=schemas.PropertyOut)
def update_property(
    property_id: int,
    payload: schemas.PropertyUpdate,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = _get_owned_property(property_id, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(property_, field, value)
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, request, current_user)


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = _get_owned_property(property_id, current_user, db)
    for img in property_.images:
        delete_upload(img.path)
    db.delete(property_)
    db.commit()
    return None


@router.post("/{property_id}/images", response_model=schemas.PropertyOut)
def upload_property_images(
    property_id: int,
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = _get_owned_property(property_id, current_user, db)
    for f in files:
        relative_path = save_upload(f, f"properties/{property_id}")
        db.add(models.PropertyImage(property_id=property_id, path=relative_path))
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, request, current_user)


@router.delete("/{property_id}/images/{image_id}", response_model=schemas.PropertyOut)
def delete_property_image(
    property_id: int,
    image_id: int,
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = _get_owned_property(property_id, current_user, db)
    image = next((img for img in property_.images if img.id == image_id), None)
    if not image:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")

    delete_upload(image.path)
    db.delete(image)
    db.commit()
    db.refresh(property_)
    return _to_property_out(property_, request, current_user)


@router.post("/{property_id}/save", response_model=schemas.SaveToggleOut)
def toggle_save(
    property_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    property_ = db.query(models.Property).filter(models.Property.id == property_id).first()
    if not property_:
        raise HTTPException(status_code=404, detail="E'lon topilmadi")

    link = (
        db.query(models.SavedProperty)
        .filter(
            models.SavedProperty.user_id == current_user.id,
            models.SavedProperty.property_id == property_id,
        )
        .first()
    )
    if link:
        db.delete(link)
        db.commit()
        return schemas.SaveToggleOut(saved=False)

    db.add(models.SavedProperty(user_id=current_user.id, property_id=property_id))
    db.commit()
    return schemas.SaveToggleOut(saved=True)

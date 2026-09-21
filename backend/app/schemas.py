from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------- Auth / Users ----------

class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    avatar_url: str | None = None
    created_at: dt.datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Properties ----------

class PropertyImageOut(BaseModel):
    id: int
    url: str

    class Config:
        from_attributes = True


class PropertyBase(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    location: str = Field(min_length=1, max_length=150)
    price: float = Field(ge=0)
    price_unit: str = "Oy"
    bedrooms: int = Field(ge=0, le=20, default=1)
    bathrooms: int = Field(ge=0, le=20, default=1)
    floor: int = Field(ge=0, le=200, default=1)
    area: float = Field(ge=0, default=0)
    renovation: str = "O'rtacha"
    amenities: list[str] = []
    student_friendly: bool = False

    @field_validator("price_unit")
    @classmethod
    def _validate_unit(cls, v: str) -> str:
        if v not in ("Kun", "Oy"):
            raise ValueError("price_unit must be 'Kun' or 'Oy'")
        return v


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    location: str | None = None
    price: float | None = None
    price_unit: str | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    floor: int | None = None
    area: float | None = None
    renovation: str | None = None
    amenities: list[str] | None = None
    student_friendly: bool | None = None


class OwnerOut(BaseModel):
    id: int
    full_name: str
    phone: str | None = None
    avatar_url: str | None = None

    class Config:
        from_attributes = True


class PropertyOut(PropertyBase):
    id: int
    created_at: dt.datetime
    owner: OwnerOut
    images: list[PropertyImageOut] = []
    is_saved: bool = False

    class Config:
        from_attributes = True


class PropertyListOut(BaseModel):
    total: int
    items: list[PropertyOut]


class SaveToggleOut(BaseModel):
    saved: bool

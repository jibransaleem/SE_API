from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date
from typing import Optional, Literal, List, Union

# ---------- SIGNUP ----------
class UserCreate(BaseModel):
    role: Literal["student", "admin"] = Field(..., description="User role: student or admin")
    fullname: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    field_of_study: str = Field(..., max_length=100)
    year: int = Field(..., ge=0, le=10)
    password: str = Field(..., min_length=6, max_length=100)

    @validator('role')
    def validate_role(cls, v):
        if v not in ['student', 'admin']:
            raise ValueError('Role must be either "student" or "admin"')
        return v

    @validator('year')
    def validate_year(cls, v, values):
        if values.get('role') == 'admin' and v != 0:
            raise ValueError('Year must be 0 for admin role')
        if values.get('role') == 'student' and v == 0:
            raise ValueError('Year must be between 1–10 for student role')
        return v


# ---------- LOGIN ----------
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


# ---------- USER RESPONSE ----------
class UserResponse(BaseModel):
    id: int
    role: str
    fullname: str
    email: EmailStr
    field_of_study: str
    year: int
    created_at: datetime

    class Config:
        orm_mode = True


# ---------- LOST ITEM ----------
class LostItemCreate(BaseModel):
    user_id: int
    item_name: str = Field(..., min_length=3, max_length=100)
    item_description: str = Field(..., min_length=10, max_length=500)
    email: EmailStr
    location: str = Field(..., min_length=3, max_length=100)


class LostItemResponse(BaseModel):
    id: int
    user_id: int
    item_name: str
    item_description: str
    email: EmailStr
    date: date
    location: str
    found: bool
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

    @validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'approved', 'rejected']:
            raise ValueError('Status must be pending, approved, or rejected')
        return v


class LostItemUpdate(BaseModel):
    item_name: Optional[str] = Field(None, min_length=3, max_length=100)
    item_description: Optional[str] = Field(None, min_length=10, max_length=500)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)


# ---------- REPORTED ITEM ----------
class ReportedItemCreate(BaseModel):
    user_id: int
    item_name: str = Field(..., min_length=3, max_length=100)
    item_description: str = Field(..., min_length=10, max_length=500)
    email: EmailStr
    location: str = Field(..., min_length=3, max_length=100)


class ReportedItemResponse(BaseModel):
    id: int
    user_id: int
    item_name: str
    item_description: str
    email: EmailStr
    date: date
    location: str
    status: str  # open / resolved
    created_at: datetime

    class Config:
        orm_mode = True

    @validator('status')
    def validate_status(cls, v):
        if v not in ['open', 'resolved']:
            raise ValueError('Status must be open or resolved')
        return v


class ReportedItemUpdate(BaseModel):
    item_name: Optional[str] = Field(None, min_length=3, max_length=100)
    item_description: Optional[str] = Field(None, min_length=10, max_length=500)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    status: Optional[str] = Field(None, description="open or resolved")


# ---------- CLAIM ----------
class ClaimCreate(BaseModel):
    user_id: int = Field(..., gt=0, description="ID of user making the claim")
    claim_type: Literal["lost", "reported"] = Field(..., description="Which type of item is being claimed")
    item_id: int = Field(..., gt=0, description="ID of item being claimed")
    claim_message: str = Field(..., min_length=20, max_length=1000)

    @validator('claim_message')
    def validate_claim_message(cls, v):
        if len(v.strip()) < 20:
            raise ValueError('Claim message must be at least 20 characters after trimming')
        return v.strip()


class ClaimResponse(BaseModel):
    id: int
    user_id: int
    lost_item_id: Optional[int]
    reported_item_id: Optional[int]
    claim_message: str
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

    @validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'approved', 'rejected']:
            raise ValueError('Status must be pending, approved, or rejected')
        return v


# ---------- PAGINATED RESPONSES ----------
class PaginatedLostItemsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[LostItemResponse]


class PaginatedReportedItemsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ReportedItemResponse]


class PaginatedClaimsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    claims: List[ClaimResponse]

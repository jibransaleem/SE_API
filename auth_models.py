from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, date
from typing import Optional, Literal

# ---------- SIGNUP ----------
class UserCreate(BaseModel):
    role: Literal["student", "admin"] = Field(..., description="User role: student or admin")
    first_name: str = Field(..., min_length=2, max_length=50)
    last_name: str = Field(..., min_length=2, max_length=50)
    home_address: str = Field(..., min_length=5, max_length=200)
    email: EmailStr
    field_of_study: str = Field(..., max_length=100)
    year: int = Field(..., ge=0, le=10)  # 0 for admin, 1-10 for students
    password: str = Field(..., min_length=6, max_length=100)

    @validator('role')
    def validate_role(cls, v):
        if v not in ['student', 'admin']:
            raise ValueError('Role must be either "student" or "admin"')
        return v

    @validator('year')
    def validate_year(cls, v, values):
        # If role is admin, year should be 0
        if values.get('role') == 'admin' and v != 0:
            raise ValueError('Year must be 0 for admin role')
        # If role is student, year should be 1-10
        if values.get('role') == 'student' and v == 0:
            raise ValueError('Year must be between 1-10 for student role')
        return v

# ---------- LOGIN ----------
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

# ---------- USER RESPONSE ----------
class UserResponse(BaseModel):
    id: int
    role: str
    first_name: str
    last_name: str
    home_address: str
    email: EmailStr
    field_of_study: str
    year: int
    created_at: datetime

    class Config:
        orm_mode = True

# ---------- LOST ITEM ----------
class LostItemCreate(BaseModel):
    """
    Note: This model is NOT used in the current API.
    The API uses Form() parameters instead for file upload support.
    Keeping for reference only.
    """
    user_id: int
    item_name: str = Field(..., min_length=3, max_length=100)
    item_description: str = Field(..., min_length=10, max_length=500)
    email: EmailStr
    location: str = Field(..., min_length=3, max_length=100)
    # date is auto-generated, not user input

class LostItemResponse(BaseModel):
    id: int
    user_id: int
    item_name: str
    item_description: str
    email: EmailStr
    date: date  # Changed from datetime to date
    location: str
    found: bool
    status: str  # "pending", "approved", "rejected"
    created_at: datetime

    class Config:
        orm_mode = True

    @validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'approved', 'rejected']:
            raise ValueError('Status must be pending, approved, or rejected')
        return v

class LostItemUpdate(BaseModel):
    """
    Used for updating item details (not image).
    All fields are optional.
    """
    item_name: Optional[str] = Field(None, min_length=3, max_length=100)
    item_description: Optional[str] = Field(None, min_length=10, max_length=500)
    email: Optional[EmailStr] = None
    location: Optional[str] = Field(None, min_length=3, max_length=100)
    # Removed date and item_image as they shouldn't be updated

# ---------- CLAIM ----------
class ClaimCreate(BaseModel):
    user_id: int = Field(..., gt=0, description="ID of user making the claim")
    item_id: int = Field(..., gt=0, description="ID of item being claimed")
    claim_message: str = Field(
        ..., 
        min_length=20, 
        max_length=1000,
        description="Detailed message proving ownership"
    )

    @validator('claim_message')
    def validate_claim_message(cls, v):
        # Ensure message has substance
        if len(v.strip()) < 20:
            raise ValueError('Claim message must be at least 20 characters after trimming')
        return v.strip()

class ClaimResponse(BaseModel):
    id: int
    user_id: int
    item_id: int
    claim_message: str
    status: str  # "pending", "approved", "rejected"
    created_at: datetime

    class Config:
        orm_mode = True

    @validator('status')
    def validate_status(cls, v):
        if v not in ['pending', 'approved', 'rejected']:
            raise ValueError('Status must be pending, approved, or rejected')
        return v

# ---------- ADDITIONAL MODELS FOR BETTER API RESPONSES ----------

class ItemApprovalResponse(BaseModel):
    """Response after approving/rejecting an item"""
    item_id: int
    status: str
    message: str

class ClaimApprovalResponse(BaseModel):
    """Response after approving/rejecting a claim"""
    claim_id: int
    status: str
    message: str
    email_sent: bool = False

class LoginResponse(BaseModel):
    """Enhanced login response"""
    user_id: int
    role: str
    email: str
    first_name: str
    last_name: str
    token: Optional[str] = None  # For future JWT implementation

class PaginatedItemsResponse(BaseModel):
    """For paginated item lists"""
    total: int
    page: int
    page_size: int
    items: list[LostItemResponse]

class PaginatedClaimsResponse(BaseModel):
    """For paginated claim lists"""
    total: int
    page: int
    page_size: int
    claims: list[ClaimResponse]
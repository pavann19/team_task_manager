"""User-related Pydantic schemas."""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from email_validator import validate_email, EmailNotValidError

from app.db.models import UserRole


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = UserRole.MEMBER

    @field_validator("email")
    def validate_email_address(cls, v):
        try:
            # check_deliverability=True verifies DNS/MX records
            email_info = validate_email(v, check_deliverability=True)
            return email_info.normalized
        except EmailNotValidError as e:
            raise ValueError(str(e))


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

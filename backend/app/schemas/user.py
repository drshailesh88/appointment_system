"""
User schemas for authentication and user management.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=15)
    name: str = Field(..., min_length=2, max_length=200)
    role: UserRole = UserRole.RECEPTIONIST


class UserCreate(UserBase):
    """Schema for creating a user."""

    password: str = Field(..., min_length=8, max_length=100)
    clinic_id: UUID | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError(
                "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
            )

        # Check for common weak passwords
        common_passwords = {
            "password", "password123", "12345678", "qwerty", "admin123",
            "welcome123", "letmein", "monkey", "1234567890", "abc123"
        }
        if v.lower() in common_passwords:
            raise ValueError("This password is too common. Please choose a stronger password")

        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number."""
        # Remove spaces and dashes
        v = v.replace(" ", "").replace("-", "")
        # Add India country code if not present
        if not v.startswith("+"):
            if v.startswith("0"):
                v = "+91" + v[1:]
            else:
                v = "+91" + v
        return v


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = Field(None, min_length=2, max_length=200)
    phone: str | None = Field(None, min_length=10, max_length=15)
    role: UserRole | None = None
    avatar_url: str | None = None
    is_active: bool | None = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr | None = None
    phone: str | None = None
    password: str

    @field_validator("phone")
    @classmethod
    def validate_login(cls, v: str | None, info) -> str | None:
        """Ensure either email or phone is provided."""
        if v is None and info.data.get("email") is None:
            raise ValueError("Either email or phone must be provided")
        return v


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    email: str
    phone: str
    name: str
    role: str
    avatar_url: str | None
    clinic_id: UUID | None
    is_active: bool
    is_verified: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str
    exp: int
    type: str = "access"
    clinic_id: str | None = None
    role: str | None = None


class OTPRequest(BaseModel):
    """Schema for OTP request."""

    phone: str = Field(..., min_length=10, max_length=15)


class OTPVerify(BaseModel):
    """Schema for OTP verification."""

    phone: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=4, max_length=6)


class PasswordReset(BaseModel):
    """Schema for password reset."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength.

        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in v):
            raise ValueError(
                "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
            )

        # Check for common weak passwords
        common_passwords = {
            "password", "password123", "12345678", "qwerty", "admin123",
            "welcome123", "letmein", "monkey", "1234567890", "abc123"
        }
        if v.lower() in common_passwords:
            raise ValueError("This password is too common. Please choose a stronger password")

        return v

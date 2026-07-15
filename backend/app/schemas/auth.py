"""Auth request and response schemas."""

import re

from pydantic import BaseModel, field_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Username is required.")
        return value.strip()

    @field_validator("email")
    @classmethod
    def email_valid(cls, value: str) -> str:
        if not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address.")
        return value.lower()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    email: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar_url: str = ""

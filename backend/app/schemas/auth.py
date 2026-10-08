from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254, examples=["demo@example.com"])
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    display_name: str
    account_id: str


class SessionOut(BaseModel):
    user: UserOut
    expires_at: datetime


class DemoCredentials(BaseModel):
    email: str
    password: str

"""Authentication request bodies."""

from pydantic import BaseModel, Field, SecretStr


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=320)
    password: SecretStr

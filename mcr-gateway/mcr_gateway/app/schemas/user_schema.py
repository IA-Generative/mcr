from enum import StrEnum
from typing import Optional

from pydantic import UUID4, BaseModel, EmailStr


class Role(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class KeycloakRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"
    BETA_TESTER = "BETA_TESTER"


class UserBase(BaseModel):
    """
    Base schema for user-related data.
    """

    keycloak_uuid: Optional[UUID4] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    entity_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[Role] = None


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """

    first_name: str
    last_name: str
    entity_name: str
    email: EmailStr
    password: Optional[str] = None


class UserUpdate(UserBase):
    """
    Schema for updating an existing user.
    """

    email: EmailStr
    password: Optional[str] = None
    role: Role


class UserDeleteResponse(BaseModel):
    """
    Schema for the response returned when a user is deleted.
    """

    id: int
    message: str


class User(UserBase):
    """
    Schema representing a user, including their ID and email and Role
    """

    id: int
    email: EmailStr
    role: Role


class UserCredentials(BaseModel):
    """
    Schema for user credentials.
    """

    email: str
    password: str


class TokenResponse(BaseModel):
    """
    Schema for the token response.
    """

    access_token: str
    token_type: str


class TokenUser(BaseModel):
    """
    Schema representing a user data which will be stored in the JWT token
    """

    keycloak_uuid: UUID4
    first_name: str
    last_name: str
    entity_name: str
    email: str
    role: Role

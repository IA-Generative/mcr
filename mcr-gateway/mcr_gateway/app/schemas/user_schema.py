from enum import StrEnum

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

    keycloak_uuid: UUID4 | None = None
    first_name: str | None = None
    last_name: str | None = None
    entity_name: str | None = None
    email: EmailStr | None = None
    role: Role | None = None


class UserCreate(UserBase):
    """
    Schema for creating a new user.
    """

    first_name: str
    last_name: str
    entity_name: str
    email: EmailStr
    password: str | None = None


class UserUpdate(UserBase):
    """
    Schema for updating an existing user.
    """

    email: EmailStr
    password: str | None = None
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

from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr

from mcr_meeting.app.models.user_model import Role


class UserBase(BaseModel):
    """
    Base class for user-related data, used as a base for creating and updating user information.

    Attributes:
        first_name (str, optional): The user's first name.
        last_name (str, optional): The user's last name.
        entity_name (str, optional): The name of the entity the user belongs to (e.g., company).
        email (EmailStr, optional): The user's email address, formatted as an email.
    """

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    entity_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserCreate(UserBase):
    """
    Class used for creating a new user. Inherits from UserBase and adds required fields for user creation.

    Attributes:
        keycloak_uuid (UUID4): The user's keycloak UUID.
        first_name (str): The user's first name.
        last_name (str): The user's last name.
        entity_name (str): The name of the entity the user belongs to (e.g., company).
        email (EmailStr): The user's email address.
    """

    keycloak_uuid: UUID4
    first_name: str
    last_name: str
    entity_name: str
    email: EmailStr


class UserUpdate(UserBase):
    """
    Class used for updating an existing user's information. Inherits from UserBase and allows optional fields for update.

    Attributes:
        password (str, optional): The new password for the user.
        role (Role): The role of the user (assumed to be an enum or similar).
    """

    password: Optional[str] = None
    role: Role


class UserDeleteResponse(BaseModel):
    """
    Response model returned after a user is deleted.

    Attributes:
        id (int): The ID of the deleted user.
        message (str): A message confirming the deletion of the user.
    """

    id: int
    message: str


class UserResponse(UserCreate):
    """
    Model representing a user, includes all fields for user information, including ID and role.

    Attributes:
        id (int): The unique identifier of the user.
        email (EmailStr): The user's email address.
        role (Role): The role of the user (assumed to be an enum or similar).

    Configuration:
        - orm_mode: Ensures that the model can be used with ORMs like SQLAlchemy.
        - from_attributes: Indicates the use of attributes in the ORM mapping.
    """

    id: int
    email: EmailStr
    role: Role

    model_config = ConfigDict(from_attributes=True)

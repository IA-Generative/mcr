from typing import TYPE_CHECKING, List

if TYPE_CHECKING:  # Avoid circular imports but allow proper typing
    from .meeting_model import Meeting

from enum import StrEnum
from uuid import UUID

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.db import Base


class Role(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(Base):
    """
    User model for the database.

    Attributes:
        id (int): The primary key of the user.
        keycloak_uuid (uuid): The keycloak UUID of the user.
        first_name (str): The first name of the user.
        last_name (str): The last name of the user.
        entity_name (str): The entity name of the user.
        email (str): The email of the user.
        role (enum): The user role.
        meetings (relationship): The relationship to the Meeting model.
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    keycloak_uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String, index=True)
    last_name: Mapped[str] = mapped_column(String, index=True)
    entity_name: Mapped[str] = mapped_column(String, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[Role] = mapped_column(SQLEnum(Role), default=Role.USER)
    meetings: Mapped[List["Meeting"]] = relationship(back_populates="owner")

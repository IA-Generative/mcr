from uuid import UUID

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mcr_capture_worker.db.db import Base


class User(Base):
    """
    ORM representation of a User for the database in the capture worker

    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    keycloak_uuid: Mapped[UUID] = mapped_column(Uuid, unique=True, index=True)

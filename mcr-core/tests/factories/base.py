from typing import Generic, TypeVar

from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy.orm import Session

from mcr_meeting.app.db.db import get_db_session_ctx

T = TypeVar("T")


class BaseFactory(SQLAlchemyModelFactory, Generic[T]):
    """
    Base factory for SQLAlchemy models.

    Uses the context variable session management to integrate with test fixtures.
    All factories inherit from this base to ensure they use the test session.
    """

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = "flush"  # Use flush instead of commit

    @classmethod
    def _create(cls, model_class, *args, **kwargs) -> T:
        """
        Create an instance using the session from context variable.

        This ensures factories use the same session as repositories and
        participate in the test transaction for automatic rollback.
        """
        session: Session = get_db_session_ctx()
        obj = model_class(*args, **kwargs)
        session.add(obj)
        session.flush()  # Flush to get IDs without committing
        return obj

    def __call__(cls, *args, **kwargs) -> T:
        return super().__call__(*args, **kwargs)

    @classmethod
    def create(cls, **kwargs) -> T:
        return super().create(**kwargs)

    @classmethod
    def build(cls, **kwargs) -> T:
        return super().build(**kwargs)

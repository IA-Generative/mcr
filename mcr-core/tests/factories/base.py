from typing import Any, Generic, TypeVar

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
    def _create(cls, model_class: type[T], *args: Any, **kwargs: Any) -> T:  # type: ignore[explicit-any, no-untyped-def]
        """
        Create an instance using the session from context variable.

        This ensures factories use the same session as repositories and
        participate in the test transaction for automatic rollback.
        """
        session: Session = get_db_session_ctx()
        obj = model_class(*args, **kwargs)
        session.add(obj)
        session.flush()  # Flush to get IDs without committing
        return obj  # type: ignore[no-any-return]

    def __call__(cls, *args: Any, **kwargs: Any) -> T:  # type: ignore[explicit-any, no-untyped-def]
        return super().__call__(*args, **kwargs)  # type: ignore[no-any-return, misc]

    @classmethod
    def create(cls, **kwargs: Any) -> T:  # type: ignore[explicit-any, no-untyped-def]
        return super().create(**kwargs)  # type: ignore[no-any-return]

    @classmethod
    def build(cls, **kwargs: Any) -> T:  # type: ignore[explicit-any, no-untyped-def]
        return super().build(**kwargs)  # type: ignore[no-any-return]

from contextlib import AbstractContextManager
from types import TracebackType
from typing import Callable, Self

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, SessionTransaction

from mcr_meeting.app.db.db import get_db_session_ctx
from mcr_meeting.app.exceptions.exceptions import NotSavedException


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    def __init__(self, session_factory: Callable[[], Session] = get_db_session_ctx):
        self._session_factory = session_factory
        self.session: Session | None = None
        self.nested_transaction: SessionTransaction | None = None

    def __enter__(self) -> Self:
        self.session = get_db_session_ctx()
        # Auto-detect if we need a savepoint:
        # If there's already an active transaction (e.g., test environment),
        # use a nested transaction to avoid rolling back existing data.
        # In production with no parent transaction, commit will persist to DB.
        if self.session.in_transaction() and self.session.is_active:
            self.nested_transaction = self.session.begin_nested()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()

    def commit(self) -> None:
        if self.session is None:
            raise RuntimeError("UnitOfWork session is not initialized")
        try:
            # Calling commit on the session will automatically handle the nested transaction
            # In test env with external transaction, this just flushes changes
            # In production, this commits the transaction
            self.session.commit()
        except SQLAlchemyError as e:
            self.rollback()
            raise NotSavedException(f"Erreur lors de la transaction : {str(e)}") from e

    def rollback(self) -> None:
        if self.session is None:
            raise RuntimeError("UnitOfWork session is not initialized")
        # Rollback the nested transaction (rollback to savepoint)
        if self.nested_transaction and self.nested_transaction.is_active:
            self.nested_transaction.rollback()

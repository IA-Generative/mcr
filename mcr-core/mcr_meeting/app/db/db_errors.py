from sqlalchemy.exc import DataError, IntegrityError, SQLAlchemyError

from mcr_meeting.app.exceptions.exceptions import (
    DataConflictException,
    InvalidDataException,
)


def raise_db_write_error(exc: SQLAlchemyError) -> None:
    if isinstance(exc, DataError):
        raise InvalidDataException(
            "Submitted data was rejected by the database (e.g. a value is too long)."
        ) from exc

    if isinstance(exc, IntegrityError):
        raise DataConflictException(
            "Submitted data violates a database constraint."
        ) from exc

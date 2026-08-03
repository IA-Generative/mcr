from enum import StrEnum
from typing import Any

from sqlalchemy import Dialect, String
from sqlalchemy.types import TypeDecorator


class StrEnumType(TypeDecorator[StrEnum]):
    """Persists a StrEnum as its value in an unbounded VARCHAR.

    The storage type stays a bare `String` on purpose: PG keeps a plain varchar
    (no native enum, no CHECK constraint, no length ceiling to migrate when a
    longer member is added). `Enum(native_enum=False)` would also store text but
    emits `VARCHAR(n)` and persists member *names* rather than values.

    Without this, `mapped_column(String)` under a `Mapped[SomeStrEnum]`
    annotation returns a raw `str` at load time while the type checker believes
    it is an enum member — so enum operations pass mypy and fail at runtime.
    """

    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type[StrEnum], *args: Any, **kwargs: Any) -> None:  # type: ignore[explicit-any]
        super().__init__(*args, **kwargs)
        self._enum_cls = enum_cls

    def process_bind_param(
        self, value: StrEnum | str | None, dialect: Dialect
    ) -> str | None:
        return None if value is None else str(value)

    def process_result_value(
        self, value: str | None, dialect: Dialect
    ) -> StrEnum | None:
        return None if value is None else self._enum_cls(value)

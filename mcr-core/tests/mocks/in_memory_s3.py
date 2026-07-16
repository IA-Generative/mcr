from collections import Counter
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from enum import StrEnum
from io import BytesIO
from typing import Any, BinaryIO

from botocore.exceptions import ResponseStreamingError


class S3Op(StrEnum):
    GET = "get_object"
    PUT = "put_object"
    LIST = "list_objects_v2"


class NoSuchKey(Exception):
    pass


class _Exceptions:
    NoSuchKey = NoSuchKey


class _ListObjectsPaginator:
    def __init__(
        self, objects: dict[str, bytes], tick: "Callable[[str], None]"
    ) -> None:
        self._objects = objects
        self._tick = tick

    def paginate(
        self, *, Bucket: str, Prefix: str = "", **_: Any
    ) -> Iterator[dict[str, Any]]:
        self._tick(S3Op.LIST)
        contents = [
            {"Key": key, "LastModified": datetime(2026, 1, 1, tzinfo=UTC)}
            for key in self._objects
            if key.startswith(Prefix)
        ]
        # boto3 omits "Contents" entirely on empty pages
        yield {"Contents": contents} if contents else {}


def transient_error() -> ResponseStreamingError:
    """The failure real S3 raises when a connection drops mid-transfer."""
    return ResponseStreamingError(error=Exception("connection reset mid-body"))


class InMemoryS3:
    exceptions = _Exceptions

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.calls: Counter[S3Op] = Counter()
        self._faults: dict[S3Op, list[Exception]] = {}

    def fail(self, op: S3Op, exc: Exception, times: int = 1) -> None:
        """Queue `exc` to be raised on the next `times` calls to `op`, then
        normal behaviour resumes."""
        self._faults.setdefault(op, []).extend([exc] * times)

    def _tick(self, op: S3Op) -> None:
        self.calls[op] += 1
        queued = self._faults.get(op)
        if queued:
            raise queued.pop(0)

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO | bytes,
        ContentType: str = "",
    ) -> dict[str, Any]:
        data = Body.read() if hasattr(Body, "read") else Body
        assert isinstance(data, bytes)
        self._tick("put_object")
        self.objects[Key] = data
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        self._tick("get_object")
        if Key not in self.objects:
            raise NoSuchKey(f"Key not found: {Key}")
        return {"Body": BytesIO(self.objects[Key])}

    def get_paginator(self, operation_name: str) -> _ListObjectsPaginator:
        assert operation_name == "list_objects_v2"
        return _ListObjectsPaginator(self.objects, self._tick)

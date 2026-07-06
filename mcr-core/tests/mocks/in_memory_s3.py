from collections.abc import Iterator
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, BinaryIO


class NoSuchKey(Exception):
    pass


class _Exceptions:
    NoSuchKey = NoSuchKey


class _ListObjectsPaginator:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self._objects = objects

    def paginate(
        self, *, Bucket: str, Prefix: str = "", **_: Any
    ) -> Iterator[dict[str, Any]]:
        contents = [
            {"Key": key, "LastModified": datetime(2026, 1, 1, tzinfo=UTC)}
            for key in self._objects
            if key.startswith(Prefix)
        ]
        # boto3 omits "Contents" entirely on empty pages
        yield {"Contents": contents} if contents else {}


class InMemoryS3:
    exceptions = _Exceptions

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.should_fail_put = False
        self.should_fail_get = False

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO | bytes,
        ContentType: str = "",
    ) -> dict[str, Any]:
        if self.should_fail_put:
            raise RuntimeError("S3 put failed")
        data = Body.read() if hasattr(Body, "read") else Body
        assert isinstance(data, bytes)
        self.objects[Key] = data
        return {}

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        if self.should_fail_get:
            raise RuntimeError("S3 get failed")
        if Key not in self.objects:
            raise NoSuchKey(f"Key not found: {Key}")
        return {"Body": BytesIO(self.objects[Key])}

    def get_paginator(self, operation_name: str) -> _ListObjectsPaginator:
        assert operation_name == "list_objects_v2"
        return _ListObjectsPaginator(self.objects)

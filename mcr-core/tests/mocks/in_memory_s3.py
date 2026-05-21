from io import BytesIO
from typing import Any, BinaryIO


class NoSuchKey(Exception):
    pass


class _Exceptions:
    NoSuchKey = NoSuchKey


class InMemoryS3:
    exceptions = _Exceptions

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.should_fail_put = False

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
        if Key not in self.objects:
            raise NoSuchKey(f"Key not found: {Key}")
        return {"Body": BytesIO(self.objects[Key])}

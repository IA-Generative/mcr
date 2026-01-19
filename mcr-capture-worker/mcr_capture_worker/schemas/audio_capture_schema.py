from typing import TypedDict

from pydantic import BaseModel, ConfigDict


class OnDataAvailableBytesWrapper(TypedDict):
    js_bytes: list[int]


class S3Object(BaseModel):
    bucket_name: str
    object_name: str

    model_config = ConfigDict(extra="allow")

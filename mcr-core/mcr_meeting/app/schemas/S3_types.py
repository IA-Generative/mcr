from datetime import datetime
from typing import Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcr_meeting.app.exceptions.exceptions import (
    InvalidAudioFileError,
)
from mcr_meeting.app.utils.files_mime_types import guess_mime_type


class S3Object(BaseModel):
    bucket_name: str
    object_name: str
    last_modified: Optional[datetime]

    model_config = ConfigDict(extra="allow")


class S3EventNotificationDto(BaseModel):
    event_name: str = Field(alias="EventName")
    path: str = Field(alias="Key")

    @property
    def meeting_id(self) -> int:
        path_array = self.path.split("/")
        return int(path_array[-2])

    model_config = ConfigDict(
        extra="allow"
    )  # Allow additional fields not defined in the model


class PresignedAudioFileRequest(BaseModel):
    filename: str

    @field_validator("filename")
    @classmethod
    def validate_audio_file(cls, filename: str) -> str:
        if not is_audio_file(filename):
            raise InvalidAudioFileError(
                "Invalid file type. Please upload an audio file."
            )
        return filename


class MultipartInitRequest(PresignedAudioFileRequest):
    content_type: Optional[str] = None


class MultipartBaseRequest(BaseModel):
    upload_id: str
    object_key: str


class MultipartInitResponse(BaseModel):
    upload_id: str
    object_key: str


class MultipartCreationObject(TypedDict):
    upload_id: str
    key: str
    bucket: str


class MultipartSignPartRequest(MultipartBaseRequest):
    part_number: int


class MultipartSignPartResponse(BaseModel):
    url: str


class MultipartCompletePart(BaseModel):
    part_number: int = Field(serialization_alias="PartNumber")
    etag: str = Field(serialization_alias="ETag")


class MultipartCompleteRequest(MultipartBaseRequest):
    parts: list[MultipartCompletePart] = Field(serialization_alias="Parts")


class MultipartAbortRequest(MultipartBaseRequest):
    pass


def is_audio_file(filename: str) -> bool:
    ext = guess_mime_type(filename)
    return ext.startswith("audio/")

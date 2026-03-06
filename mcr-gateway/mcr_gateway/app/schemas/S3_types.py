from pydantic import BaseModel


class PresignedAudioFileRequest(BaseModel):
    filename: str


class MultipartInitRequest(PresignedAudioFileRequest):
    content_type: str | None = None


class MultipartInitResponse(BaseModel):
    upload_id: str
    object_key: str


class MultipartSignPartRequest(BaseModel):
    upload_id: str
    object_key: str
    part_number: int


class MultipartSignPartResponse(BaseModel):
    url: str


class MultipartCompletePart(BaseModel):
    part_number: int
    etag: str


class MultipartCompleteRequest(BaseModel):
    upload_id: str
    object_key: str
    parts: list[MultipartCompletePart]


class MultipartAbortRequest(BaseModel):
    upload_id: str
    object_key: str

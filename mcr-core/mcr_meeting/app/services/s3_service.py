import itertools
from io import BytesIO
from typing import Iterable, Iterator, Tuple, cast

from loguru import logger
from mypy_boto3_s3.type_defs import CompletedPartTypeDef, ObjectIdentifierTypeDef

from mcr_meeting.app.configs.base import S3Settings
from mcr_meeting.app.schemas.S3_types import (
    MultipartCompleteRequest,
    MultipartCreationObject,
    MultipartInitRequest,
    S3Object,
)
from mcr_meeting.app.utils.files_mime_types import guess_mime_type
from mcr_meeting.app.utils.s3_client import s3_client, s3_external_client

s3_settings = S3Settings()


def get_file_from_s3(object_name: str) -> BytesIO:
    try:
        response = s3_client.get_object(Bucket=s3_settings.S3_BUCKET, Key=object_name)

        return BytesIO(response["Body"].read())
    except Exception as e:
        logger.error("Error while getting audio from S3 bucket: {}", e)
        raise e


def get_presigned_url_for_put_file(name: str) -> str:
    return s3_external_client.generate_presigned_url(
        "put_object",
        Params={"Bucket": s3_settings.S3_BUCKET, "Key": name},
        ExpiresIn=3600,  # 1 hour
    )


def create_multipart_upload(
    meeting_id: int,
    init_request: MultipartInitRequest,
) -> MultipartCreationObject:
    """
    Initialize an S3 multipart upload and return the upload id and key.
    """
    object_key = get_audio_object_name(meeting_id, init_request.filename)
    content_type = init_request.content_type or guess_mime_type(init_request.filename)

    response = s3_client.create_multipart_upload(
        Bucket=s3_settings.S3_BUCKET,
        Key=object_key,
        ContentType=content_type,
    )
    return {
        "upload_id": response["UploadId"],
        "key": response["Key"],
        "bucket": s3_settings.S3_BUCKET,
    }


def get_presigned_url_for_upload_part(
    object_key: str, upload_id: str, part_number: int
) -> str:
    """
    Generate a presigned URL for uploading one part of a multipart upload.
    """
    return s3_external_client.generate_presigned_url(
        "upload_part",
        Params={
            "Bucket": s3_settings.S3_BUCKET,
            "Key": object_key,
            "UploadId": upload_id,
            "PartNumber": part_number,
        },
        ExpiresIn=3600,  # 1 hour
    )


def complete_multipart_upload(complete_request: MultipartCompleteRequest) -> None:
    """
    Complete an S3 multipart upload with the list of parts:
    parts = [{ 'ETag': '<etag-from-upload>', 'PartNumber': <int> }, ...]
    """
    s3_client.complete_multipart_upload(
        Bucket=s3_settings.S3_BUCKET,
        Key=complete_request.object_key,
        UploadId=complete_request.upload_id,
        MultipartUpload={
            "Parts": cast(
                list[CompletedPartTypeDef],
                [part.model_dump(by_alias=True) for part in complete_request.parts],
            )
        },
    )


def abort_multipart_upload(object_key: str, upload_id: str) -> None:
    """
    Abort a previously initiated S3 multipart upload.
    """
    s3_client.abort_multipart_upload(
        Bucket=s3_settings.S3_BUCKET, Key=object_key, UploadId=upload_id
    )


def get_objects_list_from_prefix(prefix: str) -> Iterator[S3Object]:
    paginator = s3_client.get_paginator("list_objects_v2")
    page_iterator = paginator.paginate(
        Bucket=s3_settings.S3_BUCKET, Prefix=get_audio_object_prefix(prefix)
    )

    objects = []
    for page in page_iterator:
        if "Contents" in page:
            objects.extend(page["Contents"])

    # Sort by last modified time
    sorted_objects = sorted(objects, key=lambda obj: obj["LastModified"])

    for obj in sorted_objects:
        yield S3Object(
            bucket_name=s3_settings.S3_BUCKET,
            object_name=obj["Key"],
            last_modified=obj["LastModified"],
        )


def get_extension_from_object_list(
    it: Iterator[S3Object],
) -> Tuple[Iterator[S3Object], str]:
    """
    Extract file extension from the first S3 object in the iterator.

    Args:
        it: Iterator of S3Object instances

    Returns:
        Tuple containing the reconstructed iterator and file extension

    Raises:
        ValueError: If no objects are found in the iterator
    """
    try:
        first_object = next(it)
        file_extension = first_object.object_name.split(".")[-1]

        return (itertools.chain([first_object], it), file_extension)

    except StopIteration:
        logger.error("No audio files found in S3 iterator")
        raise ValueError("No audio files found for the specified meeting")


def put_file_to_s3(
    content: BytesIO,
    object_name: str,
    content_type: str = "application/octet-stream",
) -> None:
    """
    Upload file-like object to S3.

    Args:
        content: full file payload as BytesIO
        object_name: destination key within the bucket
        content_type: MIME type (defaults to binary)

    Returns:
        None
    """
    try:
        s3_client.put_object(
            Bucket=s3_settings.S3_BUCKET,
            Key=object_name,
            Body=content,
            ContentType=content_type,
        )
    except Exception as e:
        logger.error("Error while uploading file to S3: {}", e)
        raise


def delete_objects(object_iterable: Iterable[S3Object]) -> bool:
    valid_objects: list[ObjectIdentifierTypeDef] = []

    for obj in list(object_iterable):
        if obj.object_name:
            valid_objects.append({"Key": obj.object_name})

    if not valid_objects:
        logger.warning("No valid S3 object keys to delete.")
        return True

    try:
        response = s3_client.delete_objects(
            Bucket=s3_settings.S3_BUCKET,
            Delete={"Objects": valid_objects},
        )

        # Check if there were any errors
        if "Errors" in response and response["Errors"]:
            logger.error("Errors while deleting objects: {}", response["Errors"])
            return False

        return True
    except Exception as e:
        logger.error("Error while deleting objects: {}", e)
        return False


def get_transcription_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_TRANSCRIPTION_FOLDER}/{meeting_id}/{filename}"


def get_report_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_REPORT_FOLDER}/{meeting_id}/{filename}"


def get_audio_object_name(meeting_id: int, filename: str) -> str:
    return f"{s3_settings.S3_AUDIO_FOLDER}/{meeting_id}/{filename}"


def get_audio_object_prefix(meeting_id: str) -> str:
    normalized_meeting_id = str(meeting_id).strip("/")
    return f"{s3_settings.S3_AUDIO_FOLDER}/{normalized_meeting_id}/"

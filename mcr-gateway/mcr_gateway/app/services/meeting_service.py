from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Generator, List, Optional

import httpx
from fastapi import HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from loguru import logger
from pydantic import UUID4

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.meeting_schema import (
    Meeting,
    MeetingCreate,
    MeetingUpdate,
    MeetingWithPresignedUrl,
)
from mcr_gateway.app.schemas.S3_types import (
    PresignedAudioFileRequest,
)


class MCRCoreCustomAuth(httpx.Auth):
    def __init__(self, user_keycloak_uuid: UUID4):
        self.token = str(user_keycloak_uuid)

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, Any, None]:
        request.headers["X-User-Keycloak-Uuid"] = self.token
        yield request


@asynccontextmanager
async def get_meeting_http_client(
    user_keycloak_uuid: UUID4,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    client = httpx.AsyncClient(
        base_url=settings.MEETING_SERVICE_URL,
        auth=MCRCoreCustomAuth(user_keycloak_uuid),
    )
    try:
        yield client
    finally:
        await client.aclose()


async def create_meeting_service(
    meeting_data: MeetingCreate, user_keycloak_uuid: UUID4
) -> Meeting:
    """
    Service to create a new meeting.

    Args:
        meeting_data (MeetingCreate): The data required to create a new meeting.

    Returns:
        Meeting: The newly created meeting object.
    """
    try:
        meeting_data_dict = meeting_data.model_dump()
        meeting_data_dict["creation_date"] = meeting_data.creation_date.isoformat()
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            # TODO: This would be clearer with the slash not included in the base url
            # To make that change, one would need to change all of the services urls
            response = await client.post("", json=meeting_data_dict)
            response.raise_for_status()
            result = response.json()
            return Meeting(**result)

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def create_meeting_with_presigned_url_service(
    meeting_data: MeetingCreate,
    presigned_request: PresignedAudioFileRequest,
    user_keycloak_uuid: UUID4,
) -> MeetingWithPresignedUrl:
    """
    Service to create a new meeting with a presigned URL for the transcription file.
    Args:
        meeting_data (MeetingCreate): The data required to create a new meeting.
        user_keycloak_uuid (UUID4): The ID of the user creating the meeting.
    Returns:
        Meeting: The newly created meeting object with a presigned URL for the transcription file.
    """
    try:
        meeting_data_dict = meeting_data.model_dump()
        meeting_data_dict["creation_date"] = meeting_data.creation_date.isoformat()

        payload = {
            "meeting_data": meeting_data_dict,
            "presigned_request": presigned_request.model_dump(),
        }

        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                "create_and_generate_presigned_url", json=payload
            )
            response.raise_for_status()

            created_meeting = response.json()
            return MeetingWithPresignedUrl(**created_meeting)

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def generate_presigned_url_service(
    meeting_id: int,
    presigned_request: PresignedAudioFileRequest,
    user_keycloak_uuid: UUID4,
) -> str:
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(
                f"{meeting_id}/presigned_url/generate",
                json=presigned_request.model_dump(),
            )
            response.raise_for_status()

            presigned_url: str = response.json()
            return presigned_url

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def get_meeting_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> Meeting:
    """
    Service to retrieve a single meeting by its ID from the meeting service.

    Args:
        meeting_id (int): The ID of the meeting to retrieve.

    Returns:
        Meeting: The meeting object corresponding to the provided ID.
    """
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.get(f"{meeting_id}")
        response.raise_for_status()
        meeting_data = response.json()
        return Meeting(**meeting_data)


async def update_meeting_service(
    meeting_id: int, user_keycloak_uuid: UUID4, meeting_update: MeetingUpdate
) -> Meeting:
    """
    Service to update an existing meeting.

    Args:
        meeting_id (int): The ID of the meeting to update.
        meeting_update (MeetingUpdate): The updated data for the meeting.

    Returns:
        Meeting: The updated meeting object.
    """
    try:
        meeting_update_dict = meeting_update.model_dump(exclude_unset=True)
        meeting_update_dict["creation_date"] = meeting_update.creation_date.isoformat()

        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.put(f"{meeting_id}", json=meeting_update_dict)
            response.raise_for_status()

            updated_meeting_data = response.json()
            return Meeting(**updated_meeting_data)

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def delete_meeting_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> None:
    """
    Service to delete a meeting by its ID.

    Args:
        meeting_id (int): The ID of the meeting to delete.
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.delete(f"{meeting_id}")
            response.raise_for_status()
            return None

    except httpx.HTTPStatusError as e:
        logger.error(
            "HTTP error occurred: {} - {}", e.response.status_code, e.response.text
        )
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error("Unexpected error occurred: {}", str(e))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def init_meeting_capture_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> None:
    """
    Service to start the transcription for a meeting by calling the mcr-core API.

    Args:
        meeting_id (int): The ID of the meeting to start the transcription for.
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(f"{meeting_id}/capture/init")
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while starting transcription",
        )


async def stop_meeting_capture_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> None:
    """
    Service to stop the transcription for a meeting by calling the mcr-core API.

    Args:
        meeting_id (int): The ID of the meeting for which the transcription should be stopped.
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(url=f"{meeting_id}/capture/stop")
            response.raise_for_status()  # Raise an error for non-200 responses

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while stopping transcription.",
        )


async def get_meetings_service(
    user_keycloak_uuid: UUID4,
    search: Optional[str] = None,
) -> List[Meeting]:
    """
    Service pour interroger mcr-core et récupérer la liste des réunions.

    Args:
        search (str): Terme de recherche optionnel pour filtrer les réunions.

    Returns:
        List[Meeting]: Liste des réunions correspondant au filtre.
    """
    try:
        params = {}

        if search:
            params["search"] = search

        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.get("", params=params)
            response.raise_for_status()
            response_data = response.json()
            return [Meeting(**item) for item in response_data]

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Erreur lors de l'appel à mcr-core : {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue : {str(e)}")


async def start_meeting_transcription_service(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> None:
    async with get_meeting_http_client(user_keycloak_uuid) as client:
        response = await client.post(url=f"{meeting_id}/transcription/init")
        response.raise_for_status()


async def generate_meeting_transcription_document(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> StreamingResponse:
    """
    Service to fetch the transcription DOCX file of a given meeting by calling the API.

    Args:
        meeting_id (int): The ID of the meeting for which the transcription DOCX is needed.

    Returns:
        StreamingResponse: The DOCX file as a streaming response.
    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(url=f"{meeting_id}/transcription")
            response.raise_for_status()  # Raise an error for non-200 responses

            # Return the DOCX file as a StreamingResponse with appropriate headers
            return StreamingResponse(
                response.aiter_bytes(),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f"attachment; filename=meeting_{meeting_id}_transcription.docx"
                },
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while fetching the transcription.",
        )


async def update_meeting_transcription_service(
    meeting_id: int, user_keycloak_uuid: UUID4, file: UploadFile
) -> Response:
    """
    Service to fetch the transcription DOCX file of a given meeting by calling the API.

    Args:
        meeting_id (int): The ID of the meeting for which the transcription DOCX is needed.

    Returns:
        StreamingResponse: The DOCX file as a streaming response.
    """
    try:
        file_content = await file.read()
        files = {
            "file": (
                file.filename,
                file_content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        }
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.put(url=f"{meeting_id}/transcription", files=files)
            response.raise_for_status()  # Raise an error for non-200 responses

            # Return an appropriate response based on your needs
            return Response(status_code=204)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while updating the transcription.",
        )


async def get_report(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> StreamingResponse:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.get(url=f"{meeting_id}/report")
            response.raise_for_status()

            # Return the DOCX file as a StreamingResponse with appropriate headers
            return StreamingResponse(
                response.aiter_bytes(),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f"attachment; filename=meeting_{meeting_id}_report.docx"
                },
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while getting the report.",
        )


async def generate_report(
    meeting_id: int,
    user_keycloak_uuid: UUID4,
) -> Response:
    """
    Get the transcription DOCX file of a given meeting

    Args:
        meeting_id (int): The ID of the meeting.

    Returns:
        DOCX file of the transcription meeting

    """
    try:
        async with get_meeting_http_client(user_keycloak_uuid) as client:
            response = await client.post(url=f"{meeting_id}/report")
            response.raise_for_status()

            return Response(status_code=response.status_code)

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while getting the report.",
        )

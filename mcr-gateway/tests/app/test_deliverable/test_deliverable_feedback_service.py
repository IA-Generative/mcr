import uuid

import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.deliverable_feedback_schema import (
    DeliverableFeedbackUpsertRequest,
)
from mcr_gateway.app.services.deliverable_service import (
    deactivate_deliverable_feedback,
    upsert_deliverable_feedback,
)


@pytest.mark.asyncio
async def test_a_submitted_vote_is_forwarded_to_core_and_echoed_back(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        json={"vote_type": "POSITIVE", "comment": "clear and faithful"},
        status_code=200,
    )

    response = await upsert_deliverable_feedback(
        deliverable_id=7,
        body=DeliverableFeedbackUpsertRequest(
            vote_type="POSITIVE", comment="clear and faithful"
        ),
        user_keycloak_uuid=uuid.uuid4(),
    )

    assert response.status_code == 200
    request = httpx_mock.get_requests()[0]
    assert request.read() == (
        b'{"vote_type":"POSITIVE","comment":"clear and faithful"}'
    )


@pytest.mark.asyncio
async def test_a_retraction_is_forwarded_and_answers_no_content(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        status_code=204,
    )

    response = await deactivate_deliverable_feedback(
        deliverable_id=7, user_keycloak_uuid=uuid.uuid4()
    )

    assert response.status_code == 204


@pytest.mark.asyncio
@pytest.mark.parametrize("core_status", [400, 404, 422])
async def test_a_rejection_from_core_keeps_its_status(
    httpx_mock: HTTPXMock, core_status: int
) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        json={"detail": "rejected"},
        status_code=core_status,
    )

    with pytest.raises(HTTPException) as exc_info:
        await upsert_deliverable_feedback(
            deliverable_id=7,
            body=DeliverableFeedbackUpsertRequest(vote_type="NEGATIVE", comment=None),
            user_keycloak_uuid=uuid.uuid4(),
        )

    assert exc_info.value.status_code == core_status


@pytest.mark.asyncio
async def test_a_retraction_rejected_by_core_keeps_its_status(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="DELETE",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        json={"detail": "not found"},
        status_code=404,
    )

    with pytest.raises(HTTPException) as exc_info:
        await deactivate_deliverable_feedback(
            deliverable_id=7, user_keycloak_uuid=uuid.uuid4()
        )

    assert exc_info.value.status_code == 404

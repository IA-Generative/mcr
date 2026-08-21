import json
import uuid

import pytest
from fastapi import HTTPException
from pytest_httpx import HTTPXMock

from mcr_gateway.app.configs.config import settings
from mcr_gateway.app.schemas.deliverable_feedback_schema import (
    NegativeDeliverableFeedbackUpsertRequest,
    PositiveDeliverableFeedbackUpsertRequest,
)
from mcr_gateway.app.services.deliverable_service import (
    deactivate_deliverable_feedback,
    list_deliverable_feedback_reasons,
    upsert_deliverable_feedback,
)


@pytest.mark.asyncio
async def test_a_submitted_vote_is_forwarded_to_core_and_echoed_back(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        json={"vote_type": "POSITIVE", "comment": "clear and faithful", "reasons": []},
        status_code=200,
    )

    response = await upsert_deliverable_feedback(
        deliverable_id=7,
        body=PositiveDeliverableFeedbackUpsertRequest(
            vote_type="POSITIVE", comment="clear and faithful"
        ),
        user_keycloak_uuid=uuid.uuid4(),
    )

    assert response.status_code == 200
    forwarded = json.loads(httpx_mock.get_requests()[0].read())
    assert forwarded == {"vote_type": "POSITIVE", "comment": "clear and faithful"}


@pytest.mark.asyncio
async def test_the_reasons_a_user_ticked_reach_core_untouched(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="PUT",
        url=f"{settings.DELIVERABLE_SERVICE_URL}7/feedback",
        json={"vote_type": "NEGATIVE", "comment": None, "reasons": ["OFF_TOPIC"]},
        status_code=200,
    )

    await upsert_deliverable_feedback(
        deliverable_id=7,
        body=NegativeDeliverableFeedbackUpsertRequest(
            vote_type="NEGATIVE", comment=None, reasons=["OFF_TOPIC", "OTHER"]
        ),
        user_keycloak_uuid=uuid.uuid4(),
    )

    forwarded = json.loads(httpx_mock.get_requests()[0].read())
    assert forwarded["reasons"] == ["OFF_TOPIC", "OTHER"]


@pytest.mark.asyncio
async def test_the_catalogue_of_reasons_is_relayed_from_core(
    httpx_mock: HTTPXMock,
) -> None:
    catalogue = {
        "TRANSCRIPTION": {
            "deliverable_group": "TRANSCRIPTION",
            "reasons": ["WORD_ERRORS", "OTHER"],
        }
    }
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.DELIVERABLE_SERVICE_URL}feedback-reasons",
        json=catalogue,
        status_code=200,
    )

    response = await list_deliverable_feedback_reasons(user_keycloak_uuid=uuid.uuid4())

    assert response.status_code == 200
    assert json.loads(response.body) == catalogue


@pytest.mark.asyncio
async def test_a_catalogue_core_cannot_serve_keeps_its_status(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url=f"{settings.DELIVERABLE_SERVICE_URL}feedback-reasons",
        json={"detail": "boom"},
        status_code=500,
    )

    with pytest.raises(HTTPException) as exc_info:
        await list_deliverable_feedback_reasons(user_keycloak_uuid=uuid.uuid4())

    assert exc_info.value.status_code == 500


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
            body=NegativeDeliverableFeedbackUpsertRequest(
                vote_type="NEGATIVE", comment=None
            ),
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

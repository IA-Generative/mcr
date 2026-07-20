import uuid

import pytest
from pydantic import ValidationError

from mcr_meeting.app.api.dependencies.auth import _to_user_create
from mcr_meeting.app.schemas.keycloak_claims import TokenClaims


def _generate_fake_claims(**overrides: object) -> TokenClaims:
    data: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "email": "ada@example.com",
        "given_name": "Ada",
        "family_name": "Lovelace",
    }
    data.update(overrides)
    return TokenClaims.model_validate(data)


class TestHasClientRole:
    def test_true_when_role_present(self) -> None:
        claims = _generate_fake_claims(
            resource_access={"mcr": {"roles": ["USER", "ADMIN"]}}
        )
        assert claims.has_client_role("mcr", "ADMIN") is True

    def test_matches_case_insensitively(self) -> None:
        claims = _generate_fake_claims(resource_access={"mcr": {"roles": ["admin"]}})
        assert claims.has_client_role("mcr", "ADMIN") is True

    def test_false_without_role(self) -> None:
        claims = _generate_fake_claims(resource_access={"mcr": {"roles": ["USER"]}})
        assert claims.has_client_role("mcr", "ADMIN") is False

    def test_false_when_client_absent(self) -> None:
        assert _generate_fake_claims().has_client_role("mcr", "ADMIN") is False


class TestTokenClaimsValidation:
    def test_missing_email_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TokenClaims.model_validate({"sub": str(uuid.uuid4())})

    def test_ignores_unknown_claims(self) -> None:
        claims = _generate_fake_claims(iat=123, scope="openid profile")
        assert claims.email == "ada@example.com"


class TestToUserCreate:
    def test_maps_claims(self) -> None:
        sub = uuid.uuid4()
        user_create = _to_user_create(_generate_fake_claims(sub=str(sub)))
        assert user_create.keycloak_uuid == sub
        assert user_create.first_name == "Ada"
        assert user_create.last_name == "Lovelace"
        assert user_create.email == "ada@example.com"

    def test_defaults_names_when_absent(self) -> None:
        claims = TokenClaims.model_validate(
            {"sub": str(uuid.uuid4()), "email": "grace@example.com"}
        )
        user_create = _to_user_create(claims)
        assert user_create.first_name == ""
        assert user_create.last_name == ""

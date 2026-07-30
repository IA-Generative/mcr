from mcr_meeting.app.infrastructure.unleash import FeatureFlag
from tests.api.conftest import PrefixedTestClient
from tests.mocks.in_memory_feature_flags import InMemoryFeatureFlagClient


def test_get_feature_flag_status_enabled(
    feature_flag_client: PrefixedTestClient,
    feature_flags: InMemoryFeatureFlagClient,
) -> None:
    # Arrange
    feature_flags.enable(FeatureFlag.SPELLING_CORRECTION)

    # Act
    response = feature_flag_client.get(f"/{FeatureFlag.SPELLING_CORRECTION}")

    # Assert
    assert response.status_code == 200
    assert response.json() is True
    assert feature_flags.calls == [FeatureFlag.SPELLING_CORRECTION]


def test_get_feature_flag_status_disabled(
    feature_flag_client: PrefixedTestClient,
    feature_flags: InMemoryFeatureFlagClient,
) -> None:
    # Arrange
    feature_flags.disable(FeatureFlag.SPELLING_CORRECTION)

    # Act
    response = feature_flag_client.get(f"/{FeatureFlag.SPELLING_CORRECTION}")

    # Assert
    assert response.status_code == 200
    assert response.json() is False
    assert feature_flags.calls == [FeatureFlag.SPELLING_CORRECTION]


def test_get_unknown_feature_flag_is_rejected(
    feature_flag_client: PrefixedTestClient,
    feature_flags: InMemoryFeatureFlagClient,
) -> None:
    # Act
    response = feature_flag_client.get("/not_a_real_flag")

    # Assert
    assert response.status_code == 422
    assert feature_flags.calls == []

from unittest.mock import Mock

from ..conftest import PrefixedTestClient


def test_get_feature_flag_status_enabled(
    feature_flag_client: PrefixedTestClient,
    mock_feature_flag_client: Mock,
) -> None:
    # Arrange
    mock_feature_flag_client.is_enabled.return_value = True

    # Act
    response = feature_flag_client.get("/my_flag")

    # Assert
    assert response.status_code == 200
    assert response.json() is True
    mock_feature_flag_client.is_enabled.assert_called_once_with("my_flag")


def test_get_feature_flag_status_disabled(
    feature_flag_client: PrefixedTestClient,
    mock_feature_flag_client: Mock,
) -> None:
    # Arrange
    mock_feature_flag_client.is_enabled.return_value = False

    # Act
    response = feature_flag_client.get("/other_flag")

    # Assert
    assert response.status_code == 200
    assert response.json() is False
    mock_feature_flag_client.is_enabled.assert_called_once_with("other_flag")

from fastapi import APIRouter, Depends

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.services.feature_flag_service import (
    FeatureFlagClient,
    get_feature_flag_client,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.FEATURE_FLAG_API_PREFIX,
    tags=["Feature Flags"],
)


@router.get("/{feature_flag_name}")
def get_feature_flag_status(
    feature_flag_name: str,
    feature_flag_client: FeatureFlagClient = Depends(get_feature_flag_client),
) -> bool:
    """
    Get the status of a feature flag.

    Args:
        feature_flag_name (str): The name of the feature flag to test.

    Returns:
        bool: The status of the feature flag.

    """
    return feature_flag_client.is_enabled(feature_flag_name)

from fastapi import APIRouter

from mcr_meeting.app.configs.base import ApiSettings
from mcr_meeting.app.use_cases.get_feature_flag_status import (
    get_feature_flag_status as get_feature_flag_status_use_case,
)

api_settings = ApiSettings()
router = APIRouter(
    prefix=api_settings.FEATURE_FLAG_API_PREFIX,
    tags=["Feature Flags"],
)


@router.get("/{feature_flag_name}")
def get_feature_flag_status(feature_flag_name: str) -> bool:
    """
    Get the status of a feature flag.

    Args:
        feature_flag_name (str): The name of the feature flag to test.

    Returns:
        bool: The status of the feature flag.

    """
    return get_feature_flag_status_use_case(feature_flag_name)

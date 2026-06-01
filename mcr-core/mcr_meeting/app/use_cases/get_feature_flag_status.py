from mcr_meeting.app.infrastructure.unleash import is_enabled


def get_feature_flag_status(feature_flag_name: str) -> bool:
    return is_enabled(feature_flag_name)

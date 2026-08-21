from mcr_meeting.app.infrastructure.unleash import FeatureFlag, is_enabled


def get_feature_flag_status(feature_flag_name: FeatureFlag) -> bool:
    return is_enabled(feature_flag_name)

"""
Unleash feature flag service module.

This module provides a centralized way to manage Unleash feature flags
throughout the application using dependency injection.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional

from UnleashClient import UnleashClient

from mcr_meeting.app.configs.base import Settings, UnleashSettings


class FeatureFlag(StrEnum):
    """Centralized enum for all feature flag names in the application."""

    AUDIO_NOISE_FILTERING = "audio_noise_filtering"
    API_BASED_TRANSCRIPTION = "api_based_transcription"


class FeatureFlagClient(ABC):
    """Abstract interface for feature flag clients."""

    @abstractmethod
    def is_enabled(self, feature_flag_name: str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            feature_flag_name: The name of the feature flag to check.

        Returns:
            True if the feature flag is enabled, False otherwise.
        """
        pass


class UnleashFeatureFlagClient(FeatureFlagClient):
    """Adapter that wraps UnleashClient to implement FeatureFlagClient interface."""

    def __init__(self, unleash_client: UnleashClient) -> None:
        """
        Initialize the adapter with an UnleashClient instance.

        Args:
            unleash_client: The UnleashClient instance to wrap.
        """
        self._unleash_client = unleash_client

    def is_enabled(self, feature_flag_name: str) -> bool:
        """
        Check if a feature flag is enabled using the underlying UnleashClient.

        Args:
            feature_flag_name: The name of the feature flag to check.

        Returns:
            True if the feature flag is enabled, False otherwise.
        """
        return self._unleash_client.is_enabled(feature_flag_name)


class FeatureFlagSingleton:
    _instance: Optional["FeatureFlagSingleton"] = None
    _feature_flag_client: Optional[FeatureFlagClient] = None

    def __new__(cls) -> "FeatureFlagSingleton":
        if cls._instance is None:
            cls._instance = super(FeatureFlagSingleton, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the feature flag client."""
        unleash_settings = UnleashSettings()
        settings = Settings()
        unleash_client = UnleashClient(
            url=unleash_settings.UNLEASH_URL,
            app_name=settings.ENV_MODE,
            instance_id=unleash_settings.UNLEASH_INSTANCE_ID,
        )
        unleash_client.initialize_client()
        self._feature_flag_client = UnleashFeatureFlagClient(unleash_client)

    def get_feature_flag_client(self) -> FeatureFlagClient:
        """Get the feature flag client instance."""
        if self._feature_flag_client is None:
            raise RuntimeError(
                "Feature flag client is not initialized. Call initialize() first."
            )
        return self._feature_flag_client


def get_feature_flag_client() -> FeatureFlagClient:
    """Get the feature flag client instance."""
    return FeatureFlagSingleton().get_feature_flag_client()

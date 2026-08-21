from mcr_meeting.app.infrastructure.unleash import FeatureFlag, FeatureFlagClient


class InMemoryFeatureFlagClient(FeatureFlagClient):
    """Feature flag client backed by a dict, recording every lookup.

    Unknown flags are disabled, mirroring Unleash's behaviour.
    """

    def __init__(self, **flags: bool) -> None:
        self.calls: list[str] = []
        self._flags: dict[str, bool] = {
            str(name): value for name, value in flags.items()
        }
        self._error: Exception | None = None

    def fail_with(self, error: Exception) -> "InMemoryFeatureFlagClient":
        """Make every lookup raise, as an unreachable Unleash would."""
        self._error = error
        return self

    def enable(self, *flags: FeatureFlag | str) -> "InMemoryFeatureFlagClient":
        for flag in flags:
            self._flags[str(flag)] = True
        return self

    def disable(self, *flags: FeatureFlag | str) -> "InMemoryFeatureFlagClient":
        for flag in flags:
            self._flags[str(flag)] = False
        return self

    def is_enabled(self, feature_flag_name: str) -> bool:
        self.calls.append(str(feature_flag_name))
        if self._error is not None:
            raise self._error
        return self._flags.get(str(feature_flag_name), False)

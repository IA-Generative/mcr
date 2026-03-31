class InMemoryKeycloak:
    def __init__(
        self,
        exchange_refresh_token: str = "fake-refresh-token",
        refreshed_access_token: str = "fake-access-token",
        rotated_refresh_token: str | None = None,
    ) -> None:
        self.exchange_refresh_token = exchange_refresh_token
        self.refreshed_access_token = refreshed_access_token
        self.rotated_refresh_token = rotated_refresh_token
        self.should_fail_exchange = False
        self.should_fail_refresh = False

    def exchange_token(self, token: str, **kwargs: object) -> dict[str, str]:
        if self.should_fail_exchange:
            raise Exception("Token exchange failed")
        return {
            "refresh_token": self.exchange_refresh_token,
            "access_token": self.refreshed_access_token,
        }

    def refresh_token(self, refresh_token: str) -> dict[str, str]:
        if self.should_fail_refresh:
            raise Exception("Token refresh failed")
        result: dict[str, str] = {"access_token": self.refreshed_access_token}
        result["refresh_token"] = self.rotated_refresh_token or refresh_token
        return result

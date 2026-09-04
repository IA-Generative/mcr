class InMemoryRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expiries: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        if ex is not None:
            self.expiries[key] = ex

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.expiries.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.store

    def incr(self, key: str) -> int:
        value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(value)
        return value

    def expire(self, key: str, seconds: int) -> None:
        if key in self.store:
            self.expiries[key] = seconds

    def ttl(self, key: str) -> int:
        if key not in self.store:
            return -2
        return self.expiries.get(key, -1)

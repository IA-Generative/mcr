class InMemoryDriveClient:
    def __init__(self, url: str = "https://drive.example.com/documents/42/") -> None:
        self.url = url
        self.should_fail = False

    def __call__(self, access_token: str, filename: str, file_bytes: bytes) -> str:
        if self.should_fail:
            raise Exception("Drive upload failed")
        return self.url

from dataclasses import dataclass


@dataclass
class SentEmail:
    to_email: str
    subject: str
    html: str


class InMemoryEmailClient:
    def __init__(self) -> None:
        self.sent: list[SentEmail] = []
        self.should_fail = False

    def __call__(
        self,
        to_email: str,
        subject: str,
        html: str,
        max_retries: int = 3,
    ) -> bool:
        if self.should_fail:
            raise RuntimeError("Email send failed")
        self.sent.append(SentEmail(to_email=to_email, subject=subject, html=html))
        return True

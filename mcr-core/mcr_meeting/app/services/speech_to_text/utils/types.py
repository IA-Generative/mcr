from dataclasses import dataclass


@dataclass
class TimeSpan:
    """Small helper to reason about time intervals in seconds.

    Methods:
    - duration: length in seconds
    - overlaps: whether two spans overlap
    - overlap: amount of overlap in seconds
    """

    start: float
    end: float

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(
                f"Invalid TimeSpan with end < start ({self.start} > {self.end})"
            )

    @property
    def duration(self) -> float:
        return self.end - self.start

    def overlaps(self, other: "TimeSpan") -> bool:
        """Return True when the two spans overlap (non-empty intersection)."""
        return not (self.end <= other.start or self.start >= other.end)

    def overlap(self, other: "TimeSpan") -> float:
        """Return overlap length in seconds (0.0 when no overlap)."""
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return max(0.0, end - start)

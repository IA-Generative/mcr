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

    @property
    def midpoint(self) -> float:
        return (self.start + self.end) / 2.0

    def touches_or_overlaps(self, other: "TimeSpan") -> bool:
        """Return True when the two spans overlap or touch."""
        return not (self.end < other.start or self.start > other.end)

    def overlap(self, other: "TimeSpan") -> float:
        """Return overlap length in seconds (0.0 when no overlap)."""
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        return max(0.0, end - start)

    def merge(self, other: "TimeSpan") -> "TimeSpan":
        """Return a new TimeSpan covering both spans."""
        return TimeSpan(min(self.start, other.start), max(self.end, other.end))

    def gap_to(self, other: "TimeSpan") -> "TimeSpan | None":
        """Return the silence gap between self and other, or None if they overlap/touch."""
        if self.end >= other.start:
            return None
        return TimeSpan(self.end, other.start)

from celery.exceptions import Ignore


class MeetingDeletedException(Ignore):
    """Core returned 404: the meeting was deleted before the transition.
    Subclasses Ignore so the transcribe task ends cleanly without failing or
    retrying."""

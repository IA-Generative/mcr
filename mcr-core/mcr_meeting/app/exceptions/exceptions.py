"""
Custom exceptions for MCR Meeting.
"""


class MCRException(Exception):
    """Base exception for validation errors in MCR Meeting."""


class InvalidFileError(MCRException):
    """Raised when an invalid file is provided (a non-docx transcription for example)."""


class InvalidAudioFileError(MCRException):
    """Raised when an invalid audio file is provided."""


class LLMCompletionError(MCRException):
    """Raised when an LLM completion fails (e.g. the model returns a malformed
    or invalid response after retries)."""


class SilentAudioError(MCRException):
    """Raised when the audio is silent or contains no meaningful audio content."""


class NoAudioFoundError(MCRException):
    """Raised when no audio files are found for a given meeting."""


class NotFoundException(MCRException):
    """Raised when a resource is not found."""


class BadRequestException(MCRException):
    """Raised when an inbound request fails a business rule (mapped to HTTP 400)."""


class InvalidEvaluationZipError(MCRException):
    """Raised when an ASR evaluation archive is corrupted or has an invalid
    structure (mapped to HTTP 400)."""


class NotSavedException(MCRException):
    """Raised when a resource is not saved."""


class TaskCreationException(MCRException):
    """Raised when a transcription task couldn't be created."""


class InvalidDataException(MCRException):
    """Raised when the database rejects a write because the client data violates
    a column constraint (e.g. a value longer than the column allows). Mapped to
    HTTP 422. See raise_db_write_error."""


class DataConflictException(MCRException):
    """Raised when the database rejects a write because the client data violates
    a table constraint (unique, foreign key, ...). Mapped to HTTP 409."""


class DeliverableConcurrentlyCreatedException(MCRException):
    """Raised when a concurrent INSERT trips the partial unique index that
    forbids more than one active deliverable per (meeting, type)."""


class ForbiddenAccessException(MCRException):
    """Raised when a user try to access a ressource they don't have rights to
    (e.g Admin resources or Resources possessed by others)"""


class MeetingMultipartException(MCRException):
    """Raised when the importation of an audio file fails."""


class DiarizationError(MCRException):
    """Raised when the diarization fails"""


class UnknownDiarizationStatus(MCRException):
    """Raised when the diarization job reports a status outside the contractual
    allow-list (pending/processing/completed/failed). Fail-loud: we never guess
    a non-contractual status."""


class TranscriptionError(MCRException):
    """Raised when the transcription fails"""


class DeliverableStateConflictException(MCRException):
    """Raised when a state-machine transition is rejected because the deliverable
    is not in an allowed source state (mapped to HTTP 409)."""


class MeetingStateConflictException(MCRException):
    """Raised when a meeting transition is rejected because the meeting is not in
    an allowed source state (mapped to HTTP 409)."""


class TransientInfraError(MCRException):
    """Transient network/infra error — trigger local retry (tenacity) and task level retry."""


class S3TransientError(TransientInfraError):
    """Transient S3 error"""

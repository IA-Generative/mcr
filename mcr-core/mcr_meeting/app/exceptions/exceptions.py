"""
Custom exceptions for MCR Meeting.
"""


class MCRException(Exception):
    """Base exception for validation errors in MCR Meeting."""


class InvalidFileError(MCRException):
    """Raised when an invalid file is provided (a non-docx transcription for example)."""


class InvalidAudioFileError(MCRException):
    """Raised when an invalid audio file is provided."""


class SilentAudioError(MCRException):
    """Raised when the audio is silent or contains no meaningful audio content."""


class NoAudioFoundError(MCRException):
    """Raised when no audio files are found for a given meeting."""


class NotFoundException(MCRException):
    """Raised when a resource is not found."""


class BadRequestException(MCRException):
    """Raised when an inbound request fails a business rule (mapped to HTTP 400)."""


class NotSavedException(MCRException):
    """Raised when a resource is not saved."""


class TaskCreationException(MCRException):
    """Raised when a transcription task couldn't be created."""


class ForbiddenAccessException(MCRException):
    """Raised when a user try to access a ressource they don't have rights to
    (e.g Admin resources or Resources possessed by others)"""


class MeetingMultipartException(MCRException):
    """Raised when the importation of an audio file fails."""


class DiarizationError(MCRException):
    """Raised when the diarization fails"""


class TranscriptionError(MCRException):
    """Raised when the transcription fails"""

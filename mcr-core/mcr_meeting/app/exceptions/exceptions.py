"""
Custom exceptions for MCR Meeting.
"""


class MCRException(Exception):
    """Base exception for validation errors in MCR Meeting."""


class InvalidAudioFileError(MCRException):
    """Raised when an invalid audio file is provided."""


class NotFoundException(MCRException):
    """Raised when a resource is not found."""


class NotSavedException(MCRException):
    """Raised when a resource is not saved."""


class TaskCreationException(MCRException):
    """Raised when a transcription task couldn't be created."""


class ForbiddenAccessException(MCRException):
    """Raised when a user try to access a ressource they don't have rights to
    (e.g Admin resources or Resources possessed by others)"""


class MeetingMultipartException(MCRException):
    """Raised when the importation of an audio file fails."""

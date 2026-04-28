"""
Custom exceptions for MCR Generation.
"""


class MCRGenerationException(Exception):
    """Base exception for mcr-generation."""


class TranscriptionFileNotFoundError(MCRGenerationException):
    """Raised when the transcription DOCX is not found in S3."""


class InvalidTranscriptionFileError(MCRGenerationException):
    """Raised when the transcription DOCX cannot be parsed or chunked."""


class LLMCallError(MCRGenerationException):
    """Raised when a structured-output LLM call fails."""


class ReportCallbackError(MCRGenerationException):
    """Raised when posting the generated report back to mcr-core fails."""


class UnsupportedReportTypeError(MCRGenerationException):
    """Raised when an unknown report type is requested."""


class AllChunksFailedError(MCRGenerationException):
    """Raised when every chunk failed during map phase, leaving no content to reduce."""

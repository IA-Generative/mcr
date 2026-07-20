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


class DeliverableNotYetVisibleError(ReportCallbackError):
    """Raised when mcr-core returns 404 on in_progress: the deliverable row is
    not committed yet (send_task ran inside the transaction). Triggers a retry."""


class DeliverableNotYetPendingError(ReportCallbackError):
    """Raised when mcr-core returns 425 on in_progress: the deliverable is still
    REQUESTED (the drain has not committed its dispatch to PENDING yet). Triggers
    a retry, unlike the terminal 409 raised once it is already past PENDING."""


class UnsupportedReportTypeError(MCRGenerationException):
    """Raised when an unknown report type is requested."""


class AllChunksFailedError(MCRGenerationException):
    """Raised when every chunk failed during map phase, leaving no content to reduce."""


class EmptyChunksError(MCRGenerationException):
    """Raised when a pipeline is invoked with no chunks to process."""


class MissingCustomPromptError(MCRGenerationException):
    """Raised when a CUSTOM_REPORT is requested without a user-provided prompt."""

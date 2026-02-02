from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    """
    Schema for creating a new notification.

    Attributes:
        recipient_id (str): User ID to receive notification.
        title (str): Notification title, max length 255 characters.
        content (str): Notification content/message.
        type (str): Notification type, must be one of: info, warning, error, success.
        link (str | None): Optional link associated with the notification, max length 500 characters.
    """

    recipient_id: str = Field(..., description="User ID to receive notification")
    title: str = Field(..., max_length=255)
    content: str = Field(...)
    type: str = Field("info", pattern="^(info|warning|error|success)$")
    link: str | None = Field(None, max_length=500)


class NotificationResponse(BaseModel):
    """
    Schema for notification response.

    Attributes:
        id (str): Unique identifier for the notification.
        title (str): Notification title.
        content (str): Notification content/message.
        type (str): Notification type.
        read (bool): Whether the notification has been read.
        link (str | None): Optional link associated with the notification.
        timestamp (int): Unix timestamp of when the notification was created.
    """

    id: str
    title: str
    content: str
    type: str
    read: bool
    link: str | None
    timestamp: int

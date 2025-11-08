from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class NotificationCategory(str, Enum):
    REMINDER = "reminder"     # blue
    LOW_STOCK = "low_stock"   # red
    EVENT_SOON = "event_soon" # blue (informational)


class Notification(BaseModel):
    id: str = Field(..., description="Stable identifier for the notification")
    category: NotificationCategory = Field(..., description="Notification type/category")
    title: str = Field(..., description="Short title")
    message: str = Field(..., description="Detailed message")
    due_at: datetime = Field(..., description="When the notification is relevant (e.g., dose time)")
    color: str = Field(..., description="UI color token, e.g., 'blue' or 'red'")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Arbitrary metadata for FE actions")



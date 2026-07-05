# Copyright 2026 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import json
from datetime import datetime as DateTime
from typing import Any
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import SecretStr
from pydantic import field_validator
from pydantic import model_validator


class StrictModel(BaseModel):
  """Base model with strict validation and assignment checks."""

  model_config = ConfigDict(strict=True, validate_assignment=True, extra="forbid", from_attributes=True)

  @model_validator(mode="before")
  @classmethod
  def normalize_database_row(cls, data: object) -> object:
    """Decode SQLite row values before strict model validation."""

    if not isinstance(data, dict):
      return data

    normalized = dict(data)

    for key, value in list(normalized.items()):
      if key in {"tags", "attendees", "reminders"} and isinstance(value, str):
        normalized[key] = json.loads(value)

      if key in {"acknowledged", "read_status"} and isinstance(value, int):
        normalized[key] = bool(value)

      if (key.endswith("_at") or key.endswith("_datetime") or key in {"datetime", "timestamp"}) and isinstance(
        value, str
      ):
        normalized[key] = DateTime.fromisoformat(value)

    return normalized


def new_id() -> str:
  """Create a stable string identifier."""

  return str(uuid4())


def clean_tags(tags: list[str]) -> list[str]:
  """Normalize grouping/filtering tags for storage and search."""

  normalized: list[str] = []

  for tag in tags:
    value = tag.strip().lower()

    if value and value not in normalized:
      normalized.append(value)

  return normalized


class Alert(StrictModel):
  id: str = Field(default_factory=new_id, description="Unique identifier for the alert.")
  title: str = Field(..., min_length=1, max_length=200, description="Alert title.")
  message: str = Field(..., min_length=1, description="Detailed alert message.")
  severity: Literal["info", "warning", "critical"] = Field(..., description="Alert severity level.")
  timestamp: DateTime = Field(default_factory=DateTime.now, description="When the alert was created.")
  source: str | None = Field(None, max_length=100, description="Source of the alert.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for alerts, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )
  acknowledged: bool = Field(default=False, description="Whether the alert has been acknowledged.")
  acknowledged_at: DateTime | None = Field(None, description="When the alert was acknowledged.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class AlertCreate(StrictModel):
  title: str = Field(..., min_length=1, max_length=200, description="Alert title.")
  message: str = Field(..., min_length=1, description="Detailed alert message.")
  severity: Literal["info", "warning", "critical"] = Field(..., description="Alert severity level.")
  source: str | None = Field(None, max_length=100, description="Source of the alert.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for alerts, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class Reminder(StrictModel):
  id: str = Field(default_factory=new_id, description="Unique identifier for the reminder.")
  title: str = Field(..., min_length=1, max_length=200, description="Reminder title.")
  description: str | None = Field(None, max_length=500, description="Detailed reminder description.")
  datetime: DateTime = Field(..., description="When the reminder should trigger.")
  recurring: Literal["none", "daily", "weekly", "monthly"] = Field(default="none", description="Recurring frequency.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for reminders, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )
  status: Literal["pending", "completed", "dismissed"] = Field(default="pending", description="Current status.")
  created_at: DateTime = Field(default_factory=DateTime.now, description="When the reminder was created.")
  notified_at: DateTime | None = Field(None, description="When the notification was sent.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class ReminderCreate(StrictModel):
  title: str = Field(..., min_length=1, max_length=200, description="Reminder title.")
  description: str | None = Field(None, max_length=500, description="Detailed reminder description.")
  datetime: DateTime = Field(..., description="When the reminder should trigger.")
  recurring: Literal["none", "daily", "weekly", "monthly"] = Field(default="none", description="Recurring frequency.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for reminders, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class ReminderUpdate(StrictModel):
  title: str | None = Field(None, min_length=1, max_length=200, description="Updated reminder title.")
  description: str | None = Field(None, max_length=500, description="Updated reminder description.")
  datetime: DateTime | None = Field(None, description="Updated reminder trigger time.")
  recurring: Literal["none", "daily", "weekly", "monthly"] | None = Field(None, description="Updated recurrence.")
  tags: list[str] | None = Field(
    None,
    description=(
      "Updated client grouping and filtering tags for the reminder, such as device identifiers, UUIDs, "
      "source labels, or workflow names."
    ),
  )
  status: Literal["pending", "completed", "dismissed"] | None = Field(None, description="Updated status.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
    return clean_tags(value) if value is not None else None


class Event(StrictModel):
  id: str = Field(default_factory=new_id, description="Unique identifier for the event.")
  title: str = Field(..., min_length=1, max_length=200, description="Event title.")
  description: str | None = Field(None, max_length=500, description="Event description.")
  start_datetime: DateTime = Field(..., description="Event start date and time.")
  end_datetime: DateTime = Field(..., description="Event end date and time.")
  location: str | None = Field(None, max_length=200, description="Event location.")
  attendees: list[str] = Field(default_factory=list, description="List of attendee names or emails.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for events, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )
  reminders: list[int] = Field(default_factory=lambda: [15, 30, 60], description="Reminder offsets in minutes.")
  status: Literal["scheduled", "ongoing", "completed", "cancelled"] = Field(
    default="scheduled",
    description="Status.",
  )
  created_at: DateTime = Field(default_factory=DateTime.now, description="When the event was created.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)

  @model_validator(mode="after")
  def validate_dates(self) -> "Event":
    if self.end_datetime <= self.start_datetime:
      raise ValueError("end_datetime must be after start_datetime")
    return self


class EventCreate(StrictModel):
  title: str = Field(..., min_length=1, max_length=200, description="Event title.")
  description: str | None = Field(None, max_length=500, description="Event description.")
  start_datetime: DateTime = Field(..., description="Event start date and time.")
  end_datetime: DateTime = Field(..., description="Event end date and time.")
  location: str | None = Field(None, max_length=200, description="Event location.")
  attendees: list[str] = Field(default_factory=list, description="List of attendee names or emails.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for events, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )
  reminders: list[int] = Field(default_factory=lambda: [15, 30, 60], description="Reminder offsets in minutes.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)

  @model_validator(mode="after")
  def validate_dates(self) -> "EventCreate":
    if self.end_datetime <= self.start_datetime:
      raise ValueError("end_datetime must be after start_datetime")

    return self


class EventUpdate(StrictModel):
  title: str | None = Field(None, min_length=1, max_length=200, description="Updated event title.")
  description: str | None = Field(None, max_length=500, description="Updated event description.")
  start_datetime: DateTime | None = Field(None, description="Updated event start date and time.")
  end_datetime: DateTime | None = Field(None, description="Updated event end date and time.")
  location: str | None = Field(None, max_length=200, description="Updated event location.")
  attendees: list[str] | None = Field(None, description="Updated attendee names or emails.")
  tags: list[str] | None = Field(
    None,
    description=(
      "Updated client grouping and filtering tags for events, such as device identifiers, UUIDs, "
      "source labels, or workflow names."
    ),
  )
  reminders: list[int] | None = Field(None, description="Updated reminder offsets in minutes.")
  status: Literal["scheduled", "ongoing", "completed", "cancelled"] | None = Field(
    None,
    description="Updated status.",
  )

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
    return clean_tags(value) if value is not None else None


class Notification(StrictModel):
  id: str = Field(default_factory=new_id, description="Unique identifier for the notification.")
  type: Literal["alert", "reminder", "event"] = Field(..., description="Type of notification.")
  message: str = Field(..., min_length=1, description="Notification message.")
  entity_id: str = Field(..., description="ID of the related entity.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags for notifications, such as device identifiers, UUIDs, source labels, "
      "or workflow names."
    ),
  )
  timestamp: DateTime = Field(default_factory=DateTime.now, description="When the notification was created.")
  read_status: bool = Field(default=False, description="Whether the notification has been read.")
  read_at: DateTime | None = Field(None, description="When the notification was read.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class AgentAction(StrictModel):
  action_type: Literal[
    "create_reminder",
    "create_event",
    "update_item",
    "query",
    "list",
    "search_by_tags",
    "none",
  ] = Field(..., description="Type of action to perform.")

  entity_type: Literal["reminder", "event", "alert", "none"] = Field(..., description="Type of entity to act upon.")
  data: dict[str, Any] = Field(default_factory=dict, description="Structured data for the action.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags to apply to the action or resulting entity, such as device "
      "identifiers, UUIDs, source labels, or workflow names."
    ),
  )
  response_message: str = Field(..., description="Human-friendly response to the user.")
  requires_confirmation: bool = Field(default=False, description="Whether the action requires user confirmation.")
  confidence_score: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score of intent detection.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class AgentChatRequest(StrictModel):
  message: str = Field(..., min_length=1, max_length=2000, description="Natural language message for the agent.")
  context: dict[str, Any] = Field(default_factory=dict, description="Optional user context such as timezone.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Optional client grouping and filtering tags for the chat request, such as device identifiers, UUIDs, "
      "source labels, or workflow names."
    ),
  )

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class CalDAVAccount(StrictModel):
  id: str = Field(default_factory=new_id, description="Unique identifier for the CalDAV account.")
  name: str = Field(..., min_length=1, max_length=200, description="Human-friendly account name.")
  base_url: str = Field(..., min_length=1, max_length=500, description="CalDAV server base URL.")
  calendar_url: str = Field(..., min_length=1, max_length=500, description="CalDAV calendar collection URL.")
  username: str = Field(..., min_length=1, max_length=200, description="CalDAV username.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags used to decide which events are synchronized "
      "through this CalDAV account."
    ),
  )
  is_active: bool = Field(default=True, description="Whether the CalDAV account is currently active.")
  sync_token: str | None = Field(None, description="Last CalDAV sync token, when supported by the server.")
  last_synced_at: DateTime | None = Field(None, description="When the account was last synchronized.")
  last_sync_error: str | None = Field(None, max_length=2000, description="Last sync error message, if any.")
  created_at: DateTime = Field(default_factory=DateTime.now, description="When the account was created.")
  updated_at: DateTime = Field(default_factory=DateTime.now, description="When the account was last updated.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class CalDAVAccountCreate(StrictModel):
  name: str = Field(..., min_length=1, max_length=200, description="Human-friendly account name.")
  base_url: str = Field(..., min_length=1, max_length=500, description="CalDAV server base URL.")
  calendar_url: str = Field(..., min_length=1, max_length=500, description="CalDAV calendar collection URL.")
  username: str = Field(..., min_length=1, max_length=200, description="CalDAV username.")
  password: SecretStr = Field(..., description="CalDAV password or application-specific token.")
  tags: list[str] = Field(
    default_factory=list,
    description=(
      "Client grouping and filtering tags used to decide which events are synchronized "
      "through this CalDAV account."
    ),
  )
  is_active: bool = Field(default=True, description="Whether the CalDAV account is currently active.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str]) -> list[str]:
    return clean_tags(value)


class CalDAVAccountUpdate(StrictModel):
  name: str | None = Field(None, min_length=1, max_length=200, description="Updated account name.")
  base_url: str | None = Field(None, min_length=1, max_length=500, description="Updated CalDAV server base URL.")
  calendar_url: str | None = Field(
    None,
    min_length=1,
    max_length=500,
    description="Updated CalDAV calendar collection URL.",
  )
  username: str | None = Field(None, min_length=1, max_length=200, description="Updated CalDAV username.")
  password: SecretStr | None = Field(None, description="Updated CalDAV password or token.")
  tags: list[str] | None = Field(
    None,
    description=(
      "Updated client grouping and filtering tags used to decide which events are synchronized "
      "through this CalDAV account."
    ),
  )
  is_active: bool | None = Field(None, description="Updated account activation state.")
  sync_token: str | None = Field(None, description="Updated CalDAV sync token.")
  last_synced_at: DateTime | None = Field(None, description="Updated synchronization timestamp.")
  last_sync_error: str | None = Field(None, max_length=2000, description="Updated sync error message.")

  @field_validator("tags")
  @classmethod
  def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
    return clean_tags(value) if value is not None else None


class CalDAVSyncResult(StrictModel):
  account_id: str = Field(..., description="CalDAV account identifier.")
  event_id: str = Field(..., description="Local event identifier.")
  remote_uid: str | None = Field(None, description="Remote CalDAV UID.")
  remote_href: str | None = Field(None, description="Remote CalDAV resource URL.")
  etag: str | None = Field(None, description="Remote entity tag.")
  status: Literal["synced", "deleted", "skipped", "failed"] = Field(..., description="Sync outcome.")
  message: str | None = Field(None, description="Additional sync details or error message.")

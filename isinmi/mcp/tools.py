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
from datetime import datetime as DateTime
from typing import Literal

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from isinmi.core.models import CalDAVAccount
from isinmi.core.models import CalDAVSyncResult
from isinmi.core.models import Event
from isinmi.core.models import EventCreate
from isinmi.core.models import EventUpdate
from isinmi.core.models import Notification
from isinmi.core.models import Reminder
from isinmi.core.models import ReminderCreate
from isinmi.core.models import ReminderUpdate


READ_ONLY = ToolAnnotations(readOnlyHint=True, idempotentHint=True)


def register_mcp_tools(mcp: FastMCP, app: FastAPI) -> None:
  """Register MCP tools that expose reminder, event, and notification operations."""

  # --- Reminders Tools ---

  @mcp.tool()
  async def create_reminder(
    title: str,
    datetime: DateTime,
    description: str | None = None,
    recurring: Literal["none", "daily", "weekly", "monthly"] = "none",
    tags: list[str] | None = None,
  ) -> Reminder:
    """Create a new reminder.

    Args:
      title: The title of the reminder.
      datetime: The date and time when the reminder should trigger.
      description: Optional details about the reminder.
      recurring: Reoccurrence frequency: 'none', 'daily', 'weekly', or 'monthly'.
      tags: Optional list of tags for grouping/filtering.
    """
    service = app.state.reminder_service
    payload = ReminderCreate(
      title=title,
      datetime=datetime,
      description=description,
      recurring=recurring,
      tags=tags or [],
    )
    try:
      return await service.create(payload)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(annotations=READ_ONLY)
  async def list_reminders(
    status: Literal["pending", "completed", "dismissed"] | None = None,
    start: DateTime | None = None,
    end: DateTime | None = None,
    tags: list[str] | None = None,
    upcoming: bool = False,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Reminder]:
    """List reminders with optional filters.

    Args:
      status: Filter by status ('pending', 'completed', 'dismissed').
      start: Only reminders triggering at or after this date/time.
      end: Only reminders triggering at or before this date/time.
      tags: Filter by tags (all tags must match).
      upcoming: If true, lists pending reminders for the next 24 hours.
      limit: Maximum number of reminders to return.
      offset: Number of reminders to skip.
    """
    service = app.state.reminder_service
    try:
      return await service.list(
        status=status,
        start=start,
        end=end,
        tags=tags or [],
        upcoming=upcoming,
        limit=limit,
        offset=offset,
      )
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def update_reminder(
    reminder_id: str,
    title: str | None = None,
    description: str | None = None,
    datetime: DateTime | None = None,
    recurring: Literal["none", "daily", "weekly", "monthly"] | None = None,
    tags: list[str] | None = None,
    status: Literal["pending", "completed", "dismissed"] | None = None,
  ) -> Reminder:
    """Update an existing reminder.

    Args:
      reminder_id: ID of the reminder to update.
      title: New title.
      description: New description.
      datetime: New trigger time.
      recurring: New recurrence frequency.
      tags: New tag list.
      status: New status.
    """
    service = app.state.reminder_service
    update_data = {}
    if title is not None:
      update_data["title"] = title
    if description is not None:
      update_data["description"] = description
    if datetime is not None:
      update_data["datetime"] = datetime
    if recurring is not None:
      update_data["recurring"] = recurring
    if tags is not None:
      update_data["tags"] = tags
    if status is not None:
      update_data["status"] = status
    payload = ReminderUpdate(**update_data)
    try:
      return await service.update(reminder_id, payload)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def complete_reminder(reminder_id: str) -> Reminder:
    """Mark a reminder as completed.

    Args:
      reminder_id: ID of the reminder to complete.
    """
    service = app.state.reminder_service
    try:
      return await service.complete(reminder_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def delete_reminder(reminder_id: str) -> dict[str, str]:
    """Delete a reminder.

    Args:
      reminder_id: ID of the reminder to delete.
    """
    service = app.state.reminder_service
    try:
      return await service.delete(reminder_id)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- Events Tools ---

  @mcp.tool()
  async def create_event(
    title: str,
    start_datetime: DateTime,
    end_datetime: DateTime,
    description: str | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    tags: list[str] | None = None,
    reminders: list[int] | None = None,
  ) -> Event:
    """Create a new calendar event.

    Args:
      title: Title of the event.
      start_datetime: Start date and time.
      end_datetime: End date and time.
      description: Optional description.
      location: Optional location.
      attendees: Optional list of attendee names or emails.
      tags: Optional tags for grouping.
      reminders: Optional reminder offsets in minutes (e.g. [15, 30, 60]).
    """
    service = app.state.event_service
    payload_args = {
      "title": title,
      "start_datetime": start_datetime,
      "end_datetime": end_datetime,
      "description": description,
      "location": location,
      "attendees": attendees or [],
      "tags": tags or [],
    }
    if reminders is not None:
      payload_args["reminders"] = reminders
    try:
      payload = EventCreate(**payload_args)
      return await service.create(payload)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(annotations=READ_ONLY)
  async def get_event(event_id: str) -> Event:
    """Retrieve detailed information about a specific event.

    Args:
      event_id: ID of the event.
    """
    service = app.state.event_service
    try:
      return await service.get(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(annotations=READ_ONLY)
  async def list_events(
    status: Literal["scheduled", "ongoing", "completed", "cancelled"] | None = None,
    start: DateTime | None = None,
    end: DateTime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Event]:
    """List calendar events with optional filters.

    Args:
      status: Filter by status ('scheduled', 'ongoing', 'completed', 'cancelled').
      start: Only events starting at or after this date/time.
      end: Only events starting at or before this date/time.
      tags: Filter by tags (all tags must match).
      limit: Maximum number of events to return.
      offset: Number of events to skip.
    """
    service = app.state.event_service
    try:
      return await service.list(
        status=status,
        start=start,
        end=end,
        tags=tags or [],
        limit=limit,
        offset=offset,
      )
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def update_event(
    event_id: str,
    title: str | None = None,
    description: str | None = None,
    start_datetime: DateTime | None = None,
    end_datetime: DateTime | None = None,
    location: str | None = None,
    attendees: list[str] | None = None,
    tags: list[str] | None = None,
    reminders: list[int] | None = None,
    status: Literal["scheduled", "ongoing", "completed", "cancelled"] | None = None,
  ) -> Event:
    """Update an existing event.

    Args:
      event_id: ID of the event to update.
      title: New title.
      description: New description.
      start_datetime: New start time.
      end_datetime: New end time.
      location: New location.
      attendees: New attendee list.
      tags: New tag list.
      reminders: New reminder offsets.
      status: New status.
    """
    service = app.state.event_service
    update_data = {}
    if title is not None:
      update_data["title"] = title
    if description is not None:
      update_data["description"] = description
    if start_datetime is not None:
      update_data["start_datetime"] = start_datetime
    if end_datetime is not None:
      update_data["end_datetime"] = end_datetime
    if location is not None:
      update_data["location"] = location
    if attendees is not None:
      update_data["attendees"] = attendees
    if tags is not None:
      update_data["tags"] = tags
    if reminders is not None:
      update_data["reminders"] = reminders
    if status is not None:
      update_data["status"] = status
    payload = EventUpdate(**update_data)
    try:
      return await service.update(event_id, payload)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def delete_event(event_id: str) -> dict[str, str]:
    """Delete a calendar event.

    Args:
      event_id: ID of the event to delete.
    """
    service = app.state.event_service
    try:
      return await service.delete(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- Notifications Tools ---

  @mcp.tool(annotations=READ_ONLY)
  async def list_notifications(
    type: Literal["reminder", "event"] | None = None,
    tags: list[str] | None = None,
    read_status: bool | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Notification]:
    """List notification messages with optional filters.

    Args:
      type: Filter by type ('reminder', 'event').
      tags: Filter by tags (all tags must match).
      read_status: Filter by read status (True/False).
      limit: Maximum records to return.
      offset: Number of records to skip.
    """
    service = app.state.notification_service
    try:
      return await service.list(
        type_=type,
        tags=tags or [],
        read_status=read_status,
        limit=limit,
        offset=offset,
      )
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(annotations=READ_ONLY)
  async def get_unread_count() -> dict[str, int]:
    """Get the number of unread notifications."""
    service = app.state.notification_service
    try:
      return await service.unread_count()
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def mark_notification_read(notification_id: str) -> Notification:
    """Mark a single notification as read.

    Args:
      notification_id: ID of the notification to mark read.
    """
    service = app.state.notification_service
    try:
      return await service.mark_read(notification_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def mark_all_notifications_read(tags: list[str] | None = None) -> dict[str, int | str]:
    """Mark all notifications as read, optionally filtered by tags.

    Args:
      tags: Optional tags to limit the scope of the read operation.
    """
    service = app.state.notification_service
    try:
      return await service.mark_all_read(tags)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- CalDAV Tools ---

  @mcp.tool(annotations=READ_ONLY)
  async def list_caldav_accounts(active_only: bool = False) -> list[CalDAVAccount]:
    """List registered CalDAV calendar accounts.

    Args:
      active_only: If true, only returns active accounts.
    """
    service = app.state.caldav_service
    try:
      return await service.list_accounts(active_only=active_only)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def sync_event_to_caldav(event_id: str) -> list[CalDAVSyncResult]:
    """Synchronize a local event with configured CalDAV accounts.

    Args:
      event_id: ID of the local event to sync.
    """
    service = app.state.caldav_service
    try:
      return await service.sync_event(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool()
  async def sync_all_events_to_caldav(tags: list[str] | None = None) -> list[CalDAVSyncResult]:
    """Synchronize multiple local events with CalDAV, optionally filtered by tags.

    Args:
      tags: Optional tags to filter local events.
    """
    service = app.state.caldav_service
    try:
      return await service.sync_events(tags)
    except Exception as exc:
      raise ToolError(str(exc))

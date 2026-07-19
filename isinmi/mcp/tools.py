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

  @mcp.tool(
    title="Create Reminder",
    description="Create a new reminder."
  )
  async def create_reminder(
    title: str,
    datetime: DateTime,
    description: str | None = None,
    recurring: Literal["none", "daily", "weekly", "monthly"] = "none",
    tags: list[str] | None = None,
  ) -> Reminder:
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

  @mcp.tool(
    annotations=READ_ONLY,
    title="List Reminders",
    description="List reminders with optional filters."
  )
  async def list_reminders(
    status: Literal["pending", "completed", "dismissed"] | None = None,
    start: DateTime | None = None,
    end: DateTime | None = None,
    tags: list[str] | None = None,
    upcoming: bool = False,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Reminder]:
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

  @mcp.tool(
    title="Update Reminder",
    description="Update an existing reminder."
  )
  async def update_reminder(
    reminder_id: str,
    title: str | None = None,
    description: str | None = None,
    datetime: DateTime | None = None,
    recurring: Literal["none", "daily", "weekly", "monthly"] | None = None,
    tags: list[str] | None = None,
    status: Literal["pending", "completed", "dismissed"] | None = None,
  ) -> Reminder:
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

  @mcp.tool(
    title="Complete Reminder",
    description="Mark a reminder as completed."
  )
  async def complete_reminder(reminder_id: str) -> Reminder:
    service = app.state.reminder_service
    try:
      return await service.complete(reminder_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    title="Delete Reminder",
    description="Delete a reminder."
  )
  async def delete_reminder(reminder_id: str) -> dict[str, str]:
    service = app.state.reminder_service
    try:
      return await service.delete(reminder_id)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- Events Tools ---

  @mcp.tool(
    title="Create Event",
    description="Create a new calendar event."
  )
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

  @mcp.tool(
    annotations=READ_ONLY,
    title="Get Event",
    description="Retrieve detailed information about a specific event."
  )
  async def get_event(event_id: str) -> Event:
    service = app.state.event_service
    try:
      return await service.get(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    annotations=READ_ONLY,
    title="List Events",
    description="List calendar events with optional filters."
  )
  async def list_events(
    status: Literal["scheduled", "ongoing", "completed", "cancelled"] | None = None,
    start: DateTime | None = None,
    end: DateTime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Event]:
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

  @mcp.tool(
    title="Update Event",
    description="Update an existing event."
  )
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

  @mcp.tool(
    title="Delete Event",
    description="Delete a calendar event."
  )
  async def delete_event(event_id: str) -> dict[str, str]:
    service = app.state.event_service
    try:
      return await service.delete(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- Notifications Tools ---

  @mcp.tool(
    annotations=READ_ONLY,
    title="List Notifications",
    description="List notification messages with optional filters."
  )
  async def list_notifications(
    type: Literal["reminder", "event"] | None = None,
    tags: list[str] | None = None,
    read_status: bool | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Notification]:
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

  @mcp.tool(
    annotations=READ_ONLY,
    title="Get Unread Count",
    description="Get the number of unread notifications."
  )
  async def get_unread_count() -> dict[str, int]:
    service = app.state.notification_service
    try:
      return await service.unread_count()
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    title="Mark Notification Read",
    description="Mark a single notification as read."
  )
  async def mark_notification_read(notification_id: str) -> Notification:
    service = app.state.notification_service
    try:
      return await service.mark_read(notification_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    title="Mark All Notifications Read",
    description="Mark all notifications as read, optionally filtered by tags."
  )
  async def mark_all_notifications_read(tags: list[str] | None = None) -> dict[str, int | str]:
    service = app.state.notification_service
    try:
      return await service.mark_all_read(tags)
    except Exception as exc:
      raise ToolError(str(exc))

  # --- CalDAV Tools ---

  @mcp.tool(
    annotations=READ_ONLY,
    title="List CalDAV Accounts",
    description="List registered CalDAV calendar accounts."
  )
  async def list_caldav_accounts(active_only: bool = False) -> list[CalDAVAccount]:
    service = app.state.caldav_service
    try:
      return await service.list_accounts(active_only=active_only)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    title="Sync Event to CalDAV",
    description="Synchronize a local event with configured CalDAV accounts."
  )
  async def sync_event_to_caldav(event_id: str) -> list[CalDAVSyncResult]:
    service = app.state.caldav_service
    try:
      return await service.sync_event(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.tool(
    title="Sync All Events to CalDAV",
    description="Synchronize multiple local events with CalDAV, optionally filtered by tags."
  )
  async def sync_all_events_to_caldav(tags: list[str] | None = None) -> list[CalDAVSyncResult]:
    service = app.state.caldav_service
    try:
      return await service.sync_events(tags)
    except Exception as exc:
      raise ToolError(str(exc))

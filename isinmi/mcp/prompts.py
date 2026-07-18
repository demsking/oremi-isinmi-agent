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
from typing import Annotated
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field


def register_mcp_prompts(mcp: FastMCP) -> None:
  """Register MCP prompts for user task coordination and guidance."""

  @mcp.prompt()
  def schedule_day_plan(
    date: Annotated[
      str,
      Field(description="The target date to plan for in YYYY-MM-DD format (e.g., 2026-07-18)."),
    ],
    timezone: Annotated[
      str | None,
      Field(description="Optional user timezone to adjust datetime display or parsing."),
    ] = None,
  ) -> list[dict[str, Any]]:
    """Assist the user in organizing and planning a specific day."""
    tz_str = f" in timezone {timezone}" if timezone else ""
    return [
      {
        "role": "user",
        "content": (
          f"Please help me organize and review my schedule for the date {date}{tz_str}.\n\n"
          "Follow these steps to assist me:\n"
          "1. Use `list_events` and `list_reminders` tools to fetch all scheduled events and reminders for this day.\n"
          "2. Present the retrieved events and reminders in a clean, chronological timeline.\n"
          "3. Highlight any time conflicts (overlapping events) or tight schedules.\n"
          "4. Suggest modifications or ask if I need to schedule new reminders or events to cover gaps."
        ),
      }
    ]

  @mcp.prompt()
  def create_event_draft(
    title: Annotated[
      str,
      Field(description="The title of the event."),
    ],
    start_time: Annotated[
      str,
      Field(description="The start time of the event in ISO 8601 format (e.g. YYYY-MM-DDTHH:MM:SS)."),
    ],
    duration_minutes: Annotated[
      int,
      Field(description="The duration of the event in minutes."),
    ] = 60,
    location: Annotated[
      str | None,
      Field(description="Optional location of the event."),
    ] = None,
  ) -> list[dict[str, Any]]:
    """Draft a new calendar event with reminders and attendees."""
    loc_str = f" at {location}" if location else ""
    return [
      {
        "role": "user",
        "content": (
          f"I want to schedule an event titled '{title}' starting at {start_time} for {duration_minutes} minutes{loc_str}.\n\n"
          "Please perform the following actions:\n"
          "1. Calculate the end date/time based on the start time and duration.\n"
          "2. Propose a complete event creation payload (including title, start_datetime, end_datetime, location, and a list of reminder offsets like [15, 30, 60]).\n"
          "3. Ask for confirmation or any missing details (such as description or attendees) before calling the `create_event` tool."
        ),
      }
    ]

  @mcp.prompt()
  def manage_unread_alerts() -> list[dict[str, Any]]:
    """Review and manage unread notifications and alerts."""
    return [
      {
        "role": "user",
        "content": (
          "I want to check and manage my unread notifications and alerts.\n\n"
          "Please follow these instructions:\n"
          "1. Call `get_unread_count` to find out how many unread alerts exist.\n"
          "2. If there are unread alerts, call `list_notifications` with `read_status=False` to fetch the details.\n"
          "3. Present the notifications to me, categorized by type (reminder/event) and ordered by timestamp.\n"
          "4. Offer to mark them all as read using `mark_all_notifications_read`, or mark individual ones as read."
        ),
      }
    ]

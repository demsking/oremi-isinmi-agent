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
"""MCP integration tests."""
import importlib.util
import json
from datetime import datetime
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from isinmi import create_app
from isinmi.core.models import Event
from isinmi.core.models import Notification
from isinmi.core.models import Reminder

pytestmark = pytest.mark.skipif(
  importlib.util.find_spec("sqlcipher3") is None,
  reason="sqlcipher3 is not installed",
)


def parse_tool_result(res, model_class=None):
  """Helper to parse FastMCP tool output based on its return format."""
  if isinstance(res, tuple):
    _, structured = res
    if model_class:
      if "result" in structured:
        return [model_class.model_validate(item) for item in structured["result"]]
      else:
        return model_class.model_validate(structured)
    return structured
  else:
    text = res[0].text
    try:
      data = json.loads(text)
      if model_class and isinstance(data, list):
        return [model_class.model_validate(item) for item in data]
      elif model_class and isinstance(data, dict):
        return model_class.model_validate(data)
      return data
    except json.JSONDecodeError:
      return text


@pytest.mark.asyncio
async def test_mcp_http_endpoint_and_tools() -> None:
  app = create_app()

  with TestClient(app):
    # Verify the HTTP mount endpoint is present
    assert any(getattr(route, "path", None) == "/mcp" for route in app.routes)

    tools = await app.state.mcp.list_tools()

    # Verify the tools are registered
    tool_names = {tool.name for tool in tools}
    assert "create_reminder" in tool_names
    assert "list_reminders" in tool_names
    assert "create_event" in tool_names
    assert "list_events" in tool_names
    assert "list_notifications" in tool_names
    assert "get_unread_count" in tool_names


@pytest.mark.asyncio
async def test_mcp_reminder_tools_and_resources() -> None:
  app = create_app()
  mcp = app.state.mcp

  with TestClient(app):
    rem_time = datetime.now() + timedelta(hours=2)

    # 1. Create Reminder
    res = await mcp.call_tool(
      "create_reminder",
      {
        "title": "MCP Test Reminder",
        "datetime": rem_time.isoformat(),
        "description": "Created via MCP tool",
        "tags": ["mcp-test"],
      },
    )
    reminder = parse_tool_result(res, Reminder)
    assert isinstance(reminder, Reminder)
    assert reminder.title == "MCP Test Reminder"
    reminder_id = reminder.id

    # 2. List Reminders
    res = await mcp.call_tool("list_reminders", {"tags": ["mcp-test"]})
    reminders = parse_tool_result(res, Reminder)
    assert len(reminders) == 1
    assert reminders[0].id == reminder_id

    # 3. Read Resource
    contents = await mcp.read_resource(f"reminders:///{reminder_id}")
    assert len(contents) == 1
    data = json.loads(contents[0].content)
    assert data["title"] == "MCP Test Reminder"

    # 4. Update Reminder
    res = await mcp.call_tool(
      "update_reminder",
      {
        "reminder_id": reminder_id,
        "description": "Updated description",
      },
    )
    updated = parse_tool_result(res, Reminder)
    assert updated.description == "Updated description"

    # 5. Complete Reminder
    res = await mcp.call_tool("complete_reminder", {"reminder_id": reminder_id})
    completed = parse_tool_result(res, Reminder)
    assert completed.status == "completed"

    # 6. Delete Reminder
    res = await mcp.call_tool("delete_reminder", {"reminder_id": reminder_id})
    result = parse_tool_result(res)
    assert result == {"status": "deleted"}


@pytest.mark.asyncio
async def test_mcp_event_tools_and_resources() -> None:
  app = create_app()
  mcp = app.state.mcp

  with TestClient(app):
    start = datetime.now() + timedelta(hours=1)
    end = start + timedelta(hours=1)

    # 1. Create Event
    res = await mcp.call_tool(
      "create_event",
      {
        "title": "MCP Test Event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "location": "Online",
        "tags": ["mcp-event"],
      },
    )
    event = parse_tool_result(res, Event)
    assert isinstance(event, Event)
    assert event.title == "MCP Test Event"
    event_id = event.id

    # 2. Get Event Tool
    res = await mcp.call_tool("get_event", {"event_id": event_id})
    event_fetched = parse_tool_result(res, Event)
    assert event_fetched.id == event_id

    # 3. Read Resource
    contents = await mcp.read_resource(f"events:///{event_id}")
    assert len(contents) == 1
    data = json.loads(contents[0].content)
    assert data["title"] == "MCP Test Event"

    # 4. List Events
    res = await mcp.call_tool("list_events", {"tags": ["mcp-event"]})
    events = parse_tool_result(res, Event)
    assert len(events) == 1
    assert events[0].id == event_id

    # 5. Update Event
    res = await mcp.call_tool(
      "update_event",
      {
        "event_id": event_id,
        "title": "Updated MCP Event",
      },
    )
    updated = parse_tool_result(res, Event)
    assert updated.title == "Updated MCP Event"

    # 6. Delete Event
    res = await mcp.call_tool("delete_event", {"event_id": event_id})
    result = parse_tool_result(res)
    assert result == {"status": "deleted"}


@pytest.mark.asyncio
async def test_mcp_notification_tools_and_resources() -> None:
  app = create_app()
  mcp = app.state.mcp

  with TestClient(app):
    # Create a reminder to trigger a notification
    rem_time = datetime.now() + timedelta(hours=2)
    res = await mcp.call_tool(
      "create_reminder",
      {
        "title": "Notification Trigger Reminder",
        "datetime": rem_time.isoformat(),
        "tags": ["notification-test"],
      },
    )
    reminder = parse_tool_result(res, Reminder)

    # 1. Unread count
    res = await mcp.call_tool("get_unread_count", {})
    result = parse_tool_result(res)
    assert result["count"] >= 1

    # 2. List notifications
    res = await mcp.call_tool("list_notifications", {"tags": ["notification-test"]})
    notifications = parse_tool_result(res, Notification)
    assert len(notifications) == 1
    notif_id = notifications[0].id

    # 3. Read Resource
    contents = await mcp.read_resource(f"notifications:///{notif_id}")
    assert len(contents) == 1
    data = json.loads(contents[0].content)
    assert data["entity_id"] == reminder.id

    # 4. Mark notification read
    res = await mcp.call_tool("mark_notification_read", {"notification_id": notif_id})
    notif = parse_tool_result(res, Notification)
    assert notif.read_status is True

    # 5. Mark all read
    res = await mcp.call_tool("mark_all_notifications_read", {"tags": ["notification-test"]})
    result = parse_tool_result(res)
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_mcp_prompts() -> None:
  app = create_app()
  mcp = app.state.mcp

  # 1. schedule_day_plan prompt
  res = await mcp.get_prompt("schedule_day_plan", {"date": "2026-07-18"})
  assert len(res.messages) == 1
  assert "2026-07-18" in res.messages[0].content.text

  # 2. create_event_draft prompt
  res = await mcp.get_prompt(
    "create_event_draft",
    {
      "title": "Planning",
      "start_time": "2026-07-18T10:00:00",
    },
  )
  assert len(res.messages) == 1
  assert "Planning" in res.messages[0].content.text

  # 3. manage_unread_alerts prompt
  res = await mcp.get_prompt("manage_unread_alerts", {})
  assert len(res.messages) == 1
  assert "unread notifications" in res.messages[0].content.text

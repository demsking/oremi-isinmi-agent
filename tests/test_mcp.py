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

  with TestClient(app, backend="asyncio") as client:
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    tools = data["result"]["tools"]

    tool_names = [tool["name"] for tool in tools]

    assert "create_reminder" in tool_names
    assert "list_reminders" in tool_names
    assert "create_event" in tool_names
    assert "list_events" in tool_names
    assert "list_notifications" in tool_names
    assert "get_unread_count" in tool_names


@pytest.mark.asyncio
async def test_mcp_prompts() -> None:
  app = create_app()

  with TestClient(app, backend="asyncio") as client:
    # 1. List prompts
    payload = {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    prompts = data["result"]["prompts"]
    prompt_names = [p["name"] for p in prompts]
    assert "schedule_day_plan" in prompt_names
    assert "create_event_draft" in prompt_names
    assert "manage_unread_alerts" in prompt_names

    # 2. Get schedule_day_plan with timezone
    payload = {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "prompts/get",
      "params": {
        "name": "schedule_day_plan",
        "arguments": {
          "date": "2026-07-18",
          "timezone": "Europe/Paris",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    messages = data["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    content_text = messages[0]["content"]["text"]
    assert "2026-07-18" in content_text
    assert "timezone Europe/Paris" in content_text

    # 3. Get schedule_day_plan without timezone
    payload = {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "prompts/get",
      "params": {
        "name": "schedule_day_plan",
        "arguments": {
          "date": "2026-07-18",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    messages = data["result"]["messages"]
    content_text = messages[0]["content"]["text"]
    assert "timezone" not in content_text

    # 4. Get create_event_draft with all arguments
    payload = {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "prompts/get",
      "params": {
        "name": "create_event_draft",
        "arguments": {
          "title": "Dentist Appointment",
          "start_time": "2026-07-19T14:30:00",
          "duration_minutes": "45",
          "location": "Dental Clinic",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    messages = data["result"]["messages"]
    content_text = messages[0]["content"]["text"]
    assert "Dentist Appointment" in content_text
    assert "2026-07-19T14:30:00" in content_text
    assert "45 minutes" in content_text
    assert "at Dental Clinic" in content_text

    # 5. Get create_event_draft with defaults
    payload = {
      "jsonrpc": "2.0",
      "id": 5,
      "method": "prompts/get",
      "params": {
        "name": "create_event_draft",
        "arguments": {
          "title": "Quick Sync",
          "start_time": "2026-07-19T14:30:00",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    messages = data["result"]["messages"]
    content_text = messages[0]["content"]["text"]
    assert "Quick Sync" in content_text
    assert "60 minutes" in content_text
    assert "Dental Clinic" not in content_text

    # 6. Get manage_unread_alerts
    payload = {
      "jsonrpc": "2.0",
      "id": 6,
      "method": "prompts/get",
      "params": {
        "name": "manage_unread_alerts",
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    messages = data["result"]["messages"]
    content_text = messages[0]["content"]["text"]
    assert "get_unread_count" in content_text
    assert "list_notifications" in content_text



@pytest.mark.asyncio
async def test_mcp_resources() -> None:
  app = create_app()

  with TestClient(app, backend="asyncio") as client:
    # 1. List resource templates
    payload = {"jsonrpc": "2.0", "id": 1, "method": "resources/templates/list", "params": {}}
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    templates = data["result"]["resourceTemplates"]
    template_uris = [t["uriTemplate"] for t in templates]
    assert "reminders:///{reminder_id}" in template_uris
    assert "events:///{event_id}" in template_uris
    assert "notifications:///{notification_id}" in template_uris

    # 2. Add test data in database using services
    # Add a reminder
    reminder = Reminder(
      title="Buy milk",
      description="Pick up milk after work.",
      datetime=datetime.now() + timedelta(hours=2),
      tags=["device_id:phone-1"],
      notified_at=None,
    )
    saved_reminder = await app.state.reminder_service.create(reminder)

    # Add an event
    event = Event(
      title="Team sync",
      description="Weekly review.",
      start_datetime=datetime.now() + timedelta(days=1),
      end_datetime=datetime.now() + timedelta(days=1, hours=1),
      location=None,
      tags=["user_id:alex"],
    )
    saved_event = await app.state.event_service.create(event)

    # Get a notification (one was already created automatically during reminder/event creation)
    # Let's list notifications using repository to get a saved one
    notifications = await app.state.notification_service.repository.list_notifications(limit=10, offset=0)
    assert len(notifications) > 0
    saved_notification = notifications[0]

    # 3. Read reminder resource
    payload = {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "resources/read",
      "params": {"uri": f"reminders:///{saved_reminder.id}"},
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    contents = data["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["mimeType"] == "application/json"
    reminder_data = json.loads(contents[0]["text"])
    assert reminder_data["title"] == "Buy milk"

    # 4. Read event resource
    payload = {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "resources/read",
      "params": {"uri": f"events:///{saved_event.id}"},
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    contents = data["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["mimeType"] == "application/json"
    event_data = json.loads(contents[0]["text"])
    assert event_data["title"] == "Team sync"

    # 5. Read notification resource
    payload = {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "resources/read",
      "params": {"uri": f"notifications:///{saved_notification.id}"},
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    contents = data["result"]["contents"]
    assert len(contents) == 1
    assert contents[0]["mimeType"] == "application/json"
    notif_data = json.loads(contents[0]["text"])
    assert notif_data["id"] == saved_notification.id

    # 6. Read non-existent resources (expecting error)
    payload = {
      "jsonrpc": "2.0",
      "id": 5,
      "method": "resources/read",
      "params": {"uri": "reminders:///non-existent-id"},
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    # It should return a JSON-RPC error since ToolError/Exception is raised in the resource handler
    assert "error" in data or "result" not in data


@pytest.mark.asyncio
async def test_additional_mcp_prompts() -> None:
  app = create_app()

  with TestClient(app, backend="asyncio") as client:
    # 1. List prompts and verify all new prompts exist
    payload = {"jsonrpc": "2.0", "id": 1, "method": "prompts/list", "params": {}}
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    prompts = data["result"]["prompts"]
    prompt_names = [p["name"] for p in prompts]

    expected_prompts = [
      "set_reminder",
      "list_reminders",
      "find_reminder",
      "update_reminder",
      "complete_reminder",
      "postpone_reminder",
      "delete_reminder",
      "schedule_event",
      "list_events",
      "find_event",
      "update_event",
      "cancel_event",
      "find_free_time",
      "daily_agenda",
      "weekly_agenda",
      "schedule_recurring_reminder",
      "reminder_suggestions",
      "morning_briefing",
    ]

    for name in expected_prompts:
      assert name in prompt_names

    # 2. Test set_reminder
    payload = {
      "jsonrpc": "2.0",
      "id": 2,
      "method": "prompts/get",
      "params": {
        "name": "set_reminder",
        "arguments": {
          "title": "Buy groceries",
          "datetime": "2026-07-19T18:00:00",
          "description": "Get milk and bread",
          "recurring": "none",
          "tags": "shopping,home",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    content_text = data["result"]["messages"][0]["content"]["text"]
    assert "Buy groceries" in content_text
    assert "2026-07-19T18:00:00" in content_text
    assert "Get milk and bread" in content_text

    # 3. Test list_reminders
    payload = {
      "jsonrpc": "2.0",
      "id": 3,
      "method": "prompts/get",
      "params": {
        "name": "list_reminders",
        "arguments": {
          "status": "pending",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    content_text = data["result"]["messages"][0]["content"]["text"]
    assert "Here are the current matching reminders" in content_text

    # 4. Test find_free_time
    payload = {
      "jsonrpc": "2.0",
      "id": 4,
      "method": "prompts/get",
      "params": {
        "name": "find_free_time",
        "arguments": {
          "date": "2026-07-19",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    content_text = data["result"]["messages"][0]["content"]["text"]
    assert "Free time slots on 2026-07-19" in content_text

    # 5. Test reminder_suggestions
    payload = {
      "jsonrpc": "2.0",
      "id": 5,
      "method": "prompts/get",
      "params": {
        "name": "reminder_suggestions",
        "arguments": {
          "context": "health",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    content_text = data["result"]["messages"][0]["content"]["text"]
    assert "Suggestions for health" in content_text

    # 6. Test morning_briefing
    payload = {
      "jsonrpc": "2.0",
      "id": 6,
      "method": "prompts/get",
      "params": {
        "name": "morning_briefing",
        "arguments": {
          "date": "2026-07-19",
        },
      },
    }
    response = client.post("http://localhost:8080/mcp", json=payload, headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert "result" in data
    content_text = data["result"]["messages"][0]["content"]["text"]
    assert "briefing for 2026-07-19" in content_text

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
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from isinmi.core.models import Event
from isinmi.core.models import Notification
from isinmi.core.models import Reminder


def register_mcp_resources(mcp: FastMCP, app: FastAPI) -> None:
  """Register MCP resources for accessing reminder, event, and notification data directly."""

  @mcp.resource("reminders:///{reminder_id}", mime_type="application/json")
  async def get_reminder_resource(reminder_id: str) -> Reminder:
    """Retrieve detailed information about a specific reminder by ID."""
    service = app.state.reminder_service
    try:
      return await service.get(reminder_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.resource("events:///{event_id}", mime_type="application/json")
  async def get_event_resource(event_id: str) -> Event:
    """Retrieve detailed information about a specific calendar event by ID."""
    service = app.state.event_service
    try:
      return await service.get(event_id)
    except Exception as exc:
      raise ToolError(str(exc))

  @mcp.resource("notifications:///{notification_id}", mime_type="application/json")
  async def get_notification_resource(notification_id: str) -> Notification:
    """Retrieve detailed information about a specific notification by ID."""
    service = app.state.notification_service
    try:
      # Helper operation to load notification from SQLite
      def _operation(session):
        from isinmi.core.orm import NotificationORM

        return session.get(NotificationORM, notification_id)

      record = await service.repository.db.run(_operation)
      if not record:
        raise ToolError("Notification not found")
      return Notification.model_validate(record)
    except Exception as exc:
      raise ToolError(str(exc))

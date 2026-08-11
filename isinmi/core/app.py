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
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from mcp.server import MCPServer

from isinmi.api import caldav
from isinmi.api import docs
from isinmi.api import events
from isinmi.api import health
from isinmi.api import notifications
from isinmi.api import reminders
from isinmi.core.database import Database
from isinmi.core.package import APP_DOCUMENTATION_URL
from isinmi.core.package import APP_NAME
from isinmi.core.package import APP_VERSION
from isinmi.core.settings import get_settings
from isinmi.core.settings import log_group
from isinmi.core.settings import Settings
from isinmi.integrations.caldav.service import CalDAVSyncService
from isinmi.mcp.prompts import register_mcp_prompts
from isinmi.mcp.resources import register_mcp_resources
from isinmi.mcp.tools import register_mcp_tools
from isinmi.repositories.caldav_repository import CalDAVRepository
from isinmi.repositories.event_repository import EventRepository
from isinmi.repositories.notification_repository import NotificationRepository
from isinmi.repositories.reminder_repository import ReminderRepository
from isinmi.services.event_service import EventService
from isinmi.services.notification_service import NotificationService
from isinmi.services.reminder_service import ReminderService
from isinmi.sse.manager import SSEManager
from isinmi.utils.logger import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
  """Build the FastAPI application."""

  resolved_settings = settings or get_settings()
  configure_logging(resolved_settings.log_level, resolved_settings.log_file)

  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"{APP_NAME} v{APP_VERSION}")
    log_group(resolved_settings, "Server", "server_host", "server_port", "api_prefix")
    log_group(resolved_settings, "CalDAV", "caldav_request_timeout_seconds", "sse_retry_timeout_seconds")
    log_group(resolved_settings, "Database", "database_url", "database_encryption_key")
    log_group(resolved_settings, "Logging", "log_level", "log_file")

    db = Database(resolved_settings)

    await db.initialize()

    sse = SSEManager()
    notification_service = NotificationService(NotificationRepository(db), sse)
    reminder_service = ReminderService(ReminderRepository(db), notification_service)
    event_repository = EventRepository(db)
    caldav_repository = CalDAVRepository(db)

    app.state.settings = resolved_settings
    app.state.db = db
    app.state.sse_manager = sse
    app.state.notification_service = notification_service
    app.state.reminder_service = reminder_service
    app.state.event_service = EventService(event_repository, notification_service)
    app.state.caldav_service = CalDAVSyncService(
      caldav_repository,
      event_repository,
      resolved_settings.caldav_request_timeout_seconds,
    )

    app.state.event_service.set_caldav_sync_service(app.state.caldav_service)

    try:
      async with mcp.session_manager.run():
        yield
    finally:
      await db.dispose()

  app = FastAPI(
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title=APP_NAME,
    version=APP_VERSION,
    root_path=resolved_settings.api_prefix,
    servers=[
      {"url": resolved_settings.api_prefix},
    ],
    license_info={
      "name": "Apache 2.0",
      "url": "http://www.apache.org/licenses/LICENSE-2.0.html",
    },
    openapi_tags=[
      reminders.API_TAG_METADATA,
      events.API_TAG_METADATA,
      caldav.API_TAG_METADATA,
      notifications.API_TAG_METADATA,
      health.API_TAG_METADATA,
    ],
  )

  mcp = MCPServer(
    name="Oremi Isinmi",
    instructions=(
      "Expose AI-agent facing tools, resources, and prompts for reminders, events, notifications and calendar synchronization."
    ),
    website_url=APP_DOCUMENTATION_URL,
  )

  @app.exception_handler(Exception)
  async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})

  @app.get("/", include_in_schema=False)
  async def redirect_to_docs() -> HTMLResponse:
    return HTMLResponse(status_code=307, headers={"Location": prefix + docs.router.prefix + "/"})

  prefix = "" if resolved_settings.api_prefix == "/" else resolved_settings.api_prefix
  api_prefix = f"{prefix}/api"

  app.include_router(reminders.router, prefix=api_prefix)
  app.include_router(events.router, prefix=api_prefix)
  app.include_router(caldav.router, prefix=api_prefix)
  app.include_router(notifications.router, prefix=api_prefix)
  app.include_router(health.router, prefix=prefix)
  app.include_router(docs.router, prefix=prefix)

  app.mount(
    resolved_settings.api_prefix,
    mcp.streamable_http_app(
      stateless_http=True,
      json_response=True,
      streamable_http_path="/mcp",
    ),
    name="mcp",
  )

  register_mcp_tools(mcp, app)
  register_mcp_resources(mcp, app)
  register_mcp_prompts(mcp, app)

  return app

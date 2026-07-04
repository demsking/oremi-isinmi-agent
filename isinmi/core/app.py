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

import ollama
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP

from isinmi.api import agent
from isinmi.api import alerts
from isinmi.api import docs
from isinmi.api import events
from isinmi.api import health
from isinmi.api import notifications
from isinmi.api import reminders
from isinmi.core.database import Database
from isinmi.core.package import APP_DESCRIPTION
from isinmi.core.package import APP_NAME
from isinmi.core.package import APP_VERSION
from isinmi.core.settings import get_settings
from isinmi.core.settings import Settings
from isinmi.repositories.alert_repository import AlertRepository
from isinmi.repositories.event_repository import EventRepository
from isinmi.repositories.notification_repository import NotificationRepository
from isinmi.repositories.reminder_repository import ReminderRepository
from isinmi.services.agent_service import AgentService
from isinmi.services.alert_service import AlertService
from isinmi.services.event_service import EventService
from isinmi.services.notification_service import NotificationService
from isinmi.services.reminder_service import ReminderService
from isinmi.sse.manager import SSEManager
from isinmi.utils.logger import configure_logging

logger = logging.getLogger(__name__)


async def _pull_ollama_model(settings: Settings) -> None:
  """Pull configured Ollama model if enabled."""
  try:
    client = ollama.AsyncClient(host=settings.ollama_base_url, timeout=settings.llm_request_timeout)

    await client.pull(settings.resolve_ollama_model_name(), stream=False)
    logger.info(f"Ollama model ready: {settings.resolve_ollama_model_name()}")
  except Exception as exception:
    logger.warning(f"Could not pull Ollama model {settings.resolve_ollama_model_name()}: {exception}")


def create_app(settings: Settings | None = None) -> FastAPI:
  """Build the FastAPI application."""

  resolved_settings = settings or get_settings()
  configure_logging(resolved_settings.log_level, resolved_settings.log_file)

  @asynccontextmanager
  async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"{APP_NAME} v{APP_VERSION}")
    logger.info(f"Server: http://{resolved_settings.server_host}:{resolved_settings.server_port}")
    logger.info(f"API Docs: http://{resolved_settings.server_host}:{resolved_settings.server_port}/docs")
    logger.info("API Prefix: %s", resolved_settings.api_prefix)
    logger.info("LLM Model: %s", resolved_settings.llm_model)
    logger.info("LLM Request Timeout: %s", resolved_settings.llm_request_timeout)
    logger.info("LLM Temperature: %s", resolved_settings.llm_temperature)
    logger.info("LLM System Prompt: %s", resolved_settings.llm_system_prompt.replace("\n", " ").strip())
    logger.info("Ollama Base URL: %s", resolved_settings.ollama_base_url)
    logger.info("Database URL: %s", resolved_settings.database_url)
    logger.info("Database Encryption Key: [set]")
    logger.info("Log Level: %s", resolved_settings.log_level)
    logger.info("Log File: %s", resolved_settings.log_file)
    logger.info("SSE Retry Timeout: %s", resolved_settings.sse_retry_timeout)

    db = Database(resolved_settings)
    await db.initialize()

    sse = SSEManager()
    notification_service = NotificationService(NotificationRepository(db), sse)
    reminder_service = ReminderService(ReminderRepository(db), notification_service)

    app.state.settings = resolved_settings
    app.state.db = db
    app.state.sse_manager = sse
    app.state.notification_service = notification_service
    app.state.alert_service = AlertService(AlertRepository(db), notification_service)
    app.state.reminder_service = reminder_service
    app.state.event_service = EventService(EventRepository(db), notification_service)
    app.state.agent_service = AgentService(resolved_settings, db, reminder_service)

    if resolved_settings.uses_ollama():
      await _pull_ollama_model(resolved_settings)

    yield

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
      agent.API_TAG_METADATA,
      alerts.API_TAG_METADATA,
      reminders.API_TAG_METADATA,
      events.API_TAG_METADATA,
      notifications.API_TAG_METADATA,
      health.API_TAG_METADATA,
    ],
  )

  @app.exception_handler(Exception)
  async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": str(exc)})

  @app.get("/", include_in_schema=False)
  async def redirect_to_docs():
    return HTMLResponse(status_code=307, headers={"Location": docs.router.prefix})

  prefix = "" if resolved_settings.api_prefix == "/" else resolved_settings.api_prefix

  app.include_router(alerts.router, prefix=prefix)
  app.include_router(reminders.router, prefix=prefix)
  app.include_router(events.router, prefix=prefix)
  app.include_router(notifications.router, prefix=prefix)
  app.include_router(agent.router, prefix=prefix)
  app.include_router(health.router, prefix=prefix)
  app.include_router(docs.router, prefix=prefix)

  mcp = FastApiMCP(
    app,
    name=APP_NAME,
    description=APP_DESCRIPTION,
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_tags=[
      alerts.API_TAG_METADATA["name"],
      reminders.API_TAG_METADATA["name"],
      events.API_TAG_METADATA["name"],
      notifications.API_TAG_METADATA["name"],
    ],
    exclude_operations=events.MCP_EXCLUDED_OPERATIONS,
  )

  mcp.mount_http()
  app.state.mcp = mcp

  return app

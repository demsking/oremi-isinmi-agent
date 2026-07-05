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
from datetime import datetime
from typing import Any
from typing import cast

from fastapi import HTTPException
from pydantic import Field
from pydantic_ai import Agent
from pydantic_ai.agent import AgentModelSettings
from pydantic_ai.exceptions import UnexpectedModelBehavior

from ..core.database import Database
from ..core.models import AgentAction
from ..core.models import AgentChatRequest
from ..core.models import StrictModel
from ..core.models import clean_tags
from ..core.models import new_id
from ..core.models import ReminderCreate
from ..core.orm import AgentConversationORM
from ..core.settings import Settings
from ..services.event_service import EventService
from ..services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class AgentService:
  """Pydantic-AI based agent."""

  def __init__(
    self,
    settings: Settings,
    db: Database,
    reminders: ReminderService,
    events: EventService,
  ) -> None:
    self.settings = settings
    self.db = db
    self.reminders = reminders
    self.events = events
    self._agent = self._build_action_agent()
    self._response_agent = self._build_response_agent()

  def _build_action_agent(self):
    """Build an agent for the configured backend."""

    model_settings: AgentModelSettings = {
      "temperature": self.settings.llm_temperature,
      "thinking": False,
      "timeout": self.settings.llm_request_timeout,
    }

    if self.settings.uses_ollama():
      if not self.settings.ollama_base_url:
        raise RuntimeError("OREMI_ISINMI_OLLAMA_BASE_URL is required when llm_model uses ollama")

      from pydantic_ai.models.ollama import OllamaModel  # pylint: disable=import-outside-toplevel
      from pydantic_ai.providers.ollama import OllamaProvider  # pylint: disable=import-outside-toplevel

      return Agent(
        model=OllamaModel(
          self.settings.resolve_ollama_model_name(),
          provider=OllamaProvider(base_url=f"{self.settings.ollama_base_url}/v1"),
          settings=model_settings,
        ),
        system_prompt=self.settings.llm_system_prompt,
        output_type=AgentAction,
        model_settings=model_settings,
      )

    return Agent(
      model=self.settings.llm_model,
      system_prompt=self.settings.llm_system_prompt,
      output_type=AgentAction,
      model_settings=model_settings,
    )

  def _build_response_agent(self):
    """Build an agent dedicated to concise user-facing messages."""

    model_settings: AgentModelSettings = {
      "temperature": self.settings.llm_temperature,
      "thinking": False,
      "timeout": self.settings.llm_request_timeout,
    }

    return Agent(
      model=self._build_agent_model(),
      system_prompt=(
        "You write the final user-facing response_message for a personal assistant. "
        "Use only the provided structured action and result data. "
        "Keep the same language as the user when possible. "
        "Be concise, factual, and result-oriented. "
        "Do not ask follow-up questions unless the action truly cannot be completed. "
        "Return only the response text."
      ),
      output_type=AssistantResponse,
      model_settings=model_settings,
    )

  def _build_agent_model(self):
    """Return the configured LLM backend model."""

    if self.settings.uses_ollama():
      if not self.settings.ollama_base_url:
        raise RuntimeError("OREMI_ISINMI_OLLAMA_BASE_URL is required when llm_model uses ollama")

      from pydantic_ai.models.ollama import OllamaModel  # pylint: disable=import-outside-toplevel
      from pydantic_ai.providers.ollama import OllamaProvider  # pylint: disable=import-outside-toplevel

      return OllamaModel(
        self.settings.resolve_ollama_model_name(),
        provider=OllamaProvider(base_url=f"{self.settings.ollama_base_url}/v1"),
      )

    return self.settings.llm_model

  async def chat(self, request: AgentChatRequest) -> AgentAction:
    action = await self._run_action_agent(request)
    effective_tags = self._merge_tags(request.tags, action.tags, action.data.get("tags", []))

    action.tags = effective_tags
    result_payload = await self._resolve_action_result(action, effective_tags)

    if action.action_type == "create_reminder" and action.data.get("title") and action.data.get("datetime"):
      try:
        payload = ReminderCreate(
          title=str(action.data["title"]),
          description=action.data.get("description"),
          datetime=datetime.fromisoformat(str(action.data["datetime"])),
          recurring=action.data.get("recurring", "none"),
          tags=effective_tags,
        )

        reminder = await self.reminders.create(payload)
        action.data["id"] = reminder.id
        action.data["tags"] = effective_tags
        result_payload = self._serialize_value(reminder)
      except Exception as exc:
        logger.exception("Failed to materialize agent reminder")
        raise HTTPException(status_code=500, detail="Failed to create reminder from agent action") from exc

    action.response_message = await self._generate_response_message(request, action, result_payload)

    await self._save_conversation(request, action)

    return action

  async def _run_action_agent(self, request: AgentChatRequest) -> AgentAction:
    if self._agent is None:
      raise HTTPException(status_code=412, detail="LLM agent is not configured")

    try:
      result = await self._agent.run(request.message, deps=request.context)
      return result.output
    except UnexpectedModelBehavior as exc:
      logger.exception("Agent returned invalid structured output")
      raise HTTPException(
        status_code=502,
        detail="The language model returned an invalid structured response.",
      ) from exc
    except Exception as exc:
      logger.exception("Agent call failed")
      raise HTTPException(status_code=502, detail="LLM agent call failed") from exc

  async def _generate_response_message(
    self,
    request: AgentChatRequest,
    action: AgentAction,
    result_payload: Any,
  ) -> str:
    if self._response_agent is None:
      raise HTTPException(status_code=412, detail="LLM response generator is not configured")

    prompt = AssistantResponseRequest(
      request_message=request.message,
      request_context=request.context,
      request_tags=request.tags,
      action=action,
      result_payload=result_payload,
    )

    try:
      result = await self._response_agent.run(prompt.model_dump_json(indent=2, exclude_none=True))
      response = result.output.response_message.strip()
      if not response:
        raise ValueError("empty response message")
      return response
    except UnexpectedModelBehavior as exc:
      logger.exception("Response generator returned invalid output")
      raise HTTPException(
        status_code=502,
        detail="The language model returned an invalid response message.",
      ) from exc
    except Exception as exc:
      logger.exception("Response generation failed")
      raise HTTPException(status_code=502, detail="LLM response generation failed") from exc

  def _merge_tags(self, *tag_groups: object) -> list[str]:
    merged: list[str] = []

    for group in tag_groups:
      if isinstance(group, (list, tuple, set)):
        merged.extend(list(group))

    return clean_tags(merged)

  async def _resolve_action_result(self, action: AgentAction, tags: list[str]) -> Any:
    if action.action_type not in {"query", "list", "search_by_tags"}:
      return None

    if action.entity_type == "event":
      start, end = self._extract_datetime_range(action.data)
      status = self._extract_status(action.data)
      limit = self._extract_int(action.data, "limit", default=10)
      offset = self._extract_int(action.data, "offset", default=0)
      items = await self.events.list(status, start, end, tags, limit, offset)
      return [self._serialize_value(item) for item in items]

    if action.entity_type == "reminder":
      start, end = self._extract_datetime_range(action.data)
      status = self._extract_status(action.data)
      upcoming = bool(action.data.get("upcoming", False))
      limit = self._extract_int(action.data, "limit", default=10)
      offset = self._extract_int(action.data, "offset", default=0)
      items = await self.reminders.list(status, start, end, tags, upcoming, limit, offset)
      return [self._serialize_value(item) for item in items]

    return None

  def _extract_datetime_range(self, data: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    start = self._parse_datetime(data.get("start_datetime") or data.get("start"))
    end = self._parse_datetime(data.get("end_datetime") or data.get("end"))
    return start, end

  def _extract_status(self, data: dict[str, Any]) -> str | None:
    status = data.get("status")
    return str(status) if status else None

  def _extract_int(self, data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    try:
      return int(value)
    except (TypeError, ValueError):
      return default

  def _parse_datetime(self, value: object) -> datetime | None:
    if isinstance(value, datetime):
      return value

    if isinstance(value, str) and value:
      try:
        return datetime.fromisoformat(value)
      except ValueError:
        return None

    return None

  def _serialize_value(self, value: object) -> Any:
    if hasattr(value, "model_dump"):
      return cast(Any, value).model_dump()

    if isinstance(value, list):
      return [self._serialize_value(item) for item in value]

    if isinstance(value, dict):
      return {key: self._serialize_value(item) for key, item in value.items()}

    return value

  async def _save_conversation(self, request: AgentChatRequest, action: AgentAction) -> None:
    def _operation(session):
      session.add(
        AgentConversationORM(
          id=new_id(),
          message=request.message,
          response=action.response_message,
          action_type=action.action_type,
          entity_type=action.entity_type,
          tags=self._merge_tags(request.tags, action.tags),
          context=request.context,
          created_at=datetime.now(),
        )
      )

    await self.db.run(_operation)


class AssistantResponse(StrictModel):
  response_message: str = Field(..., min_length=1, description="Concise response generated by the LLM.")


class AssistantResponseRequest(StrictModel):
  request_message: str = Field(..., description="Original user request.")
  request_context: dict[str, Any] = Field(default_factory=dict, description="Original request context.")
  request_tags: list[str] = Field(default_factory=list, description="Original request tags.")
  action: AgentAction = Field(..., description="Structured action returned by the agent.")
  result_payload: Any = Field(default=None, description="Resolved data for the action.")

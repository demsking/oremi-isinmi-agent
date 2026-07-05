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

from pydantic_ai import Agent
from pydantic_ai.agent import AgentModelSettings
from fastapi import HTTPException

from ..core.database import Database
from ..core.models import AgentAction
from ..core.models import AgentChatRequest
from ..core.models import clean_tags
from ..core.models import new_id
from ..core.models import ReminderCreate
from ..core.orm import AgentConversationORM
from ..core.settings import Settings
from ..services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class AgentService:
  """Pydantic-AI based agent."""

  def __init__(self, settings: Settings, db: Database, reminders: ReminderService) -> None:
    self.settings = settings
    self.db = db
    self.reminders = reminders
    self._agent = self._build_agent()

  def _build_agent(self):
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

  async def chat(self, request: AgentChatRequest) -> AgentAction:
    action = await self._run_agent(request)
    effective_tags = self._merge_tags(request.tags, action.tags, action.data.get("tags", []))

    action.tags = effective_tags

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
      except Exception as exc:
        logger.exception("Failed to materialize agent reminder")

        action = AgentAction(
          action_type="none",
          entity_type="none",
          response_message=f"I understood the reminder, but could not save it: {exc}",
          confidence_score=0.2,
        )

    await self._save_conversation(request, action)

    return action

  async def _run_agent(self, request: AgentChatRequest) -> AgentAction:
    if self._agent is None:
      raise HTTPException(status_code=412, detail="LLM agent is not configured")

    try:
      result = await self._agent.run(request.message, deps=request.context)
      return result.output
    except Exception as exc:
      logger.exception("Agent call failed")
      raise HTTPException(status_code=502, detail="LLM agent call failed") from exc

  def _merge_tags(self, *tag_groups: object) -> list[str]:
    merged: list[str] = []

    for group in tag_groups:
      if isinstance(group, (list, tuple, set)):
        merged.extend(list(group))

    return clean_tags(merged)

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

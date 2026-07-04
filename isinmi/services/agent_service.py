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
import json
import logging
import re
from datetime import datetime
from datetime import timedelta

from pydantic_ai import Agent
from pydantic_ai.agent import AgentModelSettings

from isinmi.core.database import Database
from isinmi.core.database import json_dumps
from isinmi.core.models import AgentAction
from isinmi.core.models import AgentChatRequest
from isinmi.core.models import clean_tags
from isinmi.core.models import new_id
from isinmi.core.models import ReminderCreate
from isinmi.core.models import TagsRequest
from isinmi.core.settings import Settings
from isinmi.services.reminder_service import ReminderService

logger = logging.getLogger(__name__)


class AgentService:
  """Pydantic-AI based agent with a deterministic fallback."""

  def __init__(self, settings: Settings, db: Database, reminders: ReminderService) -> None:
    self.settings = settings
    self.db = db
    self.reminders = reminders
    self._agent = self._build_agent()

  def _build_agent(self):
    """Build an agent for the configured backend."""

    model_name = self.settings.resolve_ollama_model_name()
    model_settings: AgentModelSettings = {
      "temperature": self.settings.llm_temperature,
      "thinking": False,
      "timeout": self.settings.llm_request_timeout,
    }

    if self.settings.uses_ollama():
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
      model=model_name,
      system_prompt=self.settings.llm_system_prompt,
      output_type=AgentAction,
      model_settings=model_settings,
    )

  async def chat(self, request: AgentChatRequest) -> AgentAction:
    action = await self._run_agent(request)

    if action.action_type == "create_reminder" and action.data.get("title") and action.data.get("datetime"):
      try:
        payload = ReminderCreate(
          title=str(action.data["title"]),
          description=action.data.get("description"),
          datetime=datetime.fromisoformat(str(action.data["datetime"])),
          recurring=action.data.get("recurring", "none"),
          tags=clean_tags(action.tags or action.data.get("tags", [])),
        )

        reminder = await self.reminders.create(payload)
        action.data["id"] = reminder.id
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
    if self._agent is not None:
      try:
        result = await self._agent.run(request.message, deps=request.context)

        return result.output
      except Exception as exc:
        logger.warning("Agent call failed, using fallback parser: %s", exc)

    return self._fallback_parse(request)

  def _fallback_parse(self, request: AgentChatRequest) -> AgentAction:
    text = request.message.strip()
    lower = text.lower()
    tags = self.extract_tags(TagsRequest(text=text))

    if "remind me" in lower:
      title = re.sub(r"(?i)^.*?remind me to\s+", "", text)
      title = re.split(r"(?i)\s+(tomorrow|today|at|tag it as|label it as)\b", title)[0].strip(" ,.")
      when = self._rough_datetime(lower)

      return AgentAction(
        action_type="create_reminder",
        entity_type="reminder",
        data={"title": title or "Reminder", "datetime": when.isoformat(), "tags": tags},
        tags=tags,
        response_message=f"I created a reminder for {when:%Y-%m-%d %H:%M}.",
        confidence_score=0.65,
      )

    if any(word in lower for word in ["show", "list", "what"]):
      entity = "event" if "event" in lower else "reminder" if "reminder" in lower else "none"

      return AgentAction(
        action_type="search_by_tags" if tags else "list",
        entity_type=entity,
        tags=tags,
        response_message="I can search your saved items with those filters.",
        confidence_score=0.55,
      )

    return AgentAction(
      action_type="none",
      entity_type="none",
      tags=tags,
      response_message="I can help create reminders, schedule events, and search by tags.",
      confidence_score=0.4,
    )

  def _rough_datetime(self, lower: str) -> datetime:
    base = datetime.now().replace(second=0, microsecond=0)

    if "tomorrow" in lower:
      base += timedelta(days=1)

    hour_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", lower)

    if hour_match:
      hour = int(hour_match.group(1))
      minute = int(hour_match.group(2) or 0)
      marker = hour_match.group(3)

      if marker == "pm" and hour < 12:
        hour += 12

      if marker == "am" and hour == 12:
        hour = 0

      base = base.replace(hour=hour, minute=minute)

    return base

  def extract_tags(self, request: TagsRequest) -> list[str]:
    text = request.text.lower()
    tags: list[str] = []
    explicit = re.search(r"(?:tag|label)(?: it)? as ([a-z0-9, and_-]+)", text)

    if explicit:
      tags.extend(re.split(r",|\band\b", explicit.group(1)))

    for candidate in request.existing_tags + ["work", "urgent", "personal", "errands", "groceries", "meeting"]:
      if candidate.lower() in text:
        tags.append(candidate)

    return clean_tags(tags)

  async def suggestions(self) -> list[str]:
    upcoming = await self.reminders.upcoming()
    suggestions = ["Review unread notifications", "Tag related reminders for easier filtering"]

    if upcoming:
      suggestions.insert(0, f"You have {len(upcoming)} reminder(s) due in the next 24 hours")

    return suggestions

  async def _save_conversation(self, request: AgentChatRequest, action: AgentAction) -> None:
    await self.db.execute(
      """
      INSERT INTO agent_conversations
      (id, message, response, action_type, entity_type, tags, context, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      """,
      (
        new_id(),
        request.message,
        action.response_message,
        action.action_type,
        action.entity_type,
        json_dumps(action.tags),
        json.dumps(request.context, default=str),
        datetime.now().isoformat(),
      ),
    )

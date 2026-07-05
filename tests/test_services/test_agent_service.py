"""Agent service behavior tests."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic_ai.exceptions import UnexpectedModelBehavior

from isinmi.core.database import Database
from isinmi.core.models import AgentAction
from isinmi.core.models import AgentChatRequest
from isinmi.core.settings import Settings
from isinmi.services.agent_service import AgentService


class FakeEventService:
  def __init__(self) -> None:
    self.calls: list[tuple[str | None, object | None, object | None, list[str], int, int]] = []

  async def list(self, status, start, end, tags, limit, offset):  # noqa: ANN001
    self.calls.append((status, start, end, tags, limit, offset))
    return [
      {
        "id": "event-1",
        "title": "Brunch with Clara",
        "start_datetime": "2026-07-05T11:00:00",
        "end_datetime": "2026-07-05T12:00:00",
        "tags": ["family"],
      }
    ]


async def test_agent_chat_uses_concise_result_message_for_query(tmp_path: Path) -> None:
  db_path = tmp_path / "agent.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  await database.initialize()

  try:
    fake_events = FakeEventService()
    service = AgentService(settings, database, object(), fake_events)

    async def fake_run_agent(request: AgentChatRequest) -> AgentAction:
      return AgentAction(
        action_type="query",
        entity_type="event",
        data={
          "start_datetime": "2026-07-05T00:00:00",
          "end_datetime": "2026-07-07T23:59:59",
        },
        tags=[],
        response_message="ignored",
        requires_confirmation=False,
        confidence_score=0.8,
      )

    captured: dict[str, object] = {}

    async def fake_generate_response_message(request: AgentChatRequest, action: AgentAction, result_payload):
      captured["request"] = request.message
      captured["action"] = action.action_type
      captured["result_payload"] = result_payload
      return "Voici vos événements de ce week-end."

    service._run_action_agent = fake_run_agent  # type: ignore[method-assign]
    service._generate_response_message = fake_generate_response_message  # type: ignore[method-assign]

    action = await service.chat(
      AgentChatRequest(message="Quels événements ai-je ce week-end ?", context={"timezone": "Europe/Paris"})
    )

    assert action.response_message == "Voici vos événements de ce week-end."
    assert fake_events.calls[0][0] is None
    assert fake_events.calls[0][3] == []
    assert captured["action"] == "query"
    assert isinstance(captured["result_payload"], list)
    assert captured["result_payload"][0]["title"] == "Brunch with Clara"
  finally:
    await database.dispose()


async def test_agent_chat_handles_unexpected_model_behavior(tmp_path: Path) -> None:
  db_path = tmp_path / "agent_error.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  await database.initialize()

  try:
    service = AgentService(settings, database, object(), FakeEventService())

    class BrokenAgent:
      async def run(self, *_args, **_kwargs):
        raise UnexpectedModelBehavior("invalid tool call")

    service._agent = BrokenAgent()

    with pytest.raises(HTTPException) as exc_info:
      await service.chat(AgentChatRequest(message="Quels événements ai-je ce week-end ?"))

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "The language model returned an invalid structured response."
  finally:
    await database.dispose()

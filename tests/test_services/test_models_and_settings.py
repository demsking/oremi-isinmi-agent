"""Model and settings tests."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from isinmi.core.models import AlertCreate, AgentChatRequest, EventCreate
from isinmi.core.settings import Settings


def test_settings_requires_long_encryption_key() -> None:
  with pytest.raises(ValidationError):
    Settings(database_encryption_key="too-short")


def test_log_level_is_normalized() -> None:
  settings = Settings(database_encryption_key="x" * 32, log_level="DEBUG")
  assert settings.log_level == "DEBUG"


def test_default_llm_model_uses_ollama() -> None:
  settings = Settings(database_encryption_key="x" * 32)

  assert settings.llm_model == "ollama:qwen3.5:2b"
  assert settings.uses_ollama() is True
  assert settings.resolve_ollama_model_name() == "qwen3.5:2b"


def test_custom_llm_model_disables_ollama_backend() -> None:
  settings = Settings(database_encryption_key="x" * 32, llm_model="openai:gpt-4.1-mini")

  assert settings.llm_model == "openai:gpt-4.1-mini"
  assert settings.uses_ollama() is False


def test_llm_temperature_defaults_and_validates() -> None:
  settings = Settings(database_encryption_key="x" * 32)
  assert settings.llm_temperature == 0.3

  custom = Settings(database_encryption_key="x" * 32, llm_temperature=0.7)
  assert custom.llm_temperature == 0.7


def test_tags_are_normalized_and_deduplicated() -> None:
  alert = AlertCreate(title="CPU", message="High load", severity="warning", tags=[" Work ", "work", "URGENT"])
  assert alert.tags == ["work", "urgent"]


def test_agent_chat_request_accepts_client_grouping_tags() -> None:
  request = AgentChatRequest(
    message="Remind me tomorrow at 9 AM to call the dentist",
    tags=["Device:iPhone", "uuid:ABC-123", "device:iphone"],
  )

  assert request.tags == ["device:iphone", "uuid:abc-123"]


def test_event_end_must_be_after_start() -> None:
  start = datetime.now()
  with pytest.raises(ValidationError):
    EventCreate(title="Bad event", start_datetime=start, end_datetime=start - timedelta(minutes=1))

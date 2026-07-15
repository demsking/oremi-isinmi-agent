"""Model and settings tests."""

import logging
from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from isinmi.core.app import log_startup_settings
from isinmi.core.models import AgentChatRequest, EventCreate, ReminderCreate
from isinmi.core.settings import Settings


def test_settings_requires_long_encryption_key() -> None:
  with pytest.raises(ValidationError):
    Settings(database_encryption_key="too-short")


def test_log_level_is_normalized() -> None:
  settings = Settings(database_encryption_key="x" * 32, log_level="DEBUG")
  assert settings.log_level == "DEBUG"


def test_startup_logs_every_setting_without_exposing_secrets(caplog: pytest.LogCaptureFixture) -> None:
  secret = "secret-value-that-must-never-be-logged"
  settings = Settings(database_encryption_key=secret)

  with caplog.at_level(logging.INFO, logger="isinmi.core.app"):
    log_startup_settings(settings)

  output = caplog.text
  for name in Settings.model_fields:
    assert f"Setting {name}:" in output

  assert "Setting database_encryption_key: [set]" in output
  assert secret not in output


def test_tags_are_normalized_and_deduplicated() -> None:
  reminder = ReminderCreate(title="Call the dentist", datetime=datetime.now(), tags=[" Work ", "work", "URGENT"])
  assert reminder.tags == ["work", "urgent"]


def test_agent_chat_request_accepts_client_grouping_tags() -> None:
  request = AgentChatRequest(
    message="Remind me tomorrow at 9 AM to call the dentist",
    tags=["Device:IPhone", "user_id:ABC-123", "device_id:iphone"],
  )

  assert request.tags == ["device:iphone", "user_id:abc-123", "device_id:iphone"]


def test_event_end_must_be_after_start() -> None:
  start = datetime.now()
  with pytest.raises(ValidationError):
    EventCreate(title="Bad event", start_datetime=start, end_datetime=start - timedelta(minutes=1))

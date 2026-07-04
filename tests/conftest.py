"""Shared test setup."""

import os
from pathlib import Path

import pytest

os.environ.setdefault("OREMI_ISINMI_DATABASE_ENCRYPTION_KEY", "test-secret-key-with-at-least-32-chars")
os.environ.setdefault("OREMI_ISINMI_DATABASE_URL", "sqlite:///./data/test_oremi_isinmi.db")
os.environ.setdefault("OREMI_ISINMI_OLLAMA_BASE_URL", "http://localhost:21434")
os.environ.setdefault("OREMI_ISINMI_LLM_REQUEST_TIMEOUT", "30")
os.environ.setdefault("OREMI_ISINMI_LOG_FILE", "logs/test_oremi_isinmi.log")


@pytest.fixture(autouse=True)
def cleanup_test_db():
  yield
  Path("data/test_oremi_isinmi.db").unlink(missing_ok=True)

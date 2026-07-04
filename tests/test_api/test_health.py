"""API health tests."""

import importlib.util

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(importlib.util.find_spec("sqlcipher3") is None, reason="sqlcipher3 is not installed")


def test_health_endpoint() -> None:
  from isinmi.main import app

  with TestClient(app) as client:
    response = client.get("/health")

  assert response.status_code == 200
  assert response.json()["status"] == "ok"

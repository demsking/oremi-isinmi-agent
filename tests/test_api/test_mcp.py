"""MCP integration tests."""

import importlib.util

import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("sqlcipher3") is None, reason="sqlcipher3 is not installed")


def test_mcp_http_endpoint_and_tools() -> None:
  from isinmi.main import app

  assert any(getattr(route, "path", None) == "/mcp" for route in app.routes)

  tool_names = {tool.name for tool in app.state.mcp.tools}

  assert "create_alert" in tool_names
  assert "create_reminder" in tool_names
  assert "create_event" in tool_names

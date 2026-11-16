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
"""Deployment configuration tests."""

import re
from pathlib import Path

from isinmi.core.settings import Settings


DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _dockerfile() -> str:
  return DOCKERFILE.read_text(encoding="utf-8")


def _exposed_port() -> str:
  match = re.search(r"^EXPOSE\s+(?P<port>\d+)\s*$", _dockerfile(), re.MULTILINE)

  assert match is not None, "Dockerfile must expose the server port"

  return match.group("port")


def _healthcheck() -> str:
  match = re.search(r"^HEALTHCHECK(?:.*\\\n)*.*$", _dockerfile(), re.MULTILINE)

  assert match is not None, "Dockerfile must define a HEALTHCHECK"

  return match.group(0)


def test_image_defaults_match_application_server_port() -> None:
  """The image must agree with Settings.server_port so probes target the right port."""
  default_port = str(Settings.model_fields["server_port"].default)

  assert _exposed_port() == default_port
  assert f"ENV OREMI_ISINMI_SERVER_PORT={default_port}" in _dockerfile()


def test_healthcheck_falls_back_to_the_default_server_port() -> None:
  """An unset env var must not turn the probe URL into "http://127.0.0.1:/health/"."""
  default_port = str(Settings.model_fields["server_port"].default)
  healthcheck = _healthcheck()

  assert f"${{OREMI_ISINMI_SERVER_PORT:-{default_port}}}" in healthcheck, (
    "The HEALTHCHECK must fall back to Settings.server_port when OREMI_ISINMI_SERVER_PORT is unset, "
    "otherwise the probe requests http://127.0.0.1:/health/ (port 80) and the orchestrator restarts the task forever."
  )

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
"""API health tests."""
import importlib.util

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skipif(importlib.util.find_spec("sqlcipher3") is None, reason="sqlcipher3 is not installed")


def test_health_endpoint() -> None:
  from isinmi import app

  with TestClient(app) as client:
    response = client.get("/health")

  assert response.status_code == 200
  assert response.json()["status"] == "ok"

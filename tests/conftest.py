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
"""Shared test setup."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("OREMI_ISINMI_DATABASE_ENCRYPTION_KEY", "test-secret-key-with-at-least-32-chars")
os.environ.setdefault("OREMI_ISINMI_DATABASE_URL", "sqlite:///./data/test_oremi_isinmi.db")
os.environ.setdefault("OREMI_ISINMI_CALDAV_REQUEST_TIMEOUT", "30")
os.environ.setdefault("OREMI_ISINMI_LOG_FILE", "logs/test_oremi_isinmi.log")


@pytest.fixture(autouse=True)
def cleanup_test_db():
  yield
  Path("data/test_oremi_isinmi.db").unlink(missing_ok=True)

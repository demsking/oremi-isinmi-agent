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
from datetime import datetime
from typing import Any

from isinmi.core.database import json_dumps


def encode_value(value: Any) -> Any:
  """Convert Python values to SQLite-safe values."""

  if isinstance(value, datetime):
    return value.isoformat()

  if isinstance(value, list) or isinstance(value, dict):
    return json_dumps(value)

  if isinstance(value, bool):
    return int(value)

  return value


def placeholders(values: list[Any]) -> str:
  """Build SQL placeholders for an INSERT statement."""

  return ",".join("?" for _ in values)

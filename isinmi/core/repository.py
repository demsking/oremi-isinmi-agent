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
from __future__ import annotations

import json

from sqlalchemy import and_
from sqlalchemy import exists
from sqlalchemy import func
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.sql.elements import ColumnElement

from isinmi.core.models import clean_tags


def build_tags_filter(
  column: ColumnElement[list[str]],
  tags: list[str],
  dialect_name: str,
) -> ColumnElement[bool] | None:
  """Build a backend-specific expression that requires every requested tag."""

  normalized = clean_tags(tags)

  if not normalized:
    return None

  expressions: list[ColumnElement[bool]] = []

  for tag in normalized:
    if dialect_name == "postgresql":
      expressions.append(column.contains([tag]))
      continue

    if dialect_name in {"mysql", "mariadb"}:
      expressions.append(func.JSON_CONTAINS(column, json.dumps(tag)) == 1)
      continue

    values = func.json_each(column).table_valued("value")
    expressions.append(exists(select(1).select_from(values).where(values.c.value == tag)))

  return and_(*expressions)


def sort_limit_offset(query: Select, limit: int, offset: int) -> Select:
  """Apply standard pagination bounds."""

  return query.limit(limit).offset(offset)

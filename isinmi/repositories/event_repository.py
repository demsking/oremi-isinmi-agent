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

from datetime import datetime
from typing import Any

from isinmi.core.database import Database
from isinmi.core.database import tags_filter_sql
from isinmi.core.models import Event
from isinmi.repositories.base import encode_value
from isinmi.repositories.base import placeholders


class EventRepository:
  """Encrypted persistence for events."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, event: Event) -> Event:
    data = event.model_dump()
    columns = list(data)
    values = [encode_value(data[column]) for column in columns]

    await self.db.execute(
      f"INSERT INTO events ({','.join(columns)}) VALUES ({placeholders(values)})",
      tuple(values),
    )

    return event

  async def get(self, event_id: str) -> Event | None:
    row = await self.db.fetch_one("SELECT * FROM events WHERE id = ?", (event_id,))

    return Event.model_validate(row) if row else None

  async def list(
    self,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Event]:
    where: list[str] = []
    params: list[Any] = []

    if status:
      where.append("status = ?")
      params.append(status)

    if start:
      where.append("start_datetime >= ?")
      params.append(start.isoformat())

    if end:
      where.append("start_datetime <= ?")
      params.append(end.isoformat())

    if tags:
      sql, tag_params = tags_filter_sql(tags)
      where.append(sql)
      params.extend(tag_params)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = await self.db.fetch_all(
      f"SELECT * FROM events {clause} ORDER BY start_datetime ASC LIMIT ? OFFSET ?",
      tuple(params + [limit, offset]),
    )

    return [Event.model_validate(row) for row in rows]

  async def update(self, event_id: str, changes: dict[str, Any]) -> Event | None:
    if not changes:
      return await self.get(event_id)

    assignments = [f"{key} = ?" for key in changes]
    values = [encode_value(value) for value in changes.values()]

    await self.db.execute(
      f"UPDATE events SET {', '.join(assignments)} WHERE id = ?",
      tuple(values + [event_id]),
    )

    return await self.get(event_id)

  async def delete(self, event_id: str) -> bool:
    await self.db.execute("DELETE FROM events WHERE id = ?", (event_id,))

    return True

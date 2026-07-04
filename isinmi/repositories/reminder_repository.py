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
from datetime import timedelta
from typing import Any

from isinmi.core.database import Database
from isinmi.core.database import tags_filter_sql
from isinmi.core.models import Reminder
from isinmi.repositories.base import encode_value
from isinmi.repositories.base import placeholders


class ReminderRepository:
  """Encrypted persistence for reminders."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, reminder: Reminder) -> Reminder:
    data = reminder.model_dump()
    columns = list(data)
    values = [encode_value(data[column]) for column in columns]

    await self.db.execute(
      f"INSERT INTO reminders ({','.join(columns)}) VALUES ({placeholders(values)})",
      tuple(values),
    )

    return reminder

  async def get(self, reminder_id: str) -> Reminder | None:
    row = await self.db.fetch_one("SELECT * FROM reminders WHERE id = ?", (reminder_id,))

    return Reminder.model_validate(row) if row else None

  async def list(
    self,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Reminder]:
    where: list[str] = []
    params: list[Any] = []

    if status:
      where.append("status = ?")
      params.append(status)

    if start:
      where.append("datetime >= ?")
      params.append(start.isoformat())

    if end:
      where.append("datetime <= ?")
      params.append(end.isoformat())

    if tags:
      sql, tag_params = tags_filter_sql(tags)
      where.append(sql)
      params.extend(tag_params)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = await self.db.fetch_all(
      f"SELECT * FROM reminders {clause} ORDER BY datetime ASC LIMIT ? OFFSET ?",
      tuple(params + [limit, offset]),
    )

    return [Reminder.model_validate(row) for row in rows]

  async def upcoming(self) -> list[Reminder]:
    now = datetime.now()

    return await self.list(status="pending", start=now, end=now + timedelta(hours=24), limit=200)

  async def update(self, reminder_id: str, changes: dict[str, Any]) -> Reminder | None:
    if not changes:
      return await self.get(reminder_id)

    assignments = [f"{key} = ?" for key in changes]
    values = [encode_value(value) for value in changes.values()]

    await self.db.execute(
      f"UPDATE reminders SET {', '.join(assignments)} WHERE id = ?",
      tuple(values + [reminder_id]),
    )

    return await self.get(reminder_id)

  async def complete(self, reminder_id: str) -> Reminder | None:
    return await self.update(reminder_id, {"status": "completed"})

  async def delete(self, reminder_id: str) -> bool:
    await self.db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))

    return True

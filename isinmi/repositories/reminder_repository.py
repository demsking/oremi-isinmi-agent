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

from sqlalchemy import select

from isinmi.core.database import Database
from isinmi.core.models import Reminder
from isinmi.core.orm import ReminderORM
from isinmi.core.repository import build_tags_filter


class ReminderRepository:
  """ORM persistence for reminders."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, reminder: Reminder) -> Reminder:
    def _operation(session):
      record = ReminderORM(
        id=reminder.id,
        title=reminder.title,
        description=reminder.description,
        datetime=reminder.datetime,
        recurring=reminder.recurring,
        tags=reminder.tags,
        status=reminder.status,
        created_at=reminder.created_at,
        notified_at=reminder.notified_at,
      )
      session.add(record)
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Reminder.model_validate(record)

  async def get(self, reminder_id: str) -> Reminder | None:
    def _operation(session):
      return session.get(ReminderORM, reminder_id)

    record = await self.db.run(_operation)
    return Reminder.model_validate(record) if record else None

  async def list(
    self,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Reminder]:
    def _operation(session):
      stmt = select(ReminderORM)

      if status:
        stmt = stmt.where(ReminderORM.status == status)

      if start is not None:
        stmt = stmt.where(ReminderORM.datetime >= start)

      if end is not None:
        stmt = stmt.where(ReminderORM.datetime <= end)

      tag_filter = build_tags_filter(ReminderORM.tags, tags or [], session.bind.dialect.name)  # pyright: ignore
      if tag_filter is not None:
        stmt = stmt.where(tag_filter)

      stmt = stmt.order_by(ReminderORM.datetime.asc()).limit(limit).offset(offset)
      return session.scalars(stmt).all()

    rows = await self.db.run(_operation)
    return [Reminder.model_validate(row) for row in rows]

  async def update(self, reminder_id: str, changes: dict[str, object]) -> Reminder | None:
    def _operation(session):
      record = session.get(ReminderORM, reminder_id)

      if record is None:
        return None

      for key, value in changes.items():
        setattr(record, key, value)

      session.flush()
      return record

    record = await self.db.run(_operation)
    return Reminder.model_validate(record) if record else None

  async def complete(self, reminder_id: str) -> Reminder | None:
    return await self.update(reminder_id, {"status": "completed"})

  async def delete(self, reminder_id: str) -> bool:
    def _operation(session):
      record = session.get(ReminderORM, reminder_id)

      if record is None:
        return False

      session.delete(record)
      return True

    return await self.db.run(_operation)

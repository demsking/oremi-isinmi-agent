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
from isinmi.core.models import Event
from isinmi.core.orm import EventORM
from isinmi.repositories.base import build_tags_filter


class EventRepository:
  """ORM persistence for events."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, event: Event) -> Event:
    def _operation(session):
      record = EventORM(
        id=event.id,
        title=event.title,
        description=event.description,
        start_datetime=event.start_datetime,
        end_datetime=event.end_datetime,
        location=event.location,
        attendees=event.attendees,
        tags=event.tags,
        reminders=event.reminders,
        status=event.status,
        created_at=event.created_at,
      )
      session.add(record)
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Event.model_validate(record)

  async def get(self, event_id: str) -> Event | None:
    def _operation(session):
      return session.get(EventORM, event_id)

    record = await self.db.run(_operation)
    return Event.model_validate(record) if record else None

  async def list(
    self,
    status: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Event]:
    def _operation(session):
      stmt = select(EventORM)

      if status:
        stmt = stmt.where(EventORM.status == status)

      if start is not None:
        stmt = stmt.where(EventORM.start_datetime >= start)

      if end is not None:
        stmt = stmt.where(EventORM.start_datetime <= end)

      tag_filter = build_tags_filter(EventORM.tags, tags or [], session.bind.dialect.name)
      if tag_filter is not None:
        stmt = stmt.where(tag_filter)

      stmt = stmt.order_by(EventORM.start_datetime.asc()).limit(limit).offset(offset)
      return session.scalars(stmt).all()

    rows = await self.db.run(_operation)
    return [Event.model_validate(row) for row in rows]

  async def update(self, event_id: str, changes: dict[str, object]) -> Event | None:
    def _operation(session):
      record = session.get(EventORM, event_id)

      if record is None:
        return None

      for key, value in changes.items():
        setattr(record, key, value)

      session.flush()
      return record

    record = await self.db.run(_operation)
    return Event.model_validate(record) if record else None

  async def delete(self, event_id: str) -> bool:
    def _operation(session):
      record = session.get(EventORM, event_id)

      if record is None:
        return False

      session.delete(record)
      return True

    return await self.db.run(_operation)

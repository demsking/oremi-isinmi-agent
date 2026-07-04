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

from sqlalchemy import func
from sqlalchemy import select

from ..core.database import Database
from ..core.models import Notification
from ..core.orm import NotificationORM
from ..repositories.base import build_tags_filter


class NotificationRepository:
  """ORM persistence for notifications."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, notification: Notification) -> Notification:
    def _operation(session):
      record = NotificationORM(
        id=notification.id,
        type=notification.type,
        message=notification.message,
        entity_id=notification.entity_id,
        tags=notification.tags,
        timestamp=notification.timestamp,
        read_status=notification.read_status,
        read_at=notification.read_at,
      )
      session.add(record)
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Notification.model_validate(record)

  async def list(
    self,
    type_: str | None = None,
    read_status: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Notification]:
    def _operation(session):
      stmt = select(NotificationORM)

      if type_:
        stmt = stmt.where(NotificationORM.type == type_)

      if read_status is not None:
        stmt = stmt.where(NotificationORM.read_status == read_status)

      tag_filter = build_tags_filter(NotificationORM.tags, tags or [], session.bind.dialect.name)
      if tag_filter is not None:
        stmt = stmt.where(tag_filter)

      stmt = stmt.order_by(NotificationORM.timestamp.desc()).limit(limit).offset(offset)
      return session.scalars(stmt).all()

    rows = await self.db.run(_operation)
    return [Notification.model_validate(row) for row in rows]

  async def unread_count(self) -> int:
    def _operation(session):
      stmt = select(func.count()).select_from(NotificationORM).where(NotificationORM.read_status.is_(False))
      return int(session.scalar(stmt) or 0)

    return await self.db.run(_operation)

  async def mark_read(self, notification_id: str) -> Notification | None:
    def _operation(session):
      record = session.get(NotificationORM, notification_id)

      if record is None:
        return None

      record.read_status = True
      record.read_at = datetime.now()
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Notification.model_validate(record) if record else None

  async def mark_all_read(self) -> int:
    def _operation(session):
      records = session.scalars(select(NotificationORM).where(NotificationORM.read_status.is_(False))).all()
      for record in records:
        record.read_status = True
        record.read_at = datetime.now()
      session.flush()
      return len(records)

    return await self.db.run(_operation)

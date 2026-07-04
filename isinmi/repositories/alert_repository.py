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

from ..core.database import Database
from ..core.models import Alert
from ..core.orm import AlertORM
from ..repositories.base import build_tags_filter


class AlertRepository:
  """ORM persistence for alerts."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, alert: Alert) -> Alert:
    def _operation(session):
      record = AlertORM(
        id=alert.id,
        title=alert.title,
        message=alert.message,
        severity=alert.severity,
        timestamp=alert.timestamp,
        source=alert.source,
        tags=alert.tags,
        acknowledged=alert.acknowledged,
        acknowledged_at=alert.acknowledged_at,
      )
      session.add(record)
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Alert.model_validate(record)

  async def get(self, alert_id: str) -> Alert | None:
    def _operation(session):
      return session.get(AlertORM, alert_id)

    record = await self.db.run(_operation)
    return Alert.model_validate(record) if record else None

  async def list(
    self,
    severity: str | None = None,
    acknowledged: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Alert]:
    def _operation(session):
      stmt = select(AlertORM)

      if severity:
        stmt = stmt.where(AlertORM.severity == severity)

      if acknowledged is not None:
        stmt = stmt.where(AlertORM.acknowledged == acknowledged)

      tag_filter = build_tags_filter(AlertORM.tags, tags or [], session.bind.dialect.name)
      if tag_filter is not None:
        stmt = stmt.where(tag_filter)

      stmt = stmt.order_by(AlertORM.timestamp.desc()).limit(limit).offset(offset)
      return session.scalars(stmt).all()

    rows = await self.db.run(_operation)
    return [Alert.model_validate(row) for row in rows]

  async def acknowledge(self, alert_id: str) -> Alert | None:
    def _operation(session):
      record = session.get(AlertORM, alert_id)

      if record is None:
        return None

      record.acknowledged = True
      record.acknowledged_at = datetime.now()
      session.flush()
      return record

    record = await self.db.run(_operation)
    return Alert.model_validate(record) if record else None

  async def delete(self, alert_id: str) -> bool:
    def _operation(session):
      record = session.get(AlertORM, alert_id)

      if record is None:
        return False

      session.delete(record)
      return True

    return await self.db.run(_operation)

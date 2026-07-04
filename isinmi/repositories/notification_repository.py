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
from isinmi.core.models import Notification
from isinmi.repositories.base import encode_value
from isinmi.repositories.base import placeholders


class NotificationRepository:
  """Encrypted persistence for notifications."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, notification: Notification) -> Notification:
    data = notification.model_dump()
    columns = list(data)
    values = [encode_value(data[column]) for column in columns]

    await self.db.execute(
      f"INSERT INTO notifications ({','.join(columns)}) VALUES ({placeholders(values)})",
      tuple(values),
    )

    return notification

  async def list(
    self,
    type_: str | None = None,
    read_status: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Notification]:
    where: list[str] = []
    params: list[Any] = []

    if type_:
      where.append("type = ?")
      params.append(type_)

    if read_status is not None:
      where.append("read_status = ?")
      params.append(int(read_status))

    if tags:
      sql, tag_params = tags_filter_sql(tags)
      where.append(sql)
      params.extend(tag_params)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = await self.db.fetch_all(
      f"SELECT * FROM notifications {clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
      tuple(params + [limit, offset]),
    )

    return [Notification.model_validate(row) for row in rows]

  async def unread_count(self) -> int:
    row = await self.db.fetch_one("SELECT count(*) AS count FROM notifications WHERE read_status = 0")

    return int(row["count"]) if row else 0

  async def mark_read(self, notification_id: str) -> Notification | None:
    now = datetime.now().isoformat()

    await self.db.execute(
      "UPDATE notifications SET read_status = 1, read_at = ? WHERE id = ?",
      (now, notification_id),
    )

    row = await self.db.fetch_one("SELECT * FROM notifications WHERE id = ?", (notification_id,))

    return Notification.model_validate(row) if row else None

  async def mark_all_read(self) -> int:
    now = datetime.now().isoformat()

    await self.db.execute("UPDATE notifications SET read_status = 1, read_at = ? WHERE read_status = 0", (now,))

    return await self.unread_count()

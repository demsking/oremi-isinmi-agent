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
from isinmi.core.models import Alert
from isinmi.repositories.base import encode_value
from isinmi.repositories.base import placeholders


class AlertRepository:
  """Encrypted persistence for alerts."""

  table = "alerts"

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create(self, alert: Alert) -> Alert:
    data = alert.model_dump()
    columns = list(data)
    values = [encode_value(data[column]) for column in columns]

    await self.db.execute(
      f"INSERT INTO alerts ({','.join(columns)}) VALUES ({placeholders(values)})",
      tuple(values),
    )

    return alert

  async def get(self, alert_id: str) -> Alert | None:
    row = await self.db.fetch_one("SELECT * FROM alerts WHERE id = ?", (alert_id,))

    return Alert.model_validate(row) if row else None

  async def list(
    self,
    severity: str | None = None,
    acknowledged: bool | None = None,
    tags: list[str] | None = None,
    limit: int = 100,
    offset: int = 0,
  ) -> list[Alert]:
    where: list[str] = []
    params: list[Any] = []

    if severity:
      where.append("severity = ?")
      params.append(severity)

    if acknowledged is not None:
      where.append("acknowledged = ?")
      params.append(int(acknowledged))

    if tags:
      sql, tag_params = tags_filter_sql(tags)
      where.append(sql)
      params.extend(tag_params)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = await self.db.fetch_all(
      f"SELECT * FROM alerts {clause} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
      tuple(params + [limit, offset]),
    )

    return [Alert.model_validate(row) for row in rows]

  async def acknowledge(self, alert_id: str) -> Alert | None:
    now = datetime.now().isoformat()

    await self.db.execute(
      "UPDATE alerts SET acknowledged = 1, acknowledged_at = ? WHERE id = ?",
      (now, alert_id),
    )

    return await self.get(alert_id)

  async def delete(self, alert_id: str) -> bool:
    await self.db.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))

    return True

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

from fastapi import HTTPException

from isinmi.core.models import Alert
from isinmi.core.models import AlertCreate
from isinmi.repositories.alert_repository import AlertRepository
from isinmi.services.notification_service import NotificationService


class AlertService:
  """Business logic for alerts."""

  def __init__(self, repository: AlertRepository, notifications: NotificationService) -> None:
    self.repository = repository
    self.notifications = notifications

  async def create(self, payload: AlertCreate) -> Alert:
    alert = Alert(**payload.model_dump())
    saved = await self.repository.create(alert)

    await self.notifications.create("alert", saved.message, saved.id, saved.tags)

    return saved

  async def list(
    self,
    severity: str | None,
    acknowledged: bool | None,
    tags: list[str],
    limit: int,
    offset: int,
  ) -> list[Alert]:
    return await self.repository.list(
      severity=severity,
      acknowledged=acknowledged,
      tags=tags,
      limit=limit,
      offset=offset,
    )

  async def acknowledge(self, alert_id: str) -> Alert:
    alert = await self.repository.acknowledge(alert_id)

    if not alert:
      raise HTTPException(status_code=404, detail="Alert not found")

    return alert

  async def delete(self, alert_id: str) -> dict[str, str]:
    await self.repository.delete(alert_id)

    return {"status": "deleted"}

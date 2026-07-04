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

from fastapi import HTTPException

from ..core.models import Reminder
from ..core.models import ReminderCreate
from ..core.models import ReminderUpdate
from ..repositories.reminder_repository import ReminderRepository
from ..services.notification_service import NotificationService


class ReminderService:
  """Business logic for reminders."""

  def __init__(self, repository: ReminderRepository, notifications: NotificationService) -> None:
    self.repository = repository
    self.notifications = notifications

  async def create(self, payload: ReminderCreate) -> Reminder:
    reminder = Reminder(**payload.model_dump())
    saved = await self.repository.create(reminder)

    await self.notifications.create("reminder", f"Reminder scheduled: {saved.title}", saved.id, saved.tags)

    return saved

  async def list(
    self,
    status: str | None,
    start: datetime | None,
    end: datetime | None,
    tags: list[str],
    limit: int,
    offset: int,
  ) -> list[Reminder]:
    return await self.repository.list(status=status, start=start, end=end, tags=tags, limit=limit, offset=offset)

  async def upcoming(self) -> list[Reminder]:
    return await self.repository.upcoming()

  async def update(self, reminder_id: str, payload: ReminderUpdate) -> Reminder:
    reminder = await self.repository.update(reminder_id, payload.model_dump(exclude_unset=True))

    if not reminder:
      raise HTTPException(status_code=404, detail="Reminder not found")

    return reminder

  async def complete(self, reminder_id: str) -> Reminder:
    reminder = await self.repository.complete(reminder_id)

    if not reminder:
      raise HTTPException(status_code=404, detail="Reminder not found")

    return reminder

  async def delete(self, reminder_id: str) -> dict[str, str]:
    await self.repository.delete(reminder_id)

    return {"status": "deleted"}

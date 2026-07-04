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

from isinmi.core.models import Event
from isinmi.core.models import EventCreate
from isinmi.core.models import EventUpdate
from isinmi.repositories.event_repository import EventRepository
from isinmi.services.notification_service import NotificationService


class EventService:
  """Business logic for events."""

  def __init__(self, repository: EventRepository, notifications: NotificationService) -> None:
    self.repository = repository
    self.notifications = notifications

  async def create(self, payload: EventCreate) -> Event:
    event = Event(**payload.model_dump())
    saved = await self.repository.create(event)

    await self.notifications.create("event", f"Event scheduled: {saved.title}", saved.id, saved.tags)

    return saved

  async def get(self, event_id: str) -> Event:
    event = await self.repository.get(event_id)

    if not event:
      raise HTTPException(status_code=404, detail="Event not found")

    return event

  async def list(
    self,
    status: str | None,
    start: datetime | None,
    end: datetime | None,
    tags: list[str],
    limit: int,
    offset: int,
  ) -> list[Event]:
    return await self.repository.list(status=status, start=start, end=end, tags=tags, limit=limit, offset=offset)

  async def update(self, event_id: str, payload: EventUpdate) -> Event:
    event = await self.repository.update(event_id, payload.model_dump(exclude_unset=True))

    if not event:
      raise HTTPException(status_code=404, detail="Event not found")

    return event

  async def delete(self, event_id: str) -> dict[str, str]:
    await self.repository.delete(event_id)

    return {"status": "deleted"}

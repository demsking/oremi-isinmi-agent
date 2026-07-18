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

from typing import Literal

from fastapi import HTTPException

from isinmi.core.models import clean_tags
from isinmi.core.models import Notification
from isinmi.repositories.notification_repository import NotificationRepository
from isinmi.sse.manager import SSEManager


class NotificationService:
  """Business logic for notifications."""

  def __init__(self, repository: NotificationRepository, sse: SSEManager) -> None:
    self.repository = repository
    self.sse = sse

  async def create(
    self,
    type_: Literal["reminder", "event"],
    message: str,
    entity_id: str,
    tags: list[str],
  ) -> Notification:
    notification = Notification(type=type_, message=message, entity_id=entity_id, tags=tags)
    saved = await self.repository.create(notification)

    await self.sse.publish(f"new_{type_}", saved.model_dump(), saved.tags)

    return saved

  async def list(
    self,
    type_: Literal["reminder", "event"] | None,
    tags: list[str],
    read_status: bool | None,
    limit: int,
    offset: int,
  ) -> list[Notification]:
    return await self.repository.list(type_=type_, tags=tags, read_status=read_status, limit=limit, offset=offset)

  async def unread_count(self) -> dict[str, int]:
    return {"count": await self.repository.unread_count()}

  async def mark_read(self, notification_id: str) -> Notification:
    notification = await self.repository.mark_read(notification_id)

    if not notification:
      raise HTTPException(status_code=404, detail="Notification not found")

    return notification

  async def mark_all_read(self, tags: list[str] | None = None) -> dict[str, int | str]:
    if tags:
      count = await self.repository.mark_all_read_by_tags(clean_tags(tags))
    else:
      count = await self.repository.mark_all_read()

    return {"status": "ok", "count": count}

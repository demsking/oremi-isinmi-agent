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
import asyncio
import json
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from uuid import uuid4

from ..core.models import clean_tags


@dataclass
class Subscriber:
  id: str = field(default_factory=lambda: str(uuid4()))
  tags: list[str] = field(default_factory=list)
  queue: asyncio.Queue[dict[str, Any]] = field(default_factory=asyncio.Queue)


class SSEManager:
  """In-memory fanout manager for live notification events."""

  def __init__(self) -> None:
    self._subscribers: dict[str, Subscriber] = {}
    self._lock = asyncio.Lock()

  async def subscribe(self, tags: list[str]) -> Subscriber:
    subscriber = Subscriber(tags=clean_tags(tags))

    async with self._lock:
      self._subscribers[subscriber.id] = subscriber

    return subscriber

  async def unsubscribe(self, subscriber_id: str) -> None:
    async with self._lock:
      self._subscribers.pop(subscriber_id, None)

  async def publish(self, event_type: str, payload: dict[str, Any], tags: list[str] | None = None) -> None:
    normalized_tags = clean_tags(tags or [])

    async with self._lock:
      subscribers = list(self._subscribers.values())

    for subscriber in subscribers:
      if subscriber.tags and not set(subscriber.tags).intersection(normalized_tags):
        continue

      await subscriber.queue.put(
        {
          "event": event_type,
          "data": json.dumps(payload, default=str),
        }
      )

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
"""ORM repository integration tests."""
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from isinmi.core.database import Database
from isinmi.core.models import Event
from isinmi.core.models import Notification
from isinmi.core.models import Reminder
from isinmi.core.settings import Settings
from isinmi.repositories.event_repository import EventRepository
from isinmi.repositories.notification_repository import NotificationRepository
from isinmi.repositories.reminder_repository import ReminderRepository


async def test_reminder_repository_round_trip_with_tag_filter(tmp_path: Path) -> None:
  db_path = tmp_path / "reminders.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  try:
    await database.initialize()

    repository = ReminderRepository(database)
    reminder = Reminder(
      title="Buy milk",
      description="Pick up milk after work.",
      datetime=datetime.now() + timedelta(hours=2),
      tags=["device_id:phone-1", "user_id:alex"],
    )

    saved = await repository.create(reminder)
    fetched = await repository.get(saved.id)
    filtered = await repository.list(tags=["device_id:phone-1"])

    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.tags == ["device_id:phone-1", "user_id:alex"]
    assert len(filtered) == 1
    assert filtered[0].id == saved.id
  finally:
    await database.dispose()


async def test_event_repository_round_trip_with_tag_filter(tmp_path: Path) -> None:
  db_path = tmp_path / "events.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  try:
    await database.initialize()

    repository = EventRepository(database)
    start = datetime.now() + timedelta(days=1)
    event = Event(
      title="Team sync",
      description="Weekly review.",
      start_datetime=start,
      end_datetime=start + timedelta(hours=1),
      tags=["device_id:laptop-1", "user_id:alex"],
    )

    saved = await repository.create(event)
    fetched = await repository.get(saved.id)
    filtered = await repository.list(tags=["user_id:alex"])

    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.tags == ["device_id:laptop-1", "user_id:alex"]
    assert len(filtered) == 1
    assert filtered[0].id == saved.id
  finally:
    await database.dispose()


async def test_notification_repository_marks_all_read(tmp_path: Path) -> None:
  db_path = tmp_path / "notifications.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  try:
    await database.initialize()

    repository = NotificationRepository(database)
    notification = Notification(type="reminder", message="Test notification", entity_id="reminder-1", tags=["test"])

    await repository.create(notification)
    assert await repository.unread_count() == 1

    marked = await repository.mark_all_read()

    assert marked == 1
    assert await repository.unread_count() == 0
  finally:
    await database.dispose()


async def test_notification_repository_marks_all_read_by_tags(tmp_path: Path) -> None:
  db_path = tmp_path / "notifications_by_tags.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  try:
    await database.initialize()

    repository = NotificationRepository(database)
    tagged = Notification(
      type="reminder",
      message="Tagged notification",
      entity_id="reminder-1",
      tags=["device_id:iphone"],
    )
    other = Notification(
      type="event",
      message="Other notification",
      entity_id="event-2",
      tags=["device_id:android"],
    )

    await repository.create(tagged)
    await repository.create(other)

    marked = await repository.mark_all_read_by_tags(["device_id:iphone"])

    assert marked == 1
    assert await repository.unread_count() == 1
  finally:
    await database.dispose()

"""ORM repository integration tests."""

from pathlib import Path

from isinmi.core.database import Database
from isinmi.core.models import Alert
from isinmi.core.models import Notification
from isinmi.core.settings import Settings
from isinmi.repositories.alert_repository import AlertRepository
from isinmi.repositories.notification_repository import NotificationRepository


async def test_alert_repository_round_trip_with_tag_filter(tmp_path: Path) -> None:
  db_path = tmp_path / "alerts.db"
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{db_path}")
  database = Database(settings)
  try:
    await database.initialize()

    repository = AlertRepository(database)
    alert = Alert(
      title="Front door open",
      message="The front door is open.",
      severity="warning",
      tags=["home", "urgent"],
    )

    saved = await repository.create(alert)
    fetched = await repository.get(saved.id)
    filtered = await repository.list(tags=["home"])

    assert fetched is not None
    assert fetched.id == saved.id
    assert fetched.tags == ["home", "urgent"]
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
    notification = Notification(type="alert", message="Test notification", entity_id="alert-1", tags=["test"])

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
    tagged = Notification(type="alert", message="Tagged notification", entity_id="alert-1", tags=["device:iphone"])
    other = Notification(type="alert", message="Other notification", entity_id="alert-2", tags=["device:android"])

    await repository.create(tagged)
    await repository.create(other)

    marked = await repository.mark_all_read_by_tags(["device:iphone"])

    assert marked == 1
    assert await repository.unread_count() == 1
  finally:
    await database.dispose()

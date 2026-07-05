"""CalDAV integration tests."""

from datetime import datetime
from pathlib import Path

from pydantic import SecretStr

from isinmi.core.database import Database
from isinmi.core.models import CalDAVAccountCreate
from isinmi.core.models import Event
from isinmi.core.models import EventCreate
from isinmi.core.settings import Settings
from isinmi.integrations.caldav.service import CalDAVSyncService
from isinmi.repositories.caldav_repository import CalDAVRepository
from isinmi.repositories.event_repository import EventRepository


class FakeResponse:
  def __init__(self, status_code: int = 201, headers: dict[str, str] | None = None) -> None:
    self.status_code = status_code
    self.headers = headers or {"ETag": '"abc123"'}


class FakeClient:
  calls: list[tuple[str, str, str | None]] = []

  def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002,ANN003
    self.args = args
    self.kwargs = kwargs

  async def __aenter__(self):
    return self

  async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001
    return None

  async def put(self, url: str, content: bytes):  # noqa: ANN001
    self.calls.append(("PUT", url, content.decode("utf-8")))
    return FakeResponse()

  async def delete(self, url: str):  # noqa: ANN001
    self.calls.append(("DELETE", url, None))
    return FakeResponse(status_code=204)


async def test_caldav_render_event_ical_includes_categories(tmp_path: Path) -> None:
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{tmp_path / 'caldav.db'}")
  database = Database(settings)
  await database.initialize()

  try:
    service = CalDAVSyncService(CalDAVRepository(database), EventRepository(database), request_timeout=5)
    event = EventCreate(
      title="Team sync",
      start_datetime=datetime(2026, 7, 6, 9, 0, 0),
      end_datetime=datetime(2026, 7, 6, 9, 30, 0),
      tags=["work", "device:web"],
    )
    rendered = service._render_event_ical(Event(**event.model_dump()), remote_uid="event-123")

    assert "BEGIN:VCALENDAR" in rendered
    assert "SUMMARY:Team sync" in rendered
    assert "CATEGORIES:work\\,device:web" in rendered
    assert "UID:event-123" in rendered
  finally:
    await database.dispose()


async def test_caldav_sync_event_pushes_to_remote_calendar(tmp_path: Path, monkeypatch) -> None:
  settings = Settings(database_encryption_key="x" * 32, database_url=f"sqlite:///{tmp_path / 'sync.db'}")
  database = Database(settings)
  await database.initialize()

  try:
    caldav_repository = CalDAVRepository(database)
    event_repository = EventRepository(database)
    service = CalDAVSyncService(caldav_repository, event_repository, request_timeout=5)

    await caldav_repository.create_account(
      CalDAVAccountCreate(
        name="Work Calendar",
        base_url="https://cal.example.com",
        calendar_url="https://cal.example.com/calendars/work/",
        username="alice",
        password=SecretStr("x" * 32),
      )
    )

    event_payload = EventCreate(
      title="Planning",
      start_datetime=datetime(2026, 7, 6, 10, 0, 0),
      end_datetime=datetime(2026, 7, 6, 11, 0, 0),
      tags=[],
    )
    event = await event_repository.create(Event(**event_payload.model_dump()))

    monkeypatch.setattr("isinmi.integrations.caldav.service.httpx.AsyncClient", FakeClient)

    results = await service.sync_event(event)

    assert results[0].status == "synced"
    link = await caldav_repository.get_link(results[0].account_id, event.id)
    assert link is not None
    assert link["remote_uid"] == event.id
  finally:
    await database.dispose()

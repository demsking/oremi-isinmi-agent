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

import logging
from datetime import datetime
from datetime import UTC
from urllib.parse import quote

import httpx

from ...core.models import CalDAVAccount
from ...core.models import CalDAVAccountCreate
from ...core.models import CalDAVAccountUpdate
from ...core.models import CalDAVSyncResult
from ...core.models import Event
from ...core.orm import CalDAVAccountORM
from ...repositories.caldav_repository import CalDAVRepository
from ...repositories.event_repository import EventRepository

logger = logging.getLogger(__name__)


class CalDAVSyncService:
  """Push local events to configured CalDAV calendars."""

  def __init__(self, repository: CalDAVRepository, events: EventRepository, request_timeout: int) -> None:
    self.repository = repository
    self.events = events
    self.request_timeout = request_timeout

  async def list_accounts(self, active_only: bool = False) -> list[CalDAVAccount]:
    return await self.repository.list_accounts(active_only=active_only)

  async def create_account(self, payload: CalDAVAccountCreate) -> CalDAVAccount:
    return await self.repository.create_account(payload)

  async def update_account(self, account_id: str, payload: CalDAVAccountUpdate) -> CalDAVAccount | None:
    return await self.repository.update_account(account_id, payload)

  async def delete_account(self, account_id: str) -> bool:
    return await self.repository.delete_account(account_id)

  async def sync_event(self, event: Event | str) -> list[CalDAVSyncResult]:
    local_event = await self._resolve_event(event)

    if local_event is None:
      return []

    accounts = await self.repository.list_account_records_for_event(local_event.tags)
    results: list[CalDAVSyncResult] = []

    for account in accounts:
      results.append(await self._sync_event_to_account(account, local_event))

    return results

  async def sync_events(self, tags: list[str] | None = None) -> list[CalDAVSyncResult]:
    events = await self.events.list(status=None, start=None, end=None, tags=tags or [], limit=1000, offset=0)
    results: list[CalDAVSyncResult] = []

    for event in events:
      results.extend(await self.sync_event(event))

    return results

  async def delete_event(self, event: Event | str) -> list[CalDAVSyncResult]:
    local_event = await self._resolve_event(event)
    event_id = local_event.id if local_event is not None else (event if isinstance(event, str) else None)

    if event_id is None:
      return []

    links = await self.repository.list_links_for_event(event_id)
    results: list[CalDAVSyncResult] = []

    for link in links:
      account = await self.repository.get_account_record(link["account_id"])

      if account is None:
        continue

      results.append(await self._delete_event_from_account(account, event_id))

    return results

  async def _resolve_event(self, event: Event | str) -> Event | None:
    if isinstance(event, Event):
      return event

    return await self.events.get(event)

  async def _sync_event_to_account(self, account: CalDAVAccountORM, event: Event) -> CalDAVSyncResult:
    remote_uid = event.id
    link = await self.repository.get_link(account.id, event.id)
    remote_href = link["remote_href"] if link else self._build_remote_href(account.calendar_url, remote_uid)
    ical_payload = self._render_event_ical(event, remote_uid=remote_uid)

    try:
      async with httpx.AsyncClient(
        auth=(account.username, account.password),
        timeout=self.request_timeout,
        headers={"Content-Type": "text/calendar; charset=utf-8"},
      ) as client:
        response = await client.put(remote_href, content=ical_payload.encode("utf-8"))

      if response.status_code not in {200, 201, 204}:
        raise RuntimeError(f"CalDAV PUT returned HTTP {response.status_code}")

      remote_etag = response.headers.get("ETag")
      await self.repository.upsert_link(
        account.id,
        event.id,
        remote_uid=remote_uid,
        remote_href=remote_href,
        remote_etag=remote_etag,
        sync_status="synced",
        last_sync_error=None,
      )
      await self.repository.set_account_sync_state(account.id, sync_token=None, error=None)

      return CalDAVSyncResult(
        account_id=account.id,
        event_id=event.id,
        remote_uid=remote_uid,
        remote_href=remote_href,
        etag=remote_etag,
        status="synced",
        message="Event synchronized to CalDAV",
      )
    except Exception as exc:
      logger.exception("CalDAV sync failed for event %s on account %s", event.id, account.id)
      await self.repository.upsert_link(
        account.id,
        event.id,
        remote_uid=remote_uid,
        remote_href=remote_href,
        remote_etag=None,
        sync_status="failed",
        last_sync_error=str(exc),
      )
      await self.repository.set_account_sync_state(account.id, sync_token=None, error=str(exc))
      return CalDAVSyncResult(
        account_id=account.id,
        event_id=event.id,
        remote_uid=remote_uid,
        remote_href=remote_href,
        etag=None,
        status="failed",
        message=str(exc),
      )

  async def _delete_event_from_account(self, account: CalDAVAccountORM, event_id: str) -> CalDAVSyncResult:
    link = await self.repository.get_link(account.id, event_id)

    if link is None:
      return CalDAVSyncResult(
        account_id=account.id,
        event_id=event_id,
        remote_uid=None,
        remote_href=None,
        etag=None,
        status="skipped",
        message="No CalDAV link found for this event",
      )

    try:
      async with httpx.AsyncClient(
        auth=(account.username, account.password),
        timeout=self.request_timeout,
      ) as client:
        response = await client.delete(link["remote_href"])

      if response.status_code not in {200, 202, 204, 404}:
        raise RuntimeError(f"CalDAV DELETE returned HTTP {response.status_code}")

      await self.repository.mark_link_deleted(account.id, event_id)
      return CalDAVSyncResult(
        account_id=account.id,
        event_id=event_id,
        remote_uid=link["remote_uid"],
        remote_href=link["remote_href"],
        etag=link["remote_etag"] or None,
        status="deleted",
        message="Event removed from CalDAV",
      )
    except Exception as exc:
      logger.exception("CalDAV delete failed for event %s on account %s", event_id, account.id)
      return CalDAVSyncResult(
        account_id=account.id,
        event_id=event_id,
        remote_uid=link["remote_uid"],
        remote_href=link["remote_href"],
        etag=link["remote_etag"] or None,
        status="failed",
        message=str(exc),
      )

  def _build_remote_href(self, calendar_url: str, remote_uid: str) -> str:
    base = calendar_url.rstrip("/")
    return f"{base}/{quote(remote_uid)}.ics"

  def _render_event_ical(self, event: Event, remote_uid: str) -> str:
    lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Oremi Isinmi Agent//CalDAV Integration//EN",
      "CALSCALE:GREGORIAN",
      "BEGIN:VEVENT",
      f"UID:{self._escape_ical(remote_uid)}",
      f"DTSTAMP:{self._format_ical_datetime(datetime.now(UTC))}",
      f"DTSTART:{self._format_ical_datetime(event.start_datetime)}",
      f"DTEND:{self._format_ical_datetime(event.end_datetime)}",
      f"SUMMARY:{self._escape_ical(event.title)}",
    ]

    if event.description:
      lines.append(f"DESCRIPTION:{self._escape_ical(event.description)}")

    if event.location:
      lines.append(f"LOCATION:{self._escape_ical(event.location)}")

    if event.tags:
      lines.append(f"CATEGORIES:{self._escape_ical(','.join(event.tags))}")

    for attendee in event.attendees:
      if "@" in attendee:
        lines.append(f"ATTENDEE:mailto:{self._escape_ical(attendee)}")
      else:
        lines.append(f"ATTENDEE;CN={self._escape_ical(attendee)}:mailto:{self._escape_ical(attendee)}")

    lines.append(f"STATUS:{event.status.upper()}")
    lines.extend(["END:VEVENT", "END:VCALENDAR"])

    return "\r\n".join(lines) + "\r\n"

  def _escape_ical(self, value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

  def _format_ical_datetime(self, value: datetime) -> str:
    if value.tzinfo is None:
      return value.strftime("%Y%m%dT%H%M%S")

    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")

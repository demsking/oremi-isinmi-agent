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

from sqlalchemy import select

from ..core.database import Database
from ..core.models import CalDAVAccount
from ..core.models import CalDAVAccountCreate
from ..core.models import CalDAVAccountUpdate
from ..core.models import CalDAVSyncResult
from ..core.models import new_id
from ..core.orm import CalDAVAccountORM
from ..core.orm import CalDAVEventLinkORM


class CalDAVRepository:
  """ORM persistence for CalDAV accounts and event sync links."""

  def __init__(self, db: Database) -> None:
    self.db = db

  async def create_account(self, payload: CalDAVAccountCreate) -> CalDAVAccount:
    def _operation(session):
      now = datetime.now()
      record = CalDAVAccountORM(
        id=new_id(),
        name=payload.name,
        base_url=payload.base_url,
        calendar_url=payload.calendar_url,
        username=payload.username,
        password=payload.password.get_secret_value(),
        tags=payload.tags,
        is_active=payload.is_active,
        sync_token=None,
        last_synced_at=None,
        last_sync_error=None,
        created_at=now,
        updated_at=now,
      )

      session.add(record)
      session.flush()

      return record

    record = await self.db.run(_operation)

    return CalDAVAccount.model_validate(record)

  async def list_accounts(self, active_only: bool = False) -> list[CalDAVAccount]:
    rows = await self.list_account_records(active_only=active_only)

    return [CalDAVAccount.model_validate(row) for row in rows]

  async def list_account_records(self, active_only: bool = False) -> list[CalDAVAccountORM]:
    def _operation(session):
      stmt = select(CalDAVAccountORM).order_by(CalDAVAccountORM.created_at.asc())

      if active_only:
        stmt = stmt.where(CalDAVAccountORM.is_active.is_(True))

      return session.scalars(stmt).all()

    return await self.db.run(_operation)

  async def get_account(self, account_id: str) -> CalDAVAccount | None:
    record = await self.get_account_record(account_id)

    return CalDAVAccount.model_validate(record) if record else None

  async def get_account_record(self, account_id: str) -> CalDAVAccountORM | None:
    def _operation(session):
      return session.get(CalDAVAccountORM, account_id)

    return await self.db.run(_operation)

  async def update_account(self, account_id: str, changes: CalDAVAccountUpdate) -> CalDAVAccount | None:
    def _operation(session):
      record = session.get(CalDAVAccountORM, account_id)

      if record is None:
        return None

      payload = changes.model_dump(exclude_unset=True)

      if "password" in payload and payload["password"] is not None:
        payload["password"] = payload["password"].get_secret_value()

      for key, value in payload.items():
        setattr(record, key, value)

      record.updated_at = datetime.now()
      session.flush()

      return record

    record = await self.db.run(_operation)

    return CalDAVAccount.model_validate(record) if record else None

  async def delete_account(self, account_id: str) -> bool:
    def _operation(session):
      record = session.get(CalDAVAccountORM, account_id)

      if record is None:
        return False

      session.query(CalDAVEventLinkORM).filter(CalDAVEventLinkORM.account_id == account_id).delete()
      session.delete(record)

      return True

    return await self.db.run(_operation)

  async def list_accounts_for_event(self, event_tags: list[str]) -> list[CalDAVAccount]:
    rows = await self.list_account_records_for_event(event_tags)

    return [CalDAVAccount.model_validate(row) for row in rows]

  async def list_account_records_for_event(self, event_tags: list[str]) -> list[CalDAVAccountORM]:
    def _operation(session):
      return session.scalars(select(CalDAVAccountORM).where(CalDAVAccountORM.is_active.is_(True))).all()

    rows = await self.db.run(_operation)

    if not event_tags:
      return rows

    requested = set(event_tags)

    return [account for account in rows if not account.tags or requested.issuperset(account.tags)]

  async def get_link(self, account_id: str, event_id: str) -> dict[str, str] | None:
    def _operation(session):
      stmt = select(CalDAVEventLinkORM).where(
        CalDAVEventLinkORM.account_id == account_id,
        CalDAVEventLinkORM.event_id == event_id,
      )

      record = session.scalars(stmt).first()

      if record is None:
        return None

      return {
        "id": record.id,
        "account_id": record.account_id,
        "event_id": record.event_id,
        "remote_uid": record.remote_uid,
        "remote_href": record.remote_href,
        "remote_etag": record.remote_etag or "",
        "sync_status": record.sync_status,
        "last_synced_at": record.last_synced_at.isoformat() if record.last_synced_at else "",
        "last_sync_error": record.last_sync_error or "",
      }

    return await self.db.run(_operation)

  async def upsert_link(
    self,
    account_id: str,
    event_id: str,
    remote_uid: str,
    remote_href: str,
    remote_etag: str | None,
    sync_status: str,
    last_sync_error: str | None = None,
  ) -> None:
    def _operation(session):
      record = session.scalars(
        select(CalDAVEventLinkORM).where(
          CalDAVEventLinkORM.account_id == account_id,
          CalDAVEventLinkORM.event_id == event_id,
        )
      ).first()

      now = datetime.now()

      if record is None:
        record = CalDAVEventLinkORM(
          id=new_id(),
          account_id=account_id,
          event_id=event_id,
          remote_uid=remote_uid,
          remote_href=remote_href,
          remote_etag=remote_etag,
          sync_status=sync_status,
          last_synced_at=now if sync_status == "synced" else None,
          last_sync_error=last_sync_error,
          created_at=now,
          updated_at=now,
        )

        session.add(record)

        return

      record.remote_uid = remote_uid
      record.remote_href = remote_href
      record.remote_etag = remote_etag
      record.sync_status = sync_status
      record.last_synced_at = now if sync_status == "synced" else record.last_synced_at
      record.last_sync_error = last_sync_error
      record.updated_at = now

    await self.db.run(_operation)

  async def mark_link_deleted(self, account_id: str, event_id: str) -> None:
    def _operation(session):
      record = session.scalars(
        select(CalDAVEventLinkORM).where(
          CalDAVEventLinkORM.account_id == account_id,
          CalDAVEventLinkORM.event_id == event_id,
        )
      ).first()

      if record is None:
        return

      record.sync_status = "deleted"
      record.last_synced_at = datetime.now()
      record.updated_at = datetime.now()

    await self.db.run(_operation)

  async def list_links_for_event(self, event_id: str) -> list[dict[str, str]]:
    def _operation(session):
      stmt = select(CalDAVEventLinkORM).where(CalDAVEventLinkORM.event_id == event_id)
      rows = session.scalars(stmt).all()
      return [
        {
          "id": row.id,
          "account_id": row.account_id,
          "event_id": row.event_id,
          "remote_uid": row.remote_uid,
          "remote_href": row.remote_href,
          "remote_etag": row.remote_etag or "",
          "sync_status": row.sync_status,
          "last_synced_at": row.last_synced_at.isoformat() if row.last_synced_at else "",
          "last_sync_error": row.last_sync_error or "",
        }
        for row in rows
      ]

    return await self.db.run(_operation)

  async def set_account_sync_state(self, account_id: str, sync_token: str | None, error: str | None = None) -> None:
    def _operation(session):
      record = session.get(CalDAVAccountORM, account_id)

      if record is None:
        return

      record.sync_token = sync_token
      record.last_synced_at = datetime.now() if error is None else record.last_synced_at
      record.last_sync_error = error
      record.updated_at = datetime.now()

    await self.db.run(_operation)

  async def list_sync_results(self, account_id: str) -> list[CalDAVSyncResult]:
    def _operation(session):
      stmt = select(CalDAVEventLinkORM).where(CalDAVEventLinkORM.account_id == account_id)

      return session.scalars(stmt).all()

    rows = await self.db.run(_operation)

    return [
      CalDAVSyncResult(
        account_id=row.account_id,
        event_id=row.event_id,
        remote_uid=row.remote_uid,
        remote_href=row.remote_href,
        etag=row.remote_etag,
        status=row.sync_status,  # type: ignore[arg-type]
        message=row.last_sync_error,
      )
      for row in rows
    ]

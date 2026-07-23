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

from datetime import datetime as PyDateTime

from sqlalchemy import Boolean
from sqlalchemy import CheckConstraint
from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


JsonType = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
  """Declarative base for all persisted entities."""


class ReminderORM(Base):
  __tablename__ = "reminders"
  __table_args__ = (
    CheckConstraint("recurring IN ('none', 'daily', 'weekly', 'monthly')", name="ck_reminders_recurring"),
    CheckConstraint("status IN ('pending', 'completed', 'dismissed')", name="ck_reminders_status"),
    Index("idx_reminders_datetime", "datetime"),
    Index("idx_reminders_status", "status"),
    Index("idx_reminders_tags", "tags"),
  )

  id: Mapped[str] = mapped_column(String, primary_key=True)
  title: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(String(500), nullable=True)
  datetime: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  recurring: Mapped[str] = mapped_column(String(16), nullable=False)
  tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  status: Mapped[str] = mapped_column(String(16), nullable=False)
  created_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  notified_at: Mapped[PyDateTime | None] = mapped_column(DateTime, nullable=True)


class EventORM(Base):
  __tablename__ = "events"
  __table_args__ = (
    CheckConstraint("status IN ('scheduled', 'ongoing', 'completed', 'cancelled')", name="ck_events_status"),
    CheckConstraint("end_datetime > start_datetime", name="ck_events_date_order"),
    Index("idx_events_start_datetime", "start_datetime"),
    Index("idx_events_end_datetime", "end_datetime"),
    Index("idx_events_status", "status"),
    Index("idx_events_tags", "tags"),
  )

  id: Mapped[str] = mapped_column(String, primary_key=True)
  title: Mapped[str] = mapped_column(String(200), nullable=False)
  description: Mapped[str | None] = mapped_column(String(500), nullable=True)
  start_datetime: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  end_datetime: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  location: Mapped[str | None] = mapped_column(String(200), nullable=True)
  attendees: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  reminders: Mapped[list[int]] = mapped_column(JsonType, nullable=False)
  status: Mapped[str] = mapped_column(String(16), nullable=False)
  created_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)


class NotificationORM(Base):
  __tablename__ = "notifications"
  __table_args__ = (
    CheckConstraint("type IN ('reminder', 'event')", name="ck_notifications_type"),
    Index("idx_notifications_timestamp", "timestamp"),
    Index("idx_notifications_type", "type"),
    Index("idx_notifications_entity_id", "entity_id"),
    Index("idx_notifications_read_status", "read_status"),
    Index("idx_notifications_tags", "tags"),
  )

  id: Mapped[str] = mapped_column(String, primary_key=True)
  type: Mapped[str] = mapped_column(String(16), nullable=False)
  message: Mapped[str] = mapped_column(String, nullable=False)
  entity_id: Mapped[str] = mapped_column(String, nullable=False)
  tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  timestamp: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  read_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
  read_at: Mapped[PyDateTime | None] = mapped_column(DateTime, nullable=True)


class AgentConversationORM(Base):
  __tablename__ = "agent_conversations"
  __table_args__ = (Index("idx_agent_conversations_created_at", "created_at"),)

  id: Mapped[str] = mapped_column(String, primary_key=True)
  message: Mapped[str] = mapped_column(String, nullable=False)
  response: Mapped[str] = mapped_column(String, nullable=False)
  action_type: Mapped[str] = mapped_column(String(64), nullable=False)
  entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
  tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  context: Mapped[dict[str, object]] = mapped_column(JsonType, nullable=False)
  created_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)


class CalDAVAccountORM(Base):
  __tablename__ = "caldav_accounts"
  __table_args__ = (
    Index("idx_caldav_accounts_is_active", "is_active"),
    Index("idx_caldav_accounts_tags", "tags"),
  )

  id: Mapped[str] = mapped_column(String, primary_key=True)
  name: Mapped[str] = mapped_column(String(200), nullable=False)
  base_url: Mapped[str] = mapped_column(String(500), nullable=False)
  calendar_url: Mapped[str] = mapped_column(String(500), nullable=False)
  username: Mapped[str] = mapped_column(String(200), nullable=False)
  password: Mapped[str] = mapped_column(String(500), nullable=False)
  tags: Mapped[list[str]] = mapped_column(JsonType, nullable=False)
  is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
  sync_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
  last_synced_at: Mapped[PyDateTime | None] = mapped_column(DateTime, nullable=True)
  last_sync_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
  created_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  updated_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)


class CalDAVEventLinkORM(Base):
  __tablename__ = "caldav_event_links"
  __table_args__ = (
    Index("idx_caldav_event_links_account_id", "account_id"),
    Index("idx_caldav_event_links_event_id", "event_id"),
    Index("idx_caldav_event_links_remote_uid", "remote_uid"),
    Index("idx_caldav_event_links_status", "sync_status"),
  )

  id: Mapped[str] = mapped_column(String, primary_key=True)
  account_id: Mapped[str] = mapped_column(String, nullable=False)
  event_id: Mapped[str] = mapped_column(String, nullable=False)
  remote_uid: Mapped[str] = mapped_column(String(500), nullable=False)
  remote_href: Mapped[str] = mapped_column(String(1000), nullable=False)
  remote_etag: Mapped[str | None] = mapped_column(String(200), nullable=True)
  sync_status: Mapped[str] = mapped_column(String(32), nullable=False)
  last_synced_at: Mapped[PyDateTime | None] = mapped_column(DateTime, nullable=True)
  last_sync_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
  created_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)
  updated_at: Mapped[PyDateTime] = mapped_column(DateTime, nullable=False)

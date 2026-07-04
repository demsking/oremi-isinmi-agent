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

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import sqlcipher3 as sqlite

from .settings import Settings

logger = logging.getLogger(__name__)


def database_path(database_url: str) -> Path:
  """Extract a filesystem path from a sqlite:/// URL."""

  raw = database_url.removeprefix("sqlite:///")
  return Path(raw).expanduser()


class Database:
  """Small async wrapper around SQLCipher connections."""

  def __init__(self, settings: Settings) -> None:
    self.settings = settings
    self.path = database_path(settings.database_url)
    self.key = settings.database_encryption_key.get_secret_value()
    self._lock = asyncio.Lock()

  def _connect(self) -> sqlite.Connection:
    if sqlite is None:
      raise RuntimeError("sqlcipher3 is required for encrypted database storage")

    self.path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite.connect(str(self.path), check_same_thread=False)
    conn.row_factory = sqlite.Row
    escaped_key = self.key.replace("'", "''")

    conn.execute(f"PRAGMA key = '{escaped_key}'")
    conn.execute("PRAGMA cipher_memory_security = ON")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("SELECT count(*) FROM sqlite_master")

    return conn

  @asynccontextmanager
  async def connection(self) -> AsyncGenerator[sqlite.Connection, None]:
    async with self._lock:
      conn = await asyncio.to_thread(self._connect)

      try:
        yield conn
        await asyncio.to_thread(conn.commit)
      except Exception:
        await asyncio.to_thread(conn.rollback)
        raise
      finally:
        await asyncio.to_thread(conn.close)

  async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
    async with self.connection() as conn:
      await asyncio.to_thread(conn.execute, sql, params)

  async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    async with self.connection() as conn:
      cursor = await asyncio.to_thread(conn.execute, sql, params)
      row = await asyncio.to_thread(cursor.fetchone)

      return dict(row) if row else None

  async def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with self.connection() as conn:
      cursor = await asyncio.to_thread(conn.execute, sql, params)
      rows = await asyncio.to_thread(cursor.fetchall)

      return [dict(row) for row in rows]

  async def initialize(self) -> None:
    """Create tables and indexes. Alembic migrations mirror this schema."""

    statements = [
      """
      CREATE TABLE IF NOT EXISTS alerts (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          message TEXT NOT NULL,
          severity TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
          timestamp TEXT NOT NULL,
          source TEXT,
          tags TEXT NOT NULL DEFAULT '[]',
          acknowledged INTEGER NOT NULL DEFAULT 0,
          acknowledged_at TEXT
      )
      """,
      """
      CREATE TABLE IF NOT EXISTS reminders (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          description TEXT,
          datetime TEXT NOT NULL,
          recurring TEXT NOT NULL CHECK (recurring IN ('none','daily','weekly','monthly')),
          tags TEXT NOT NULL DEFAULT '[]',
          status TEXT NOT NULL CHECK (status IN ('pending','completed','dismissed')),
          created_at TEXT NOT NULL,
          notified_at TEXT
      )
      """,
      """
      CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY,
          title TEXT NOT NULL,
          description TEXT,
          start_datetime TEXT NOT NULL,
          end_datetime TEXT NOT NULL,
          location TEXT,
          attendees TEXT NOT NULL DEFAULT '[]',
          tags TEXT NOT NULL DEFAULT '[]',
          reminders TEXT NOT NULL DEFAULT '[15,30,60]',
          status TEXT NOT NULL CHECK (status IN ('scheduled','ongoing','completed','cancelled')),
          created_at TEXT NOT NULL
      )
      """,
      """
      CREATE TABLE IF NOT EXISTS notifications (
          id TEXT PRIMARY KEY,
          type TEXT NOT NULL CHECK (type IN ('alert','reminder','event')),
          message TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          tags TEXT NOT NULL DEFAULT '[]',
          timestamp TEXT NOT NULL,
          read_status INTEGER NOT NULL DEFAULT 0,
          read_at TEXT
      )
      """,
      """
      CREATE TABLE IF NOT EXISTS agent_conversations (
          id TEXT PRIMARY KEY,
          message TEXT NOT NULL,
          response TEXT NOT NULL,
          action_type TEXT NOT NULL,
          entity_type TEXT NOT NULL,
          tags TEXT NOT NULL DEFAULT '[]',
          context TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL
      )
      """,
      "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)",
      "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)",
      "CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged)",
      "CREATE INDEX IF NOT EXISTS idx_alerts_tags ON alerts(tags)",
      "CREATE INDEX IF NOT EXISTS idx_reminders_datetime ON reminders(datetime)",
      "CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status)",
      "CREATE INDEX IF NOT EXISTS idx_reminders_tags ON reminders(tags)",
      "CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON events(start_datetime)",
      "CREATE INDEX IF NOT EXISTS idx_events_end_datetime ON events(end_datetime)",
      "CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)",
      "CREATE INDEX IF NOT EXISTS idx_events_tags ON events(tags)",
      "CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp)",
      "CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type)",
      "CREATE INDEX IF NOT EXISTS idx_notifications_entity_id ON notifications(entity_id)",
      "CREATE INDEX IF NOT EXISTS idx_notifications_read_status ON notifications(read_status)",
      "CREATE INDEX IF NOT EXISTS idx_notifications_tags ON notifications(tags)",
    ]
    async with self.connection() as conn:
      for statement in statements:
        await asyncio.to_thread(conn.execute, statement)
    logger.info("Encrypted database initialized at %s", self.path)


def json_dumps(value: Any) -> str:
  return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def tags_filter_sql(tags: list[str], column: str = "tags") -> tuple[str, list[str]]:
  """Return SQL and params matching rows that contain every requested tag."""

  clauses: list[str] = []
  params: list[str] = []

  for tag in tags:
    clauses.append(f"EXISTS (SELECT 1 FROM json_each({column}) WHERE value = ?)")
    params.append(tag)

  return (" AND ".join(clauses), params)

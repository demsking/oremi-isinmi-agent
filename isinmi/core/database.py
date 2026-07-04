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
from collections.abc import Callable
from pathlib import Path
from typing import Any
from typing import TypeVar

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.engine import make_url
from sqlalchemy.engine import Result
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from .orm import Base
from .settings import Settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


def database_path(database_url: str) -> Path:
  """Extract a filesystem path from a SQLite-compatible database URL."""

  url = make_url(database_url)

  if not url.drivername.startswith("sqlite"):
    raise ValueError("database_path only supports SQLite database URLs")

  if not url.database:
    raise ValueError("SQLite database URL must include a path")

  return Path(url.database).expanduser()


class Database:
  """SQLAlchemy-backed persistence layer with SQLCipher support for SQLite."""

  def __init__(self, settings: Settings) -> None:
    self.settings = settings
    self._engine = self._build_engine()
    self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False, class_=Session)

  @property
  def engine(self) -> Engine:
    return self._engine

  def _build_engine(self) -> Engine:
    url = make_url(self.settings.database_url)

    if url.drivername.startswith("sqlite"):
      try:
        import sqlcipher3 as sqlite
      except ImportError as exc:
        raise RuntimeError("sqlcipher3 is required for encrypted SQLite storage") from exc

      database_file = database_path(self.settings.database_url)
      database_file.parent.mkdir(parents=True, exist_ok=True)

      engine = create_engine(
        f"sqlite:///{database_file.as_posix()}",
        connect_args={"check_same_thread": False},
        module=sqlite,
        future=True,
        pool_pre_ping=True,
      )

      encryption_key = self.settings.database_encryption_key.get_secret_value().replace("'", "''")

      @event.listens_for(engine, "connect")
      def _configure_sqlcipher(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.execute(f"PRAGMA key = '{encryption_key}'")
        dbapi_connection.execute("PRAGMA cipher_memory_security = ON")
        dbapi_connection.execute("PRAGMA foreign_keys = ON")
        dbapi_connection.execute("PRAGMA journal_mode = WAL")
        dbapi_connection.execute("SELECT count(*) FROM sqlite_master")

      return engine

    return create_engine(self.settings.database_url, future=True, pool_pre_ping=True)

  def _run_sync(self, operation: Callable[[Session], T]) -> T:
    with self._session_factory() as session:
      try:
        with session.begin():
          return operation(session)
      except SQLAlchemyError:
        session.rollback()
        raise
      except Exception:
        session.rollback()
        raise

  async def run(self, operation: Callable[[Session], T]) -> T:
    """Run a synchronous SQLAlchemy operation in a worker thread."""

    return await asyncio.to_thread(self._run_sync, operation)

  async def execute(self, statement: str, params: dict[str, Any] | tuple[Any, ...] | None = None) -> None:
    """Compatibility helper for legacy call sites."""

    def _operation(session: Session) -> None:
      session.connection().exec_driver_sql(statement, params or ())

    await self.run(_operation)

  async def fetch_one(
    self,
    statement: str,
    params: dict[str, Any] | tuple[Any, ...] | None = None,
  ) -> dict[str, Any] | None:
    """Compatibility helper for legacy call sites."""

    def _operation(session: Session) -> dict[str, Any] | None:
      result: Result[Any] = session.connection().exec_driver_sql(statement, params or ())
      row = result.mappings().first()
      return dict(row) if row is not None else None

    return await self.run(_operation)

  async def fetch_all(
    self,
    statement: str,
    params: dict[str, Any] | tuple[Any, ...] | None = None,
  ) -> list[dict[str, Any]]:
    """Compatibility helper for legacy call sites."""

    def _operation(session: Session) -> list[dict[str, Any]]:
      result: Result[Any] = session.connection().exec_driver_sql(statement, params or ())
      return [dict(row) for row in result.mappings().all()]

    return await self.run(_operation)

  async def initialize(self) -> None:
    """Create the database schema on startup."""

    await asyncio.to_thread(Base.metadata.create_all, self._engine)
    logger.info("Encrypted database initialized at %s", database_path(self.settings.database_url))

  async def dispose(self) -> None:
    """Dispose the underlying SQLAlchemy engine."""

    await asyncio.to_thread(self._engine.dispose)


def json_dumps(value: Any) -> str:
  """Serialize values for logging and JSON payload storage."""

  return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

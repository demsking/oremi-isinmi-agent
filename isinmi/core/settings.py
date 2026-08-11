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
import logging
from functools import lru_cache
from typing import Any
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from sqlalchemy.engine import make_url

logger = logging.Logger(__name__)


class Settings(BaseSettings):
  """Runtime settings loaded from environment variables and .env."""

  model_config = SettingsConfigDict(
    env_prefix="OREMI_ISINMI_",
    strict=True,
    extra="ignore",
  )

  server_host: str = Field(default="127.0.0.1", description="Host to bind the server.")
  server_port: int = Field(default=5073, ge=1, le=65535, description="Port to bind the server.")

  api_prefix: str = Field(default="/", description="API prefix for all endpoints.")

  sse_retry_timeout_seconds: int = Field(
    default=30,
    ge=1,
    le=120,
    description="SSE client retry interval in seconds.",
  )

  caldav_request_timeout_seconds: int = Field(
    default=30,
    ge=1,
    le=300,
    description=("Maximum time in seconds to wait for a CalDAV server response when performing HTTP requests."),
  )

  database_url: str = Field(default="sqlite:///./oremi_isinmi.db", description="Database connection URL.")
  database_encryption_key: SecretStr = Field(..., description="Encryption key for SQLite database.")

  log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", description="Logging level.")
  log_file: str | None = Field(default=None, description="Path to rotating log file.")

  @field_validator("api_prefix")
  @classmethod
  def validate_api_prefix(cls, value: str) -> str:
    if not value.startswith("/"):
      raise ValueError("OREMI_ISINMI_API_PREFIX must start with '/'")

    return value.rstrip("/") or "/"

  @field_validator("database_url")
  @classmethod
  def validate_database_url(cls, value: str) -> str:
    url = make_url(value)

    if not url.drivername.startswith(("sqlite", "postgresql", "mysql", "mariadb")):
      raise ValueError("OREMI_ISINMI_DATABASE_URL must use sqlite:///, postgresql://, mysql://, or mariadb://")

    return value

  @field_validator("database_encryption_key")
  @classmethod
  def validate_database_key(cls, value: SecretStr) -> SecretStr:
    if len(value.get_secret_value()) < 32:
      raise ValueError("OREMI_ISINMI_DATABASE_ENCRYPTION_KEY must be at least 32 characters long")

    return value


@lru_cache
def get_settings() -> Settings:
  """Return cached application settings."""
  return Settings(database_encryption_key=SecretStr("0" * 32))  # pyright: ignore


def _format(value: Any) -> str:
  if value is None:
    return "None"

  if isinstance(value, SecretStr):
    return "[set]"

  if isinstance(value, list):
    return ",".join(str(item) for item in value)

  return str(value)


def log_group(settings: Settings, name: str, *fields: str) -> None:
  """Log a group of related settings."""
  values: list[str] = []

  for field in fields:
    value = getattr(settings, field)
    values.append(f"{field}={_format(value)}")

  logger.info("%s Settings: %s", name, " ".join(values))

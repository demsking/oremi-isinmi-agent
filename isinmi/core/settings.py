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
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic import field_validator
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
  """Runtime settings loaded from environment variables and .env."""

  model_config = SettingsConfigDict(
    env_prefix="OREMI_ISINMI_",
    strict=True,
    extra="ignore",
  )

  server_host: str = Field(default="127.0.0.1", description="Host to bind the server.")
  server_port: int = Field(default=7337, description="Port to bind the server.")

  api_prefix: str = Field(default="/", description="API prefix for all endpoints.")
  sse_retry_timeout: int = Field(default=30000, ge=1000, le=120000, description="SSE retry timeout in milliseconds.")

  llm_model: str = Field(
    default="ollama:qwen3.5:2b",
    description="Fully qualified Pydantic-AI model identifier.",
  )

  llm_request_timeout: int = Field(
    default=15,
    ge=1,
    le=300,
    description="Request timeout in seconds for LLM calls and Ollama pulls when Ollama is the active backend.",
  )

  llm_temperature: float = Field(
    default=0.3,
    ge=0.0,
    le=2.0,
    description="Sampling temperature used by the configured LLM backend.",
  )

  llm_system_prompt: str = Field(
    default=(
      "You are Oremi, a friendly assistant that helps users manage their reminders "
      "and events. You understand natural language and can help users create, "
      "update, or manage their time commitments. Return a concise result-oriented response_message. "
      "Do not ask for more details unless they are required to complete the action. "
      "For query, list, and search_by_tags actions, summarize the requested result in one short sentence."
    ),
    description="System prompt for the AI agent.",
  )

  ollama_base_url: str | None = Field(
    default=None,
    description="Ollama API base URL used when the agent runs on Ollama.",
  )

  database_url: str = Field(default="sqlite:///./oremi_isinmi.db", description="Database connection URL.")
  database_encryption_key: SecretStr = Field(..., description="Encryption key for SQLite database.")

  log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
    default="INFO", description="Logging level."
  )
  log_file: str = Field(default="oremi_isinmi.log", description="Path to rotating log file.")

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

  def uses_ollama(self) -> bool:
    """Return whether the active agent model uses the Ollama backend."""

    return self.llm_model.startswith("ollama:")

  def resolve_ollama_model_name(self) -> str:
    """Return the Ollama model name without provider prefix."""
    return self.llm_model.removeprefix("ollama:")  # pylint: disable=no-member


@lru_cache
def get_settings() -> Settings:
  """Return cached application settings."""
  return Settings()

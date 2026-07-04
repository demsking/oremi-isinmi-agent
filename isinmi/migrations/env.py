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
from logging.config import fileConfig

from alembic import context

from isinmi.core.database import Database
from isinmi.core.orm import Base
from isinmi.core.settings import get_settings

config = context.config
if config.config_file_name is not None:
  fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
  settings = get_settings()
  context.configure(
    url=settings.database_url,
    target_metadata=target_metadata,
    literal_binds=True,
    compare_type=True,
  )

  with context.begin_transaction():
    context.run_migrations()


def run_migrations_online() -> None:
  settings = get_settings()
  database = Database(settings)

  try:
    with database.engine.connect() as connection:
      context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

      with context.begin_transaction():
        context.run_migrations()
  finally:
    database.engine.dispose()


if context.is_offline_mode():
  run_migrations_offline()
else:
  run_migrations_online()

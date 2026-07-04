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
import sys

from pydantic import ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError

from .core.app import create_app

logger = logging.getLogger(__name__)


try:
  app, settings = create_app()
except ValidationError as exc:
  logger.error("Invalid Oremi Isinmi configuration:")

  for error in exc.errors():
    logger.error("- %s: %s", ".".join(str(part) for part in error["loc"]), error["msg"])

  sys.exit(1)
except OperationalError as exc:
  logger.error(
    "Unable to open the encrypted database. "
    "Check that OREMI_ISINMI_DATABASE_URL points to a writable path inside the container "
    "and that the data volume is mounted. "
    f"{exc.orig or exc}",
  )

  sys.exit(2)
except SQLAlchemyError as exc:
  logger.error("Database initialization failed: %s", exc)
  sys.exit(3)
except RuntimeError as exc:
  logger.error("%s", exc)

  sys.exit(4)

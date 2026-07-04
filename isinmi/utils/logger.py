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
from logging.handlers import RotatingFileHandler
from pathlib import Path

from isinmi.core.package import APP_NAME


def configure_logging(level: str, log_file: str) -> None:
  """Configure console and rotating file logging."""

  formatter = logging.Formatter(
    fmt=f"%(asctime)s {APP_NAME} - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
  )

  root = logging.getLogger()
  root.setLevel(level)
  root.handlers.clear()

  console = logging.StreamHandler()
  console.setFormatter(formatter)
  root.addHandler(console)

  path = Path(log_file)
  path.parent.mkdir(parents=True, exist_ok=True)
  file_handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5)

  file_handler.setFormatter(formatter)
  root.addHandler(file_handler)

  for noisy_logger in ("watchfiles", "watchfiles.main"):
    logging.getLogger(noisy_logger).setLevel(logging.WARNING)

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
from datetime import datetime

from fastapi import HTTPException
from fastapi import Query

from isinmi.core.models import clean_tags


def parse_tags_query(tags: str | None = Query(default=None, description="Comma-separated tag list.")) -> list[str]:
  """Parse a comma-separated query parameter into normalized tags."""

  if not tags:
    return []

  return clean_tags([part for part in tags.split(",")])


def ensure_date_range(start: datetime | None, end: datetime | None) -> None:
  """Validate optional date range query parameters."""

  if start and end and end < start:
    raise HTTPException(status_code=422, detail="end date must be greater than or equal to start date")

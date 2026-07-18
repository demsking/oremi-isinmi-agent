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
from typing import Annotated
from typing import Literal

from fastapi import APIRouter
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi.openapi.models import Example

from isinmi.core.models import Notification
from isinmi.services.notification_service import NotificationService
from isinmi.utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "Notifications Endpoints",
  "description": (
    "Notification inbox operations for reminders and events. Notifications are the user-facing messages "
    "generated from scheduled reminders and calendar event reminders. Use these endpoints to build unread "
    "badges, notification centers, tag-filtered notification views, and read-state workflows."
  ),
}

router = APIRouter(prefix="/notifications", tags=[API_TAG_METADATA["name"]])

NOTIFICATION_LIST_QUERY_EXAMPLES: dict[str, Example] = {
  "unread": {
    "summary": "Unread notifications",
    "description": "Show only unread notifications.",
    "value": False,
  },
}

NOTIFICATION_ID_PATH_EXAMPLES: dict[str, Example] = {
  "sample_notification_id": {
    "summary": "Notification identifier",
    "description": "A notification ID returned by the API.",
    "value": "notification_123",
  }
}


def service(request: Request) -> NotificationService:
  return request.app.state.notification_service


@router.get(
  "/",
  operation_id="list_notifications",
  response_model=list[Notification],
  summary="List notifications",
  description=(
    "List notification messages with optional filters for notification type, tags, read status, and "
    "pagination. Use this endpoint for notification centers, activity feeds, and assistant summaries "
    "without needing a separate tag-only route."
  ),
)
async def list_notifications(
  request: Request,
  type_: Literal["reminder", "event"] | None = Query(
    default=None,
    alias="type",
    description="Notification type filter.",
    openapi_examples={
      "reminder": {"summary": "Reminder notifications", "value": "reminder"},
      "event": {"summary": "Event notifications", "value": "event"},
    },
  ),
  tags: str | None = Query(
    default=None,
    description="Comma-separated tags.",
    openapi_examples=NOTIFICATION_LIST_QUERY_EXAMPLES,
  ),
  read_status: bool | None = Query(
    default=None,
    description="Read status filter.",
    openapi_examples={
      "unread": {"summary": "Unread notifications", "value": False},
      "read": {"summary": "Read notifications", "value": True},
    },
  ),
  limit: int = Query(
    default=100,
    ge=1,
    le=500,
    description="Maximum records to return.",
    openapi_examples={
      "default": {"summary": "Default page size", "value": 100},
      "compact": {"summary": "Compact page", "value": 25},
    },
  ),
  offset: int = Query(
    default=0,
    ge=0,
    description="Number of records to skip.",
    openapi_examples={
      "first_page": {"summary": "First page", "value": 0},
      "later_page": {"summary": "Later page", "value": 50},
    },
  ),
) -> list[Notification]:
  return await service(request).list(type_, parse_tags_query(tags), read_status, limit, offset)


@router.get(
  "/unread/count",
  operation_id="get_unread_count",
  summary="Unread count",
  description=(
    "Return the number of unread notifications. Use this for badges, tray indicators, mobile widgets, "
    "and assistant prompts that tell the user how many items need attention."
  ),
)
async def unread_count(request: Request) -> dict[str, int]:
  return await service(request).unread_count()


@router.put(
  "/{notification_id}/read",
  operation_id="mark_notification_read",
  response_model=Notification,
  summary="Mark notification read",
  description=(
    "Mark a single notification as read and record when it was read. This is useful when the user opens "
    "one notification from a feed without clearing the rest."
  ),
)
async def mark_read(
  notification_id: Annotated[
    str,
    Path(..., description="Notification identifier.", openapi_examples=NOTIFICATION_ID_PATH_EXAMPLES),
  ],
  request: Request,
) -> Notification:
  return await service(request).mark_read(notification_id)


@router.put(
  "/read/all",
  operation_id="mark_all_notifications_read",
  summary="Mark all notifications read",
  description=(
    "Mark every unread notification as read in one operation. Use this when the user clears their "
    "notification center or says something like `mark everything as read`. Optional tags can limit the "
    "operation to a specific device, UUID, user, or workflow."
  ),
)
async def mark_all_read(
  request: Request,
  tags: str | None = Query(
    default=None,
    description="Comma-separated tags to scope the read operation.",
    openapi_examples={
      "work": {"summary": "Device-specific notifications", "value": "device_id:web-app,user_id:alex"},
      "device": {"summary": "User-scoped notifications", "value": "device_id:phone-1,user_id:alex"},
    },
  ),
) -> dict[str, int | str]:
  return await service(request).mark_all_read(parse_tags_query(tags))

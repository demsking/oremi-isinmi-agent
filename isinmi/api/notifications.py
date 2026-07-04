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
from typing import Literal

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request

from isinmi.core.models import Notification
from isinmi.services.notification_service import NotificationService
from isinmi.utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "Notifications Endpoints",
  "description": (
    "Notification inbox operations for alerts, reminders, and events. Notifications are the user-facing "
    "messages generated from scheduled reminders, calendar event reminders, and alerts. Use these endpoints "
    "to build unread badges, notification centers, tag-filtered notification views, and read-state workflows."
  ),
}

router = APIRouter(prefix="/notifications", tags=[API_TAG_METADATA["name"]])


def service(request: Request) -> NotificationService:
  return request.app.state.notification_service


@router.get(
  "/",
  operation_id="list_notifications",
  response_model=list[Notification],
  summary="List notifications",
  description=(
    "List notification messages with optional filters for notification type, tags, read status, and "
    "pagination. Use this endpoint for notification centers, activity feeds, and assistant summaries."
  ),
)
async def list_notifications(
  request: Request,
  type_: Literal["alert", "reminder", "event"] | None = Query(
    default=None,
    alias="type",
    description="Notification type filter.",
  ),
  tags: str | None = Query(default=None, description="Comma-separated tags."),
  read_status: bool | None = Query(default=None, description="Read status filter."),
  limit: int = Query(default=100, ge=1, le=500, description="Maximum records to return."),
  offset: int = Query(default=0, ge=0, description="Number of records to skip."),
) -> list[Notification]:
  return await service(request).list(type_, parse_tags_query(tags), read_status, limit, offset)


@router.get(
  "/by-tags/",
  operation_id="get_notifications_by_tags",
  response_model=list[Notification],
  summary="Get notifications by tags",
  description=(
    "Return notifications that contain every requested tag. This lets clients show focused notification "
    "streams such as `family`, `home`, `health`, `school`, or `urgent`."
  ),
)
async def notifications_by_tags(
  request: Request,
  tags: str = Query(..., description="Comma-separated tags."),
  limit: int = Query(default=100, ge=1, le=500, description="Maximum records to return."),
  offset: int = Query(default=0, ge=0, description="Number of records to skip."),
) -> list[Notification]:
  return await service(request).list(None, parse_tags_query(tags), None, limit, offset)


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
async def mark_read(notification_id: str, request: Request) -> Notification:
  return await service(request).mark_read(notification_id)


@router.put(
  "/read/all",
  operation_id="mark_all_notifications_read",
  summary="Mark all notifications read",
  description=(
    "Mark every unread notification as read in one operation. Use this when the user clears their "
    "notification center or says something like `mark everything as read`."
  ),
)
async def mark_all_read(request: Request) -> dict[str, str]:
  return await service(request).mark_all_read()

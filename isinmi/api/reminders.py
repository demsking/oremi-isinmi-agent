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
from typing import Annotated
from typing import cast
from typing import Literal

from fastapi import APIRouter
from fastapi import Body
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi.openapi.models import Example

from isinmi.core.models import Reminder
from isinmi.core.models import ReminderCreate
from isinmi.core.models import ReminderUpdate
from isinmi.services.reminder_service import ReminderService
from isinmi.utils.validators import ensure_date_range
from isinmi.utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "Reminders Endpoints",
  "description": (
    "Reminder creation and lifecycle management. Reminders are personal-assistant tasks with a trigger time, "
    "optional recurrence, status tracking, and tags. Use this group for chores, medication, school pickup, "
    "bills, errands, and any time-based nudge the user wants Oremi Isinmi to remember."
  ),
}

router = APIRouter(prefix="/reminders", tags=[API_TAG_METADATA["name"]])

REMINDER_CREATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "school_pickup": {
    "summary": "School pickup",
    "description": "A parent asks the assistant to remind them before school pickup.",
    "value": {
      "title": "Pick up Amara from school",
      "description": "Leave by 3:10 PM to avoid traffic.",
      "datetime": "2026-07-03T15:00:00",
      "recurring": "none",
      "tags": ["device_id:phone-1", "user_id:alex"],
    },
  },
  "trash_night": {
    "summary": "Household chore",
    "description": "A recurring home reminder similar to an Alexa household routine.",
    "value": {
      "title": "Take the bins to the curb",
      "description": "Put recycling and trash outside after dinner.",
      "datetime": "2026-07-07T19:30:00",
      "recurring": "weekly",
      "tags": ["device_id:kitchen-hub", "user_id:alex"],
    },
  },
  "daily_medication": {
    "summary": "Recurring health reminder",
    "description": "A daily medication reminder with a health tag.",
    "value": {
      "title": "Take blood pressure medication",
      "description": "Take one tablet with water after dinner.",
      "datetime": "2026-07-03T20:00:00",
      "recurring": "daily",
      "tags": ["device_id:phone-1", "user_id:alex"],
    },
  },
  "bill_due": {
    "summary": "Bill reminder",
    "description": "A personal finance reminder for a recurring monthly bill.",
    "value": {
      "title": "Pay electricity bill",
      "description": "Pay before the due date to avoid late fees.",
      "datetime": "2026-07-25T09:00:00",
      "recurring": "monthly",
      "tags": ["device_id:web-app", "user_id:alex"],
    },
  },
}

REMINDER_RESPONSE_EXAMPLE = Reminder.model_validate(
  {
    "id": "reminder_123",
    "title": "Pick up Amara from school",
    "description": "Leave by 3:10 PM to avoid traffic.",
    "datetime": "2026-07-03T15:00:00",
    "recurring": "none",
    "tags": ["device_id:phone-1", "user_id:alex"],
    "status": "pending",
    "created_at": "2026-07-03T10:20:00",
    "notified_at": None,
  }
)

REMINDER_UPDATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "add_detail": {
    "summary": "Add reminder detail",
    "description": "Update a family reminder after the user gives more context.",
    "value": {
      "title": "Pick up Amara and Noah from school",
      "description": "Bring the booster seat and park near the side gate.",
      "tags": ["device_id:phone-1", "user_id:alex"],
    },
  },
  "reschedule": {
    "summary": "Reschedule reminder",
    "description": "Move a reminder because the user's plan changed.",
    "value": {
      "datetime": "2026-07-03T15:20:00",
    },
  },
  "dismiss": {
    "summary": "Dismiss reminder",
    "description": "Mark the reminder as dismissed.",
    "value": {
      "status": "dismissed",
    },
  },
}

REMINDER_LIST_QUERY_EXAMPLES: dict[str, Example] = {
  "today": {
    "summary": "Today's reminders",
    "description": "Show reminders due today.",
    "value": "2026-07-03T00:00:00,2026-07-03T23:59:59",
  },
  "home": {
    "summary": "Home reminders",
    "description": "Filter reminders tagged for home organization.",
    "value": "device_id:phone-1,user_id:alex",
  },
  "upcoming": {
    "summary": "Upcoming reminders",
    "description": "List pending reminders due within the next 24 hours.",
    "value": "true",
  },
}

REMINDER_ID_PATH_EXAMPLES: dict[str, Example] = {
  "sample_reminder_id": {
    "summary": "Reminder identifier",
    "description": "A reminder ID returned by the API.",
    "value": "reminder_123",
  }
}


def service(request: Request) -> ReminderService:
  return cast(ReminderService, request.app.state.reminder_service)


@router.post(
  "/",
  operation_id="create_reminder",
  response_model=Reminder,
  status_code=201,
  summary="Create reminder",
  description="""
    Create a new reminder with a title, trigger datetime, optional description,
    recurrence, and tags. Use this for everyday assistant scenarios such as
    school pickup, taking medication, putting bins outside, paying bills, or
    remembering an errand. The reminder is stored in the encrypted database and
    appears in the list endpoint, including the `upcoming=true` view and tag
    filtered queries.
  """,
  responses={
    201: {
      "content": {
        "application/json": {
          "example": REMINDER_RESPONSE_EXAMPLE,
        },
      },
    },
  },
)
async def create_reminder(
  request: Request,
  payload: ReminderCreate = Body(
    ...,
    description="Reminder details including title, trigger datetime, recurrence, and tags.",
    openapi_examples=REMINDER_CREATE_OPENAPI_EXAMPLES,
  ),
) -> Reminder:
  return await service(request).create(payload)


@router.get(
  "/",
  operation_id="list_reminders",
  response_model=list[Reminder],
  summary="List reminders",
  description=(
    "List reminders with optional filters for status, date range, tags, and pagination. This endpoint powers "
    "reminder inboxes, calendar sidebars, upcoming reminder views, and assistant queries like `what reminders "
    "do I have today`, `show my health reminders`, or `show my upcoming reminders`."
  ),
)
async def list_reminders(
  request: Request,
  status: Literal["pending", "completed", "dismissed"] | None = Query(
    default=None,
    description="Reminder status filter.",
    openapi_examples={
      "pending": {"summary": "Pending reminders", "value": "pending"},
      "completed": {"summary": "Completed reminders", "value": "completed"},
      "dismissed": {"summary": "Dismissed reminders", "value": "dismissed"},
    },
  ),
  start: datetime | None = Query(
    default=None,
    description="Start datetime filter.",
    openapi_examples={
      "morning": {"summary": "From morning", "value": "2026-07-03T08:00:00"},
      "week_start": {"summary": "Week start", "value": "2026-07-06T00:00:00"},
    },
  ),
  end: datetime | None = Query(
    default=None,
    description="End datetime filter.",
    openapi_examples={
      "evening": {"summary": "Until evening", "value": "2026-07-03T20:00:00"},
      "week_end": {"summary": "Week end", "value": "2026-07-12T23:59:59"},
    },
  ),
  tags: str | None = Query(
    default=None,
    description="Comma-separated tags, for example device_id:phone-1,user_id:alex.",
    openapi_examples=REMINDER_LIST_QUERY_EXAMPLES,
  ),
  upcoming: bool = Query(
    default=False,
    description="If true, return pending reminders due in the next 24 hours.",
    openapi_examples={
      "default": {"summary": "Do not limit to upcoming", "value": False},
      "upcoming": {"summary": "Only upcoming reminders", "value": True},
    },
  ),
  limit: int = Query(
    default=100,
    ge=1,
    le=500,
    description="Maximum records to return.",
    openapi_examples={
      "default": {"summary": "Default page size", "value": 100},
      "compact": {"summary": "Compact page", "value": 10},
    },
  ),
  offset: int = Query(
    default=0,
    ge=0,
    description="Number of records to skip.",
    openapi_examples={
      "first_page": {"summary": "First page", "value": 0},
      "later_page": {"summary": "Later page", "value": 30},
    },
  ),
) -> list[Reminder]:
  """
  This endpoint allows you to retrieve a list of reminders based on various filters.

  You can filter reminders by status, date range, tags, and the upcoming flag.
  When `upcoming=true`, the endpoint returns pending reminders due in the next
  24 hours. The results can be paginated using the limit and offset parameters.
  If no filters are provided, all reminders will be returned.
  """
  ensure_date_range(start, end)
  return await service(request).list_reminders(status, start, end, parse_tags_query(tags), upcoming, limit, offset)


@router.put(
  "/{reminder_id}",
  operation_id="update_reminder",
  response_model=Reminder,
  summary="Update reminder",
  description=(
    "Partially update an existing reminder. Use this when the user changes a reminder time, adds detail, "
    "changes recurrence, edits tags, or moves the reminder into another status."
  ),
)
async def update_reminder(
  reminder_id: Annotated[
    str,
    Path(..., description="Reminder identifier.", openapi_examples=REMINDER_ID_PATH_EXAMPLES),
  ],
  request: Request,
  payload: ReminderUpdate = Body(
    ...,
    description="Partial reminder fields to update.",
    openapi_examples=REMINDER_UPDATE_OPENAPI_EXAMPLES,
  ),
) -> Reminder:
  return await service(request).update(reminder_id, payload)


@router.put(
  "/{reminder_id}/complete",
  operation_id="complete_reminder",
  response_model=Reminder,
  summary="Complete reminder",
  description=(
    "Mark a reminder as completed after the user has handled it. Completed reminders stay in history and can "
    "be filtered separately from pending or dismissed reminders."
  ),
)
async def complete_reminder(
  reminder_id: Annotated[
    str,
    Path(..., description="Reminder identifier.", openapi_examples=REMINDER_ID_PATH_EXAMPLES),
  ],
  request: Request,
) -> Reminder:
  return await service(request).complete(reminder_id)


@router.delete(
  "/{reminder_id}",
  operation_id="delete_reminder",
  summary="Delete reminder",
  description=(
    "Delete a reminder permanently by ID. Use this when the user removes an obsolete reminder instead of "
    "marking it completed or dismissed."
  ),
)
async def delete_reminder(
  reminder_id: Annotated[
    str,
    Path(..., description="Reminder identifier.", openapi_examples=REMINDER_ID_PATH_EXAMPLES),
  ],
  request: Request,
) -> dict[str, str]:
  return await service(request).delete(reminder_id)

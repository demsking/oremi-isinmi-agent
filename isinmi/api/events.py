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
import asyncio
from datetime import datetime
from typing import Annotated
from typing import Literal

from fastapi import APIRouter
from fastapi import Body
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi.openapi.models import Example
from sse_starlette.sse import EventSourceResponse

from isinmi.core.models import Event
from isinmi.core.models import EventCreate
from isinmi.core.models import EventUpdate
from isinmi.core.settings import Settings
from isinmi.services.event_service import EventService
from isinmi.sse.manager import SSEManager
from isinmi.utils.validators import ensure_date_range
from isinmi.utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "Events Endpoints",
  "description": (
    "Calendar event scheduling and live event delivery. Use these endpoints to create personal appointments, "
    "family plans, work meetings, and tagged calendar entries. This group also exposes the Server-Sent Events "
    "stream used by clients to receive reminder notifications, event reminders, and keepalive pings without "
    "polling."
  ),
}

router = APIRouter(prefix="/events", tags=[API_TAG_METADATA["name"]])

MCP_EXCLUDED_OPERATIONS: list[str] = [
  "stream_events",
]

SSE_STREAM_DESCRIPTION = """
Open a Server-Sent Events (SSE) subscription for real-time Oremi Isinmi notifications.

SSE is a lightweight HTTP streaming protocol where the server keeps one response
open and sends text frames as events happen. It is ideal for personal-assistant
notifications because browsers support it natively with `EventSource`, it
automatically reconnects, and it avoids repeated polling for new reminders or
events.

Clients may pass `tags=device_id:iphone-14,user_id:alex` to receive only events whose notification
tags overlap the requested tag set. If no tags are provided, the client receives
all live events. The stream emits named events such as `new_reminder`,
`new_event`, and `ping`. Event payloads are JSON strings.

**JavaScript example**

```javascript
const stream = new EventSource("http://localhost:7337/api/events/stream?tags=device_id:iphone-14,user_id:alex");

stream.addEventListener("new_reminder", (event) => {
  const reminder = JSON.parse(event.data);
  console.log("Reminder:", reminder.message, reminder.tags);
});

stream.addEventListener("ping", () => {
  console.debug("Oremi stream heartbeat");
});

stream.onerror = () => {
  console.warn("SSE connection interrupted; the browser will retry automatically.");
};
```

**Python example**

```python
import json
import httpx

url = "http://localhost:7337/api/events/stream?tags=device_id:iphone-14,user_id:alex"

with httpx.stream("GET", url, timeout=None) as response:
  response.raise_for_status()
  event_name = "message"

  for line in response.iter_lines():
    if line.startswith("event:"):
      event_name = line.removeprefix("event:").strip()
    elif line.startswith("data:"):
      payload = json.loads(line.removeprefix("data:").strip())
      print(event_name, payload)
    elif line == "":
      event_name = "message"
```
"""

EVENT_CREATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "doctor_appointment": {
    "summary": "Doctor appointment",
    "description": "A personal assistant schedules a health appointment with travel-time reminders.",
    "value": {
      "title": "Doctor appointment",
      "description": "Annual checkup with Dr. Martin.",
      "start_datetime": "2026-07-06T09:30:00",
      "end_datetime": "2026-07-06T10:15:00",
      "location": "City Health Clinic",
      "attendees": [],
      "tags": ["device_id:phone-1", "user_id:alex"],
      "reminders": [30, 60],
    },
  },
  "family_dinner": {
    "summary": "Family dinner",
    "description": "A household calendar event with attendees and a location.",
    "value": {
      "title": "Dinner with Mom",
      "description": "Birthday dinner reservation.",
      "start_datetime": "2026-07-10T19:00:00",
      "end_datetime": "2026-07-10T21:00:00",
      "location": "Bistro Lumiere",
      "attendees": ["Mom", "Tola"],
      "tags": ["device_id:phone-1", "user_id:alex"],
      "reminders": [120, 30],
    },
  },
  "team_sync": {
    "summary": "Work meeting",
    "description": "A work calendar event created from a personal-assistant scheduling request.",
    "value": {
      "title": "Weekly team sync",
      "description": "Review priorities, blockers, and Friday demo agenda.",
      "start_datetime": "2026-07-06T11:00:00",
      "end_datetime": "2026-07-06T11:30:00",
      "location": "Zoom",
      "attendees": ["ada@example.com", "marc@example.com"],
      "tags": ["device_id:laptop-1", "user_id:alex"],
      "reminders": [10],
    },
  },
}

EVENT_RESPONSE_EXAMPLE = Event.model_validate(
  {
    "id": "event_123",
    "title": "Doctor appointment",
    "description": "Annual checkup with Dr. Martin.",
    "start_datetime": "2026-07-06T09:30:00",
    "end_datetime": "2026-07-06T10:15:00",
    "location": "City Health Clinic",
    "attendees": [],
    "tags": ["device_id:phone-1", "user_id:alex"],
    "reminders": [30, 60],
    "status": "scheduled",
    "created_at": "2026-07-03T10:20:00",
  }
)

EVENT_UPDATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "change_restaurant": {
    "summary": "Change dinner location",
    "description": "Update a family dinner after the reservation changes.",
    "value": {
      "location": "Le Jardin",
      "description": "Birthday dinner reservation moved to Le Jardin.",
      "tags": ["device_id:phone-1", "user_id:alex"],
    },
  },
  "reschedule": {
    "summary": "Reschedule event",
    "description": "Move an appointment to a new time.",
    "value": {
      "start_datetime": "2026-07-06T10:30:00",
      "end_datetime": "2026-07-06T11:15:00",
    },
  },
  "cancel": {
    "summary": "Cancel event",
    "description": "Mark the event as cancelled.",
    "value": {
      "status": "cancelled",
    },
  },
}

EVENT_STREAM_QUERY_EXAMPLES: dict[str, Example] = {
  "family": {
    "summary": "Family events",
    "description": "Stream only events tagged for family planning.",
    "value": "device_id:phone-1,user_id:alex",
  },
  "work": {
    "summary": "Work events",
    "description": "Stream only work-related notification events.",
    "value": "device_id:laptop-1,user_id:alex",
  },
}

EVENT_LIST_QUERY_EXAMPLES: dict[str, Example] = {
  "work_week": {
    "summary": "Work week events",
    "description": "Filter events that happen during the work week.",
    "value": "2026-07-06T00:00:00,2026-07-10T23:59:59",
  },
  "tagged": {
    "summary": "Tagged events",
    "description": "Filter events by tags only.",
    "value": "device_id:laptop-1,user_id:alex",
  },
}

EVENT_ID_PATH_EXAMPLES: dict[str, Example] = {
  "sample_event_id": {
    "summary": "Event identifier",
    "description": "A real-looking event ID returned by the API.",
    "value": "event_123",
  }
}


def service(request: Request) -> EventService:
  return request.app.state.event_service


def sse_manager(request: Request) -> SSEManager:
  return request.app.state.sse_manager


def settings(request: Request) -> Settings:
  return request.app.state.settings


@router.get(
  "/stream",
  operation_id="stream_events",
  response_class=EventSourceResponse,
  summary="Stream live notifications",
  description=SSE_STREAM_DESCRIPTION,
)
async def stream_events(
  request: Request,
  tags: str | None = Query(
    default=None,
    description="Comma-separated tag filter.",
    openapi_examples=EVENT_STREAM_QUERY_EXAMPLES,
  ),
) -> EventSourceResponse:
  manager = sse_manager(request)
  subscriber = await manager.subscribe(parse_tags_query(tags))
  sse_retry_timeout_seconds = settings(request).sse_retry_timeout_seconds
  sse_retry_timeout_miliseconds = sse_retry_timeout_seconds * 1000

  async def event_generator():
    try:
      yield {"retry": sse_retry_timeout_miliseconds}

      while True:
        if await request.is_disconnected():
          break

        try:
          yield await asyncio.wait_for(subscriber.queue.get(), timeout=15)
        except TimeoutError:
          yield {"event": "ping", "data": "{}"}
    finally:
      await manager.unsubscribe(subscriber.id)

  return EventSourceResponse(event_generator(), ping=15)


@router.post(
  "/",
  operation_id="create_event",
  response_model=Event,
  status_code=201,
  summary="Create event",
  description=(
    "Create a calendar event for an appointment, family plan, work meeting, or other time commitment. "
    "The event stores start/end times, optional location and attendees, tags for organization, and reminder "
    "offsets in minutes before the event."
  ),
  responses={201: {"content": {"application/json": {"example": EVENT_RESPONSE_EXAMPLE}}}},
)
async def create_event(
  request: Request,
  payload: EventCreate = Body(
    ...,
    description="Event details including start/end times, attendees, reminders, and tags.",
    openapi_examples=EVENT_CREATE_OPENAPI_EXAMPLES,
  ),
) -> Event:
  return await service(request).create(payload)


@router.get(
  "/",
  operation_id="list_events",
  response_model=list[Event],
  summary="List events",
  description=(
    "Return calendar events matching optional filters. Use this endpoint to show a user's upcoming schedule, "
    "review completed or cancelled events, filter by date windows, or narrow results to tags such as "
    "`family`, `health`, `work`, or `school` without needing a separate tag-only endpoint."
  ),
)
async def list_events(
  request: Request,
  status: Literal["scheduled", "ongoing", "completed", "cancelled"] | None = Query(
    default=None,
    description="Event status filter.",
    openapi_examples={
      "scheduled": {"summary": "Scheduled events", "value": "scheduled"},
      "ongoing": {"summary": "Ongoing events", "value": "ongoing"},
      "completed": {"summary": "Completed events", "value": "completed"},
      "cancelled": {"summary": "Cancelled events", "value": "cancelled"},
    },
  ),
  start: datetime | None = Query(
    default=None,
    description="Start datetime filter.",
    openapi_examples={
      "week_start": {"summary": "Week start", "value": "2026-07-06T00:00:00"},
      "tomorrow": {"summary": "Tomorrow morning", "value": "2026-07-04T08:00:00"},
    },
  ),
  end: datetime | None = Query(
    default=None,
    description="End datetime filter.",
    openapi_examples={
      "week_end": {"summary": "Week end", "value": "2026-07-12T23:59:59"},
      "tomorrow_end": {"summary": "Tomorrow evening", "value": "2026-07-04T20:00:00"},
    },
  ),
  tags: str | None = Query(
    default=None,
    description="Comma-separated tags.",
    openapi_examples=EVENT_LIST_QUERY_EXAMPLES,
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
) -> list[Event]:
  ensure_date_range(start, end)
  return await service(request).list(status, start, end, parse_tags_query(tags), limit, offset)


@router.get(
  "/{event_id}",
  operation_id="get_event",
  response_model=Event,
  summary="Get event",
  description=(
    "Fetch one event by its unique ID. Use this when a client needs complete event details before showing, "
    "editing, cancelling, or confirming a scheduled commitment."
  ),
)
async def get_event(
  event_id: Annotated[str, Path(..., description="Event identifier.", openapi_examples=EVENT_ID_PATH_EXAMPLES)],
  request: Request,
) -> Event:
  return await service(request).get(event_id)


@router.put(
  "/{event_id}",
  operation_id="update_event",
  response_model=Event,
  summary="Update event",
  description=(
    "Partially update an existing event. Clients can reschedule the start/end time, change the location, "
    "adjust attendees or reminder offsets, revise tags, or mark the event as completed or cancelled."
  ),
)
async def update_event(
  event_id: Annotated[str, Path(..., description="Event identifier.", openapi_examples=EVENT_ID_PATH_EXAMPLES)],
  request: Request,
  payload: EventUpdate = Body(
    ...,
    description="Partial event fields to update.",
    openapi_examples=EVENT_UPDATE_OPENAPI_EXAMPLES,
  ),
) -> Event:
  return await service(request).update(event_id, payload)


@router.delete(
  "/{event_id}",
  operation_id="delete_event",
  summary="Delete event",
  description=(
    "Delete an event permanently by ID. Use this for events the user no longer wants Oremi Isinmi to track "
    "or include in calendar and tag searches."
  ),
)
async def delete_event(
  event_id: Annotated[str, Path(..., description="Event identifier.", openapi_examples=EVENT_ID_PATH_EXAMPLES)],
  request: Request,
) -> dict[str, str]:
  return await service(request).delete(event_id)

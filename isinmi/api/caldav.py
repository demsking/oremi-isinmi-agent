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
from typing import cast

from fastapi import APIRouter
from fastapi import Body
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Request
from fastapi.openapi.models import Example

from isinmi.core.models import CalDAVAccount
from isinmi.core.models import CalDAVAccountCreate
from isinmi.core.models import CalDAVAccountUpdate
from isinmi.core.models import CalDAVSyncResult
from isinmi.integrations.caldav.service import CalDAVSyncService as CalDAVService
from isinmi.utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "CalDAV Endpoints",
  "description": (
    "Integration endpoints for CalDAV calendars. Use these endpoints to register remote calendar accounts, "
    "store credentials securely inside the encrypted local database, and synchronize local Oremi events with "
    "external CalDAV servers. The integration uses iCalendar event payloads and mirrors only the local events "
    "that match the account tag filters."
  ),
}

router = APIRouter(prefix="/caldav", tags=[API_TAG_METADATA["name"]])

CALDAV_ACCOUNT_CREATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "work_calendar": {
    "summary": "Work calendar account",
    "description": "A CalDAV account that syncs work events to a corporate calendar.",
    "value": {
      "name": "Work Calendar",
      "base_url": "https://cal.example.com",
      "calendar_url": "https://cal.example.com/calendars/work/",
      "username": "alice",
      "password": "replace-with-an-app-password",
      "tags": ["device_id:laptop-1", "user_id:alex"],
      "is_active": True,
    },
  },
  "family_calendar": {
    "summary": "Family calendar account",
    "description": "A CalDAV account used for household events and school planning.",
    "value": {
      "name": "Family Calendar",
      "base_url": "https://calendar.family.example",
      "calendar_url": "https://calendar.family.example/caldav/family/",
      "username": "family-admin",
      "password": "replace-with-an-app-password",
      "tags": ["device_id:phone-1", "user_id:alex"],
      "is_active": True,
    },
  },
}

CALDAV_ACCOUNT_UPDATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "rotate_password": {
    "summary": "Rotate credentials",
    "description": "Update the account password after an app password rotation.",
    "value": {
      "password": "replace-with-a-new-app-password",
    },
  },
  "disable_account": {
    "summary": "Disable account",
    "description": "Temporarily disable synchronization for this account.",
    "value": {
      "is_active": False,
    },
  },
}

CALDAV_ACCOUNT_ID_PATH_EXAMPLES: dict[str, Example] = {
  "sample_caldav_account_id": {
    "summary": "CalDAV account identifier",
    "description": "A stored CalDAV account ID returned by the API.",
    "value": "caldav_123",
  }
}

CALDAV_SYNC_TAG_QUERY_EXAMPLES: dict[str, Example] = {
  "work": {
    "summary": "Work events",
    "description": "Sync only work-tagged local events.",
    "value": "device_id:laptop-1,user_id:alex",
  },
  "family": {
    "summary": "Family events",
    "description": "Sync only family-tagged local events.",
    "value": "device_id:phone-1,user_id:alex",
  },
}


def service(request: Request) -> CalDAVService:
  return cast(CalDAVService, request.app.state.caldav_service)


@router.post(
  "/accounts/",
  response_model=CalDAVAccount,
  summary="Create a CalDAV account",
  description=(
    "Register a remote CalDAV calendar account. The account is stored locally in the encrypted database and "
    "can be restricted to specific client tags so that only matching events are synchronized."
  ),
)
async def create_account(
  request: Request,
  payload: CalDAVAccountCreate = Body(
    ...,
    description="CalDAV account details and credentials.",
    openapi_examples=CALDAV_ACCOUNT_CREATE_OPENAPI_EXAMPLES,
  ),
) -> CalDAVAccount:
  return await service(request).create_account(payload)


@router.get(
  "/accounts/",
  response_model=list[CalDAVAccount],
  summary="List CalDAV accounts",
  description=(
    "Return all configured CalDAV accounts. Use `active_only=true` to display only the accounts that currently "
    "participate in synchronization."
  ),
)
async def list_accounts(
  request: Request,
  active_only: bool = Query(
    default=False,
    description="Filter to active CalDAV accounts only.",
    openapi_examples={
      "all": {"summary": "All accounts", "value": False},
      "active": {"summary": "Active accounts only", "value": True},
    },
  ),
) -> list[CalDAVAccount]:
  return await service(request).list_accounts(active_only=active_only)


@router.put(
  "/accounts/{account_id}",
  response_model=CalDAVAccount,
  summary="Update a CalDAV account",
  description="Update CalDAV account details, credentials, or tag filters.",
)
async def update_account(
  account_id: Annotated[
    str,
    Path(..., description="CalDAV account identifier.", openapi_examples=CALDAV_ACCOUNT_ID_PATH_EXAMPLES),
  ],
  request: Request,
  payload: CalDAVAccountUpdate = Body(
    ...,
    description="Updated CalDAV account values.",
    openapi_examples=CALDAV_ACCOUNT_UPDATE_OPENAPI_EXAMPLES,
  ),
) -> CalDAVAccount:
  account = await service(request).update_account(account_id, payload)

  if account is None:
    raise HTTPException(status_code=404, detail="CalDAV account not found")

  return account


@router.delete(
  "/accounts/{account_id}",
  summary="Delete a CalDAV account",
  description="Remove a CalDAV account and its associated sync links from local storage.",
)
async def delete_account(
  account_id: Annotated[
    str,
    Path(..., description="CalDAV account identifier.", openapi_examples=CALDAV_ACCOUNT_ID_PATH_EXAMPLES),
  ],
  request: Request,
) -> dict[str, str]:
  deleted = await service(request).delete_account(account_id)

  if not deleted:
    raise HTTPException(status_code=404, detail="CalDAV account not found")

  return {"status": "deleted"}


@router.post(
  "/sync/events/{event_id}",
  response_model=list[CalDAVSyncResult],
  summary="Sync one event to CalDAV",
  description=(
    "Synchronize a single local event with every active CalDAV account whose tag filters match the event tags. "
    "The event is rendered as iCalendar and pushed to the remote calendar using CalDAV `PUT`."
  ),
)
async def sync_event(
  event_id: Annotated[
    str,
    Path(
      ...,
      description="Local event identifier.",
      openapi_examples={
        "sample_event_id": {
          "summary": "Event identifier",
          "description": "A local event ID returned by the API.",
          "value": "event_123",
        }
      },
    ),
  ],
  request: Request,
) -> list[CalDAVSyncResult]:
  return await service(request).sync_event(event_id)


@router.post(
  "/sync/events",
  response_model=list[CalDAVSyncResult],
  summary="Sync matching events to CalDAV",
  description=(
    "Synchronize local events with active CalDAV accounts. Optionally filter the local events by tags before "
    "syncing. This is useful after connecting a new calendar or when you want to push a batch of tagged events."
  ),
)
async def sync_events(
  request: Request,
  tags: str | None = Query(
    default=None,
    description="Comma-separated tag list used to filter local events.",
    openapi_examples=CALDAV_SYNC_TAG_QUERY_EXAMPLES,
  ),
) -> list[CalDAVSyncResult]:
  return await service(request).sync_events(parse_tags_query(tags))

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
from fastapi import Body
from fastapi import Query
from fastapi import Path
from fastapi import Request
from fastapi.openapi.models import Example

from ..core.models import Alert
from ..core.models import AlertCreate
from ..services.alert_service import AlertService
from ..utils.validators import parse_tags_query

API_TAG_METADATA = {
  "name": "Alerts Endpoints",
  "description": (
    "Alert ingestion and acknowledgement workflows. Alerts represent immediate personal-assistant signals such "
    "as smart-home warnings, kitchen timers, safety issues, or other attention-worthy events. Alerts can be "
    "tagged, filtered, acknowledged, and deleted after the user has handled them."
  ),
}

router = APIRouter(prefix="/alerts", tags=[API_TAG_METADATA["name"]])

ALERT_CREATE_OPENAPI_EXAMPLES: dict[str, Example] = {
  "front_door_open": {
    "summary": "Smart home alert",
    "description": "A personal assistant surfaces a smart-home alert that needs attention.",
    "value": {
      "title": "Front door left open",
      "message": "The front door has been open for 8 minutes.",
      "severity": "warning",
      "source": "smart-home",
      "tags": ["device_id:front-door-sensor", "user_id:alex"],
    },
  },
  "oven_timer_done": {
    "summary": "Kitchen timer",
    "description": "A personal assistant alert for a finished cooking timer.",
    "value": {
      "title": "Oven timer is done",
      "message": "Your lasagna timer finished. Check the oven now.",
      "severity": "info",
      "source": "kitchen-timer",
      "tags": ["device_id:kitchen-hub", "user_id:alex"],
    },
  },
  "water_leak": {
    "summary": "Critical household alert",
    "description": "A critical alert from a connected home sensor.",
    "value": {
      "title": "Possible water leak",
      "message": "The laundry room sensor detected water near the washing machine.",
      "severity": "critical",
      "source": "smart-home",
      "tags": ["device_id:laundry-sensor", "user_id:alex"],
    },
  },
}

ALERT_RESPONSE_EXAMPLE = Alert.model_validate(
  {
    "id": "alert_123",
    "title": "Front door left open",
    "message": "The front door has been open for 8 minutes.",
    "severity": "warning",
    "timestamp": "2026-07-03T10:20:00",
    "source": "smart-home",
    "tags": ["device_id:front-door-sensor", "user_id:alex"],
    "acknowledged": False,
    "acknowledged_at": None,
  }
)

ALERT_LIST_QUERY_EXAMPLES: dict[str, Example] = {
  "urgent_home": {
    "summary": "Urgent home alerts",
    "description": "Filter to active alerts from the home environment.",
    "value": "device_id:front-door-sensor,user_id:alex",
  },
  "security": {
    "summary": "Security alerts",
    "description": "Filter to security-related alerts only.",
    "value": "device_id:front-door-sensor,user_id:alex",
  },
}

ALERT_ID_PATH_EXAMPLES: dict[str, Example] = {
  "sample_alert_id": {
    "summary": "Alert identifier",
    "description": "A real-looking alert ID returned by the API.",
    "value": "alert_123",
  }
}


def service(request: Request) -> AlertService:
  return request.app.state.alert_service


@router.post(
  "/",
  operation_id="create_alert",
  response_model=Alert,
  status_code=201,
  summary="Create alert",
  description=(
    "Create a new alert that should be surfaced to the user. Use this for smart-home warnings, timer "
    "notifications, safety issues, or other assistant-generated messages. Tags make alerts easier to filter "
    "and route to the right clients."
  ),
  responses={201: {"content": {"application/json": {"example": ALERT_RESPONSE_EXAMPLE}}}},
)
async def create_alert(
  request: Request,
  payload: AlertCreate = Body(
    ...,
    description="Alert details including severity, source, and tags.",
    openapi_examples=ALERT_CREATE_OPENAPI_EXAMPLES,
  ),
) -> Alert:
  return await service(request).create(payload)


@router.get(
  "/",
  operation_id="list_alerts",
  response_model=list[Alert],
  summary="List alerts",
  description=(
    "List stored alerts with optional filters for severity, acknowledgement status, and tags. This endpoint "
    "supports notification centers, alert history screens, and assistant queries like `show urgent home alerts` "
    "without requiring a separate tag-only route."
  ),
)
async def list_alerts(
  request: Request,
  severity: Literal["info", "warning", "critical"] | None = Query(
    default=None,
    description="Severity filter.",
    openapi_examples={
      "warning": {"summary": "Warning alerts", "value": "warning"},
      "critical": {"summary": "Critical alerts", "value": "critical"},
    },
  ),
  acknowledged: bool | None = Query(
    default=None,
    description="Acknowledgement filter.",
    openapi_examples={
      "active": {"summary": "Only active alerts", "value": False},
      "acknowledged": {"summary": "Only acknowledged alerts", "value": True},
    },
  ),
  tags: str | None = Query(
    default=None,
    description="Comma-separated tags, for example device_id:front-door-sensor,user_id:alex.",
    openapi_examples=ALERT_LIST_QUERY_EXAMPLES,
  ),
  limit: int = Query(
    default=100,
    ge=1,
    le=500,
    description="Maximum records to return.",
    openapi_examples={
      "default": {"summary": "Default page size", "value": 100},
      "small": {"summary": "Small page size", "value": 20},
    },
  ),
  offset: int = Query(
    default=0,
    ge=0,
    description="Number of records to skip.",
    openapi_examples={
      "first_page": {"summary": "First page", "value": 0},
      "later_page": {"summary": "Later page", "value": 40},
    },
  ),
) -> list[Alert]:
  return await service(request).list(severity, acknowledged, parse_tags_query(tags), limit, offset)


@router.put(
  "/{alert_id}/acknowledge",
  operation_id="acknowledge_alert",
  response_model=Alert,
  summary="Acknowledge alert",
  description=(
    "Mark an alert as acknowledged and record the acknowledgement timestamp. Acknowledged alerts remain in "
    "history but are no longer treated as active items needing the user's attention."
  ),
)
async def acknowledge_alert(
  alert_id: Annotated[str, Path(..., description="Alert identifier.", openapi_examples=ALERT_ID_PATH_EXAMPLES)],
  request: Request,
) -> Alert:
  return await service(request).acknowledge(alert_id)


@router.delete(
  "/{alert_id}",
  operation_id="delete_alert",
  summary="Delete alert",
  description=(
    "Delete an alert permanently by ID. Use this when the user clears old alert history or removes a signal "
    "that is no longer relevant."
  ),
)
async def delete_alert(
  alert_id: Annotated[str, Path(..., description="Alert identifier.", openapi_examples=ALERT_ID_PATH_EXAMPLES)],
  request: Request,
) -> dict[str, str]:
  return await service(request).delete(alert_id)

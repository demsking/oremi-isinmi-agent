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
from fastapi import APIRouter
from fastapi import Body
from fastapi import Request
from fastapi.openapi.models import Example

from ..core.models import AgentAction
from ..core.models import AgentChatRequest
from ..services.agent_service import AgentService

API_TAG_METADATA = {
  "name": "Agent Endpoints",
  "description": (
    "Natural-language personal-assistant interactions. The agent accepts Alexa-style requests, "
    "uses LLM model through, and returns structured actions that can create or query reminders "
    "and events from conversational text."
  ),
}

router = APIRouter(prefix="/agent", tags=[API_TAG_METADATA["name"]])

AGENT_CHAT_OPENAPI_EXAMPLES: dict[str, Example] = {
  "create_reminder": {
    "summary": "Voice-style reminder",
    "description": "A user talks to Oremi the way they would talk to a home assistant.",
    "value": {
      "message": "Remind me tomorrow at 7 AM to pack Amara's lunch and tag it school",
      "context": {"user_id": "family_admin", "timezone": "Europe/Paris"},
    },
  },
  "create_event": {
    "summary": "Schedule an appointment",
    "description": "Natural language scheduling for a real personal calendar appointment.",
    "value": {
      "message": "Schedule dentist appointment next Wednesday at 2 PM for one hour, tag it health",
      "context": {"user_id": "user123", "timezone": "Europe/Paris"},
    },
  },
  "query_family": {
    "summary": "Ask about family plans",
    "description": "Search the assistant's saved calendar and reminders by tag.",
    "value": {
      "message": "What family events do I have this weekend?",
      "context": {"timezone": "Europe/Paris"},
    },
  },
  "query_bills": {
    "summary": "Ask about bills",
    "description": "Find finance reminders using natural language.",
    "value": {
      "message": "Show me my bill reminders for this month",
      "context": {"timezone": "Europe/Paris"},
    },
  },
}


def service(request: Request) -> AgentService:
  return request.app.state.agent_service


@router.post(
  "/chat",
  response_model=AgentAction,
  summary="Chat with Oremi Isinmi",
  description=(
    "Send a natural-language message to Oremi Isinmi and receive a structured action. Use this endpoint for "
    "voice-assistant style requests such as `remind me to pack lunch tomorrow`, `schedule a dentist appointment`, "
    "or `show my family events this weekend`. The response includes the detected action, entity type, extracted "
    "data, tags, confidence score, and a user-friendly message."
  ),
)
async def chat(
  request: Request,
  payload: AgentChatRequest = Body(
    ...,
    description="Natural language message and optional user context for the agent.",
    openapi_examples=AGENT_CHAT_OPENAPI_EXAMPLES,
  ),
) -> AgentAction:
  return await service(request).chat(payload)

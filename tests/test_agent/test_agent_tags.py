"""Agent tag extraction tests."""

from isinmi.core.models import TagsRequest
from isinmi.services.agent_service import AgentService


def test_extract_tags_from_natural_language() -> None:
  service = AgentService.__new__(AgentService)
  tags = AgentService.extract_tags(
    service,
    TagsRequest(text="Remind me to buy groceries tomorrow, tag it as personal and errands"),
  )
  assert tags == ["personal", "errands", "groceries"]

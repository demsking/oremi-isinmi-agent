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
from datetime import datetime as DateTime
from datetime import time as Time
from datetime import timedelta

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP


def register_mcp_prompts(mcp: FastMCP, app: FastAPI) -> None:
  """Register MCP prompts for user task coordination and guidance."""

  @mcp.prompt(title="Schedule Day Plan", description="Generate a daily plan and schedule tasks for a specific date.")
  def schedule_day_plan(date: str, timezone: str | None = None) -> str:
    tz_part = f" timezone {timezone}" if timezone else ""
    return (
      f"Please help me schedule my day for {date}{tz_part}. "
      "Look at any existing events and reminders for this day and help organize my agenda."
    )

  @mcp.prompt(
    title="Create Event Draft", description="Create a draft event with title, start time, duration, and optional location."
  )
  def create_event_draft(
    title: str,
    start_time: str,
    duration_minutes: str = "60",
    location: str | None = None,
  ) -> str:
    loc_part = f" at {location}" if location else ""
    return (
      f"Drafting a calendar event:\n"
      f"Title: {title}\n"
      f"Start: {start_time}\n"
      f"Duration: {duration_minutes} minutes\n"
      f"Location: {loc_part}\n"
      "Please verify the details and use create_event tool to schedule it if correct."
    )

  @mcp.prompt(title="Manage Unread Alerts", description="Guidelines to manage and process unread notifications.")
  def manage_unread_alerts() -> str:
    return (
      "To manage unread alerts, follow these steps:\n"
      "1. Check the count of unread alerts using the get_unread_count tool.\n"
      "2. Retrieve the notifications list using the list_notifications tool with read_status=False.\n"
      "3. Process them accordingly and mark them read using mark_notification_read."
    )

  @mcp.prompt(title="Set Reminder", description="Guide the setup of a new reminder.")
  async def set_reminder(
    title: str,
    datetime: str,
    description: str | None = None,
    recurring: str = "none",
    tags: str | None = None,
  ) -> str:
    desc_str = f"\nDescription: {description}" if description else ""
    rec_str = f"\nRecurring: {recurring}" if recurring and recurring != "none" else ""
    tags_str = f"\nTags: {tags}" if tags else ""
    return (
      f"I want to set a reminder with the following details:\n"
      f"Title: {title}\n"
      f"Datetime: {datetime}"
      f"{desc_str}"
      f"{rec_str}"
      f"{tags_str}\n\n"
      "Please call the `create_reminder` tool to register this reminder."
    )

  @mcp.prompt(title="List Reminders", description="List current reminders filtered by status, tags, or upcoming status.")
  async def list_reminders(
    status: str | None = None,
    tags: str | None = None,
    upcoming: bool = False,
  ) -> str:
    from isinmi.core.models import clean_tags

    tags_list = clean_tags(tags.split(",")) if tags else []

    try:
      reminders = await app.state.reminder_service.list(
        status=status,
        tags=tags_list,
        upcoming=upcoming,
        limit=50,
      )
    except Exception:
      reminders = []

    if reminders:
      reminder_lines = []
      for r in reminders:
        desc = f" ({r.description})" if r.description else ""
        reminder_lines.append(f"- [{r.id}] {r.title} at {r.datetime.isoformat()} - Status: {r.status}{desc}")
      reminders_text = "\n".join(reminder_lines)
    else:
      reminders_text = "No matching reminders found in the database."

    return (
      f"Here are the current matching reminders from the database:\n\n"
      f"{reminders_text}\n\n"
      "You can manage these reminders using `update_reminder`, `complete_reminder`, or `delete_reminder`."
    )

  @mcp.prompt(title="Find Reminder", description="Search for reminders matching a query in the title or description.")
  async def find_reminder(query: str) -> str:
    try:
      all_reminders = await app.state.reminder_service.list(limit=200)
      matches = [
        r
        for r in all_reminders
        if query.lower() in r.title.lower() or (r.description and query.lower() in r.description.lower())
      ]
    except Exception:
      matches = []

    if matches:
      lines = []
      for r in matches:
        desc = f" ({r.description})" if r.description else ""
        lines.append(f"- [{r.id}] {r.title} at {r.datetime.isoformat()} ({r.status}){desc}")
      matches_text = "\n".join(lines)
    else:
      matches_text = f"No reminders found matching query '{query}'."

    return (
      f"Search results for reminders matching '{query}':\n\n"
      f"{matches_text}\n\n"
      "If you found the reminder you were looking for, you can act on it using its ID."
    )

  @mcp.prompt(title="Update Reminder", description="Guide the update of an existing reminder.")
  async def update_reminder(
    reminder_id: str,
    title: str | None = None,
    description: str | None = None,
    datetime: str | None = None,
    recurring: str | None = None,
    tags: str | None = None,
    status: str | None = None,
  ) -> str:
    try:
      r = await app.state.reminder_service.get(reminder_id)
      current_details = (
        f"Current Details:\n"
        f"- ID: {r.id}\n"
        f"- Title: {r.title}\n"
        f"- Datetime: {r.datetime.isoformat()}\n"
        f"- Description: {r.description or 'None'}\n"
        f"- Status: {r.status}\n"
        f"- Recurring: {r.recurring}\n"
        f"- Tags: {', '.join(r.tags) if r.tags else 'None'}"
      )
    except Exception:
      current_details = f"Reminder with ID '{reminder_id}' could not be loaded or does not exist."

    proposed = []
    if title:
      proposed.append(f"Title -> {title}")
    if description:
      proposed.append(f"Description -> {description}")
    if datetime:
      proposed.append(f"Datetime -> {datetime}")
    if recurring:
      proposed.append(f"Recurring -> {recurring}")
    if tags:
      proposed.append(f"Tags -> {tags}")
    if status:
      proposed.append(f"Status -> {status}")

    proposed_str = "\n".join(f"- {p}" for p in proposed) if proposed else "No updates specified yet."

    return (
      f"Updating Reminder:\n\n"
      f"{current_details}\n\n"
      f"Proposed Updates:\n"
      f"{proposed_str}\n\n"
      f"Please use the `update_reminder` tool to apply these changes."
    )

  @mcp.prompt(title="Complete Reminder", description="Mark a specific reminder as completed.")
  async def complete_reminder(reminder_id: str) -> str:
    try:
      r = await app.state.reminder_service.get(reminder_id)
      details = f"Reminder: '{r.title}' scheduled for {r.datetime.isoformat()} (ID: {r.id})."
    except Exception:
      details = f"Reminder ID: {reminder_id}"

    return (
      f"Please mark the following reminder as completed:\n{details}\n\nUse the `complete_reminder` tool to perform this action."
    )

  @mcp.prompt(title="Postpone Reminder", description="Postpone a reminder to a new date and time.")
  async def postpone_reminder(reminder_id: str, new_datetime: str) -> str:
    try:
      r = await app.state.reminder_service.get(reminder_id)
      details = f"Reminder '{r.title}' (currently at {r.datetime.isoformat()})"
    except Exception:
      details = f"Reminder ID {reminder_id}"

    return (
      f"I want to postpone the following reminder:\n"
      f"{details}\n"
      f"New Datetime: {new_datetime}\n\n"
      f"Please use the `update_reminder` tool to update its `datetime` field to '{new_datetime}'."
    )

  @mcp.prompt(title="Delete Reminder", description="Delete a reminder.")
  async def delete_reminder(reminder_id: str) -> str:
    try:
      r = await app.state.reminder_service.get(reminder_id)
      details = f"Reminder: '{r.title}' scheduled for {r.datetime.isoformat()} (ID: {r.id})."
    except Exception:
      details = f"Reminder ID: {reminder_id}"

    return f"Please delete the following reminder:\n{details}\n\nUse the `delete_reminder` tool to perform this action."

  @mcp.prompt(title="Schedule Event", description="Schedule a new calendar event.")
  async def schedule_event(
    title: str,
    start_datetime: str,
    end_datetime: str,
    description: str | None = None,
    location: str | None = None,
    attendees: str | None = None,
    tags: str | None = None,
  ) -> str:
    desc_part = f"\nDescription: {description}" if description else ""
    loc_part = f"\nLocation: {location}" if location else ""
    att_part = f"\nAttendees: {attendees}" if attendees else ""
    tags_part = f"\nTags: {tags}" if tags else ""
    return (
      f"I want to schedule a calendar event with these details:\n"
      f"Title: {title}\n"
      f"Start: {start_datetime}\n"
      f"End: {end_datetime}"
      f"{desc_part}"
      f"{loc_part}"
      f"{att_part}"
      f"{tags_part}\n\n"
      f"Please use the `create_event` tool to schedule this event."
    )

  @mcp.prompt(title="List Events", description="List calendar events with optional filters.")
  async def list_events(
    status: str | None = None,
    start: str | None = None,
    end: str | None = None,
    tags: str | None = None,
  ) -> str:
    from isinmi.core.models import clean_tags

    tags_list = clean_tags(tags.split(",")) if tags else []

    start_dt = None
    if start:
      try:
        start_dt = DateTime.fromisoformat(start)
      except ValueError:
        pass

    end_dt = None
    if end:
      try:
        end_dt = DateTime.fromisoformat(end)
      except ValueError:
        pass

    try:
      events = await app.state.event_service.list(
        status=status,
        start=start_dt,
        end=end_dt,
        tags=tags_list,
        limit=50,
      )
    except Exception:
      events = []

    if events:
      lines = []
      for e in events:
        loc = f" at {e.location}" if e.location else ""
        lines.append(
          f"- [{e.id}] {e.title} ({e.start_datetime.isoformat()} to {e.end_datetime.isoformat()}){loc} - Status: {e.status}"
        )
      events_text = "\n".join(lines)
    else:
      events_text = "No matching events found in the calendar."

    return (
      f"Here are the calendar events matching your search:\n\n"
      f"{events_text}\n\n"
      "You can manage these events using `update_event` or `delete_event`."
    )

  @mcp.prompt(title="Find Event", description="Find calendar events matching a title/description search query.")
  async def find_event(query: str) -> str:
    try:
      all_events = await app.state.event_service.list(limit=200)
      matches = [
        e for e in all_events if query.lower() in e.title.lower() or (e.description and query.lower() in e.description.lower())
      ]
    except Exception:
      matches = []

    if matches:
      lines = []
      for e in matches:
        loc = f" at {e.location}" if e.location else ""
        lines.append(
          f"- [{e.id}] {e.title} ({e.start_datetime.isoformat()} to {e.end_datetime.isoformat()}){loc} - Status: {e.status}"
        )
      matches_text = "\n".join(lines)
    else:
      matches_text = f"No events found matching query '{query}'."

    return (
      f"Search results for calendar events matching '{query}':\n\n"
      f"{matches_text}\n\n"
      "If you found the event you were looking for, you can inspect it or update/delete it by ID."
    )

  @mcp.prompt(title="Update Event", description="Update details of an existing calendar event.")
  async def update_event(
    event_id: str,
    title: str | None = None,
    description: str | None = None,
    start_datetime: str | None = None,
    end_datetime: str | None = None,
    location: str | None = None,
    attendees: str | None = None,
    tags: str | None = None,
    status: str | None = None,
  ) -> str:
    try:
      e = await app.state.event_service.get(event_id)
      current_details = (
        f"Current Details:\n"
        f"- ID: {e.id}\n"
        f"- Title: {e.title}\n"
        f"- Start: {e.start_datetime.isoformat()}\n"
        f"- End: {e.end_datetime.isoformat()}\n"
        f"- Location: {e.location or 'None'}\n"
        f"- Description: {e.description or 'None'}\n"
        f"- Attendees: {', '.join(e.attendees) if e.attendees else 'None'}\n"
        f"- Status: {e.status}\n"
        f"- Tags: {', '.join(e.tags) if e.tags else 'None'}"
      )
    except Exception:
      current_details = f"Event with ID '{event_id}' could not be loaded or does not exist."

    proposed = []

    if title:
      proposed.append(f"Title -> {title}")

    if description:
      proposed.append(f"Description -> {description}")

    if start_datetime:
      proposed.append(f"Start -> {start_datetime}")

    if end_datetime:
      proposed.append(f"End -> {end_datetime}")

    if location:
      proposed.append(f"Location -> {location}")

    if attendees:
      proposed.append(f"Attendees -> {attendees}")

    if tags:
      proposed.append(f"Tags -> {tags}")

    if status:
      proposed.append(f"Status -> {status}")

    proposed_str = "\n".join(f"- {p}" for p in proposed) if proposed else "No updates specified yet."

    return (
      f"Updating Calendar Event:\n\n"
      f"{current_details}\n\n"
      f"Proposed Updates:\n"
      f"{proposed_str}\n\n"
      f"Please use the `update_event` tool to apply these changes."
    )

  @mcp.prompt(title="Cancel Event", description="Cancel a calendar event.")
  async def cancel_event(event_id: str) -> str:
    try:
      e = await app.state.event_service.get(event_id)
      details = f"Event: '{e.title}' scheduled for {e.start_datetime.isoformat()} to {e.end_datetime.isoformat()} (ID: {e.id})."
    except Exception:
      details = f"Event ID: {event_id}"

    return (
      f"Please cancel the following calendar event:\n"
      f"{details}\n\n"
      f"Use the `update_event` tool to set its `status` to 'cancelled', or use `delete_event` to remove it."
    )

  @mcp.prompt(title="Find Free Time", description="Find free slots in the user's schedule on a specific date.")
  async def find_free_time(date: str, timezone: str | None = None) -> str:
    try:
      target_date = DateTime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
      return f"Invalid date format '{date}'. Please use YYYY-MM-DD."

    day_start = DateTime.combine(target_date, Time.min)
    day_end = DateTime.combine(target_date, Time.max)

    try:
      events = await app.state.event_service.list(start=day_start, end=day_end, limit=100)
    except Exception:
      events = []

    active_events = [e for e in events if e.status != "cancelled"]
    active_events.sort(key=lambda x: x.start_datetime)

    work_start = DateTime.combine(target_date, Time(9, 0))
    work_end = DateTime.combine(target_date, Time(18, 0))

    free_slots = []
    current_time = work_start

    for e in active_events:
      e_start = max(e.start_datetime, work_start)
      e_end = min(e.end_datetime, work_end)

      if e_start > current_time:
        diff_mins = int((e_start - current_time).total_seconds() / 60)
        if diff_mins >= 15:
          free_slots.append((current_time, e_start))
      current_time = max(current_time, e_end)

    if current_time < work_end:
      diff_mins = int((work_end - current_time).total_seconds() / 60)
      if diff_mins >= 15:
        free_slots.append((current_time, work_end))

    if free_slots:
      slots_text = "\n".join(f"- {s[0].strftime('%H:%M')} to {s[1].strftime('%H:%M')}" for s in free_slots)
    else:
      slots_text = "No free time slots available during working hours (09:00 - 18:00)."

    events_list_str = ""
    if active_events:
      events_list_str = "\nBusy times:\n" + "\n".join(
        f"- {e.title}: {e.start_datetime.strftime('%H:%M')} - {e.end_datetime.strftime('%H:%M')}" for e in active_events
      )

    return (
      f"Free time slots on {date} (Working hours 09:00 - 18:00):\n\n"
      f"{slots_text}\n"
      f"{events_list_str}\n\n"
      "You can schedule new events during these free slots using `create_event`."
    )

  @mcp.prompt(
    title="Daily Agenda", description="Retrieve and display the daily agenda of events and reminders for a specific date."
  )
  async def daily_agenda(date: str, timezone: str | None = None) -> str:
    try:
      target_date = DateTime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
      return f"Invalid date format '{date}'. Please use YYYY-MM-DD."

    day_start = DateTime.combine(target_date, Time.min)
    day_end = DateTime.combine(target_date, Time.max)

    try:
      events = await app.state.event_service.list(start=day_start, end=day_end, limit=100)
    except Exception:
      events = []

    try:
      reminders = await app.state.reminder_service.list(start=day_start, end=day_end, limit=100)
    except Exception:
      reminders = []

    active_events = [e for e in events if e.status != "cancelled"]
    active_events.sort(key=lambda x: x.start_datetime)

    reminders.sort(key=lambda x: x.datetime)

    events_str = ""
    if active_events:
      events_str = "\n".join(
        f"- [{e.start_datetime.strftime('%H:%M')}] Event: {e.title}" + (f" at {e.location}" if e.location else "")
        for e in active_events
      )
    else:
      events_str = "No events scheduled."

    reminders_str = ""
    if reminders:
      reminders_str = "\n".join(f"- [{r.datetime.strftime('%H:%M')}] Reminder: {r.title} ({r.status})" for r in reminders)
    else:
      reminders_str = "No reminders set."

    return f"Agenda for {date}:\n\n--- Calendar Events ---\n{events_str}\n\n--- Reminders ---\n{reminders_str}"

  @mcp.prompt(title="Weekly Agenda", description="Retrieve and display the weekly agenda starting from a specific date.")
  async def weekly_agenda(start_date: str, timezone: str | None = None) -> str:
    try:
      start_d = DateTime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
      return f"Invalid date format '{start_date}'. Please use YYYY-MM-DD."

    lines = []
    for i in range(7):
      day = start_d + timedelta(days=i)
      day_str = day.strftime("%Y-%m-%d")
      day_name = day.strftime("%A")

      day_start = DateTime.combine(day, Time.min)
      day_end = DateTime.combine(day, Time.max)

      try:
        events = await app.state.event_service.list(start=day_start, end=day_end, limit=50)
        active_events = [e for e in events if e.status != "cancelled"]
      except Exception:
        active_events = []

      try:
        reminders = await app.state.reminder_service.list(start=day_start, end=day_end, limit=50)
      except Exception:
        reminders = []

      lines.append(f"### {day_name}, {day_str}")

      if not active_events and not reminders:
        lines.append("  No items scheduled.\n")
        continue

      if active_events:
        lines.append("  Events:")
        for e in sorted(active_events, key=lambda x: x.start_datetime):
          lines.append(f"    - [{e.start_datetime.strftime('%H:%M')}] {e.title}")

      if reminders:
        lines.append("  Reminders:")
        for r in sorted(reminders, key=lambda x: x.datetime):
          lines.append(f"    - [{r.datetime.strftime('%H:%M')}] {r.title} ({r.status})")

      lines.append("")

    weekly_text = "\n".join(lines)

    return f"Weekly Agenda starting {start_date}:\n\n{weekly_text}"

  @mcp.prompt(title="Schedule Recurring Reminder", description="Schedule a recurring reminder (daily, weekly, monthly).")
  async def schedule_recurring_reminder(
    title: str,
    datetime: str,
    recurring: str,
    description: str | None = None,
    tags: str | None = None,
  ) -> str:
    if recurring not in ["daily", "weekly", "monthly"]:
      return f"Error: recurring must be 'daily', 'weekly', or 'monthly'. Got '{recurring}'."

    desc_part = f"\nDescription: {description}" if description else ""
    tags_part = f"\nTags: {tags}" if tags else ""
    return (
      f"I want to schedule a recurring reminder with these details:\n"
      f"Title: {title}\n"
      f"Datetime: {datetime}\n"
      f"Frequency: {recurring}"
      f"{desc_part}"
      f"{tags_part}\n\n"
      f"Please use the `create_reminder` tool to register this recurring reminder."
    )

  @mcp.prompt(title="Reminder Suggestions", description="Provide helpful suggestions/templates for reminders based on context.")
  async def reminder_suggestions(context: str | None = None) -> str:
    suggestions = {
      "work": [
        "Submit weekly status report",
        "Prepare agenda for team sync",
        "Review code pull requests",
        "Check email and slack backlog",
      ],
      "health": [
        "Take daily vitamins",
        "Drink a glass of water",
        "Stretch and walk for 5 minutes",
        "Schedule annual medical checkup",
      ],
      "home": [
        "Water the house plants",
        "Take out the trash/recycling",
        "Clean the kitchen counters",
        "Check the mail box",
      ],
      "shopping": [
        "Buy groceries (milk, eggs, bread)",
        "Order replacement light bulbs",
        "Pick up prescription from pharmacy",
        "Buy gift for upcoming birthday",
      ],
    }

    ctx = context.lower() if context else None
    if ctx and ctx in suggestions:
      selected = suggestions[ctx]
      title = f"Suggestions for {context}:"
    else:
      selected = [item for sub in suggestions.values() for item in sub]
      title = "General Reminder Suggestions:"

    suggested_lines = "\n".join(f"- {s}" for s in selected)

    return f"{title}\n\n{suggested_lines}\n\nFeel free to select one of these suggestions and use `create_reminder` to set it."

  @mcp.prompt(
    title="Morning Briefing",
    description="Get a comprehensive morning briefing including pending reminders and calendar events for today.",
  )
  async def morning_briefing(date: str, timezone: str | None = None) -> str:
    try:
      target_date = DateTime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
      return f"Invalid date format '{date}'. Please use YYYY-MM-DD."

    day_start = DateTime.combine(target_date, Time.min)
    day_end = DateTime.combine(target_date, Time.max)

    try:
      events = await app.state.event_service.list(start=day_start, end=day_end, limit=50)
      active_events = [e for e in events if e.status != "cancelled"]
      active_events.sort(key=lambda x: x.start_datetime)
    except Exception:
      active_events = []

    try:
      reminders = await app.state.reminder_service.list(start=day_start, end=day_end, limit=50)
      reminders.sort(key=lambda x: x.datetime)
    except Exception:
      reminders = []

    try:
      all_pending = await app.state.reminder_service.list(status="pending", limit=100)
      overdue = [r for r in all_pending if r.datetime < day_start]
      overdue.sort(key=lambda x: x.datetime)
    except Exception:
      overdue = []

    brief_lines = [f"Good morning! Here is your briefing for {date}.\n", "--- Today's Agenda ---"]

    if active_events:
      for e in active_events:
        loc = f" at {e.location}" if e.location else ""
        brief_lines.append(f"- [{e.start_datetime.strftime('%H:%M')} - {e.end_datetime.strftime('%H:%M')}] {e.title}{loc}")
    else:
      brief_lines.append("No calendar events scheduled for today.")

    brief_lines.append("\n--- Today's Reminders ---")
    if reminders:
      for r in reminders:
        brief_lines.append(f"- [{r.datetime.strftime('%H:%M')}] {r.title} ({r.status})")
    else:
      brief_lines.append("No reminders scheduled for today.")

    brief_lines.append("\n--- Overdue / Pending Reminders ---")
    if overdue:
      for r in overdue:
        brief_lines.append(f"- [{r.datetime.strftime('%Y-%m-%d %H:%M')}] {r.title}")
    else:
      brief_lines.append("No overdue reminders.")

    return "\n".join(brief_lines)

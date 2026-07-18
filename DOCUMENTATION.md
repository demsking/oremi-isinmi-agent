**Oremi Isinmi** is the reminders, scheduling, tagging, and notification
subsystem of the Oremi personal assistant ecosystem. It provides a REST API
and MCP interface that help AI assistants and autonomous agents manage
reminders, schedules, tags, and notifications through a secure and intelligent
platform.

Project repository: https://gitlab.com/demsking/oremi-isinmi

![Oremi Isinmi Logo](./static/logo.jpg)

## Why Oremi Isinmi?

In Yorùbá culture, _Oremi_ means "my friend" and _Isinmi_ means "rest" or
"appointment." Together, they represent a friendly companion that helps you find
peace of mind by keeping your commitments organized and your time well-managed.
This agent embodies that philosophy by offering:

- **Natural Language Interaction**: Simply tell the agent what you need, and it understands
- **Smart Organization**: Use tags to group and filter records by device, UUID, source, user, or workflow
- **Privacy First**: Everything stays on your device with encrypted local storage
- **Real-time Notifications**: Stay informed with Server-Sent Events for reminders and events
- **Natural Language Understanding**: Converts conversational requests into structured actions

## Core Capabilities

- **Intelligent Reminder Management**: Create, update, and track reminders with natural language
- **Smart Event Scheduling**: Plan events with automatic reminder generation
- **Tag-Based Organization**: Filter and find items instantly using client grouping tags stored on reminders, events, and notifications
- **Real-time Notifications**: SSE streaming for immediate updates
- **AI Conversation**: Chat with the agent to manage your schedule
- **Encrypted Storage**: SQLAlchemy ORM with SQLCipher-backed SQLite and support for other SQL databases
- **Lightweight Deployment**: Alpine-based [Docker image](https://hub.docker.com/r/demsking/oremi-isinmi) for minimal resource usage

## Tags

Tags are free-form client grouping keys used to organize and filter records
across the application. They are stored as normalized JSON arrays and can be
attached to reminders, events, notifications, and chat requests.

Use tags when you want to group records by values such as:

- `device_id:iphone-14`
- `device_id:web-app`
- `user_id:alex`

Tag-filtered endpoints match every requested tag, so
`?tags=device_id:iphone-14,user_id:alex` returns only records that carry both
tags. The `/agent/chat` endpoint also accepts optional tags so a client can
group the conversation itself and any reminder created from it.

## Use Cases

- **Personal Time Management**: "Remind me to call the dentist tomorrow at 2pm"
- **Event Planning**: "Schedule a team meeting for Friday at 10am, tag it as 'work'"
- **Information Retrieval**: "Show me all my personal reminders for next week"
- **Tag Organization**: "List all events tagged as 'urgent' and 'work'"

## Security & Privacy

- Default SQLite storage is encrypted locally via SQLCipher
- Encryption key required at startup (provided via environment variable)
- Remote data is transmitted only to CalDAV servers that you explicitly configure
- Local-first architecture ensures data sovereignty

## Deployment

### Docker Image

The [`demsking/oremi-isinmi`](https://hub.docker.com/r/demsking/oremi-isinmi)
Docker image is officially available on Docker Hub, supporting both
`linux/amd64` and `linux/arm64` platforms. The image is configured to expose
port `5073`, which serves the API and documentation endpoints.

The local documentation can be accessed at `http://localhost:5073/docs` for easy
reference on available endpoints and usage instructions.

### Volumes

The Docker image defines one persistent volume for application data:

- **Container path:** `/oremi/data`
- **Purpose:** SQLite database files and any other data you place under that directory

The image does not define a dedicated logs volume. If you want log files to
persist across container recreation, set `OREMI_ISINMI_LOG_FILE` to a path under
`/oremi/data` and mount that directory on the host.

### Deploy with Docker

Use the official Docker image [`demsking/oremi-isinmi`](https://hub.docker.com/r/demsking/oremi-isinmi)
to run Oremi Isinmi:

```sh
docker run -d \
  --env-file <path_to_env_file> \
  -v ~/.config/oremi-isinmi:/oremi/data \
  -p 5073:5073 \
  demsking/oremi-isinmi
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#description/environment-variables) file containing the
necessary configurations.

### Deploy with Docker Compose

Create a `compose.yml` file:

```yaml
services:
  isinmi:
    image: demsking/oremi-isinmi
    restart: unless-stopped
    ports:
      - 5073:5073
    volumes:
      - ~/.config/oremi-isinmi:/oremi/data
    environment:
      OREMI_ISINMI_DATABASE_ENCRYPTION_KEY: ${OREMI_ISINMI_DATABASE_ENCRYPTION_KEY?Missing required environment variable}
    env_file:
      - .env
```

Run the container using `docker compose`:

```sh
docker compose up -d
```

### Environment Variables

When configuring **Oremi Isinmi**, several environment variables are used to
control its behavior and connect with external services. Below is a breakdown
of these variables, grouped by their purpose.

All runtime settings use the `OREMI_ISINMI_` prefix and can be provided through
the environment or a `.env` file in the working directory.

#### Application and Server Settings

- `OREMI_ISINMI_SERVER_HOST`: Optional. Defaults to `0.0.0.0`. Host interface used by
  the Oremi Isinmi server.
- `OREMI_ISINMI_SERVER_PORT`: Optional. Defaults to `5073`. Port used by the
  Oremi Isinmi server.
- `OREMI_ISINMI_API_PREFIX`: Optional. Defaults to `/`. Prefix for all API
  routes. Must start with `/`.

#### Database Settings

- `OREMI_ISINMI_DATABASE_URL`: Optional. Defaults to
  `sqlite:///./oremi_isinmi.db`. Use `sqlite:///` for SQLCipher-backed local
  storage, or point the ORM at a supported PostgreSQL, MariaDB, or MySQL URL.
- `OREMI_ISINMI_DATABASE_ENCRYPTION_KEY`: **Required**. No default. SQLCipher
  encryption key for SQLite storage. Must be at least 32 characters long.

To generate a new encryption key, use a cryptographically secure random string.
For example:

```sh
openssl rand -base64 32
```

Copy the output into `OREMI_ISINMI_DATABASE_ENCRYPTION_KEY`. If you want a
plain ASCII key instead of base64, make sure it is at least 32 characters long
and store it in your `.env` file without extra spaces or quotes.

#### Realtime Notification Settings

- `OREMI_ISINMI_SSE_RETRY_TIMEOUT_SECONDS`: Optional. Defaults to `30`.
  Server-Sent Events client retry interval in seconds. Valid range: `1` to
  `120`.

#### CalDAV Settings

- `OREMI_ISINMI_CALDAV_REQUEST_TIMEOUT_SECONDS`: Optional. Defaults to `30`.
  Maximum time in seconds to wait for a CalDAV server response. Valid range:
  `1` to `300`.

#### Logging Settings

- `OREMI_ISINMI_LOG_LEVEL`: Optional. Defaults to `INFO`. Logging level:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `OREMI_ISINMI_LOG_FILE`: Optional. Rotating application log file path.

#### Example

```env
OREMI_ISINMI_API_PREFIX=/
OREMI_ISINMI_SERVER_HOST=0.0.0.0
OREMI_ISINMI_SERVER_PORT=5073
OREMI_ISINMI_DATABASE_URL=sqlite:///oremi/data/oremi_isinmi.db
OREMI_ISINMI_DATABASE_ENCRYPTION_KEY=replace-this-with-at-least-32-characters
OREMI_ISINMI_LOG_LEVEL=INFO
OREMI_ISINMI_SSE_RETRY_TIMEOUT_SECONDS=30
OREMI_ISINMI_CALDAV_REQUEST_TIMEOUT_SECONDS=30
```

### Storage Layer

The persistence layer uses SQLAlchemy ORM instead of hand-written SQL queries.
SQLite remains encrypted through SQLCipher, while the same repositories can be
backed by PostgreSQL or MariaDB when you need a server database.

## CalDAV Integration

CalDAV is integrated as a dedicated sync layer on top of the local event store.
Local events remain the source of truth inside Oremi Isinmi, while CalDAV acts
as an optional remote calendar target.

What the integration does:

- Stores CalDAV accounts in the encrypted local database
- Synchronizes local events to remote calendars using iCalendar `VEVENT` payloads
- Uses the local event `id` as the CalDAV `UID`
- Maps event fields as follows:
  - `title` -> `SUMMARY`
  - `description` -> `DESCRIPTION`
  - `location` -> `LOCATION`
  - `tags` -> `CATEGORIES`
  - `attendees` -> `ATTENDEE`
- Filters which events are synchronized by CalDAV account tags
- Keeps sync links locally so updates and deletions can reuse the same remote resource

What it does not do yet:

- It does not import remote CalDAV changes back into the local database
- It does not try to auto-discover a calendar home set from the server URL
- It does not force the local request to fail if the remote CalDAV sync fails

Tag-based CalDAV routing:

- An account with no tags receives every local event
- An account with tags only receives events whose tags contain all of those values
- Example:
  - account tags: `["device_id:laptop-1"]`
  - event tags: `["device_id:laptop-1", "user_id:alex"]`
  - result: event is synchronized
  - event tags: `["device_id:phone-1"]`
  - result: event is skipped

Operational notes:

- CalDAV credentials are stored inside the encrypted SQLCipher database
- The integration uses the configured `calendar_url` directly for writes
- Remote sync uses `PUT` for create/update and `DELETE` for removals
- The current implementation is best-effort and logs remote sync errors without
  breaking the local event workflow

### MCP Integration

Oremi Isinmi exposes a Model Context Protocol (MCP) server over HTTP, built on Python's official `mcp` SDK using the `FastMCP` framework.

The MCP HTTP transport endpoint is mounted at:

- `POST /mcp` (Server-Sent Events connection negotiation and request/response transport)

#### MCP Tools

The server provides a rich catalog of strongly-typed tools representing scheduling, reminders, notifications, and synchronization operations:

##### Reminder Management

- `create_reminder`: Schedule a new encrypted reminder with natural language-oriented metadata and tags.
- `list_reminders`: Retrieve reminders matching filters (status, tags, datetime range, upcoming).
- `update_reminder`: Update fields of an existing reminder.
- `complete_reminder`: Mark a reminder as completed.
- `delete_reminder`: Permanently remove a reminder.

##### Calendar Event Management

- `create_event`: Book a calendar event and generate corresponding notifications.
- `get_event`: Fetch details of a single event by ID.
- `list_events`: List calendar events matching tags, status, or date range.
- `update_event`: Modify properties of a booked event.
- `delete_event`: Cancel and delete a calendar event.

##### Notifications and Alerts

- `list_notifications`: Retrieve read/unread notification logs.
- `get_unread_count`: Query the count of unread alerts.
- `mark_notification_read`: Mark a specific notification as read.
- `mark_all_notifications_read`: Bulk mark notifications as read.

##### CalDAV Accounts Sync

- `create_caldav_account`: Register or update CalDAV credentials and endpoint configurations.
- `list_caldav_accounts`: Retrieve registered CalDAV accounts.
- `delete_caldav_account`: Remove a CalDAV account profile.

#### MCP Resources

AI agents can directly inspect the state of resources using URI-based resource paths. The resource payloads are returned as raw JSON:

- `reminders:///{reminder_id}`: Retrieves detailed state of a specific reminder.
- `events:///{event_id}`: Retrieves detailed state of a specific calendar event.
- `notifications:///{notification_id}`: Retrieves detailed state of a specific notification.

#### MCP Prompts

The server publishes high-level prompt templates to guide AI agents in multi-step workflows:

- `schedule_day_plan`: Helps the agent organize tasks and appointments for a specific day.
- `create_event_draft`: Guides the user/agent through gathering necessary details to draft and book calendar events.
- `manage_unread_alerts`: Facilitates reading, acknowledging, and completing tasks associated with outstanding notifications.

## Contributing

Oremi Device is built with Python and uses `uv` for dependency management. The
project follows standard Python development practices with type hints, linting,
and automated testing.

For detailed information on setting up your development environment, running
tests, code style guidelines, and the pull request process, please refer to
[CONTRIBUTING.md](https://gitlab.com/demsking/oremi-isinmi/-/blob/main/CONTRIBUTING.md).

## Versioning

Oremi Device project adheres to [Semantic Versioning](https://semver.org/)
(SemVer). Version numbers follow the `MAJOR.MINOR.PATCH` format:

- **MAJOR** version increments for incompatible API changes
- **MINOR** version increments for backward-compatible new functionality
- **PATCH** version increments for backward-compatible bug fixes

## License

Copyright 2026 Sébastien Demanou. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

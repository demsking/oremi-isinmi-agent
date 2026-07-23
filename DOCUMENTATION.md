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
This subsystem embodies that philosophy by offering:

- **REST API & MCP Interface**: Seamless management via HTTP endpoints and Model Context Protocol
- **Smart Organization**: Use tags to group and filter records by device, UUID, source, user, or workflow
- **Privacy First**: Everything stays on your device with encrypted local storage
- **Real-time Notifications**: Stay informed with Server-Sent Events (SSE) for reminders and events
- **Remote Synchronization**: Synchronize calendar events with CalDAV servers

## Core Capabilities

- **Reminder Management**: Create, update, list, complete, and delete encrypted reminders
- **Event Scheduling**: Plan calendar events with automated notifications and CalDAV sync
- **Tag-Based Organization**: Filter and find items using client grouping tags on reminders, events, and notifications
- **Real-time Notifications**: Server-Sent Events (SSE) streaming for immediate updates
- **Model Context Protocol (MCP)**: Expose tools, resources, and prompts for AI integrations
- **Encrypted Storage**: SQLAlchemy ORM with SQLCipher-backed SQLite and support for other SQL databases
- **Lightweight Deployment**: Alpine-based [Docker image](https://hub.docker.com/r/demsking/oremi-isinmi) for minimal resource usage

## Tags

Tags are free-form client grouping keys used to organize and filter records
across the application. They are stored as normalized JSON arrays and can be
attached to reminders, events, and notifications.

Use tags when you want to group records by values such as:

- `device_id:iphone-14`
- `device_id:web-app`
- `user_id:alex`

Tag-filtered endpoints match every requested tag, so
`?tags=device_id:iphone-14,user_id:alex` returns only records that carry both
tags. Optional tags can also be passed when creating reminders, scheduling
events, or managing notifications so clients can group records by client,
device, or workflow.

## Use Cases

- **Reminder Management**: Create, list, update, and complete reminders via REST API or MCP tools
- **Event Scheduling**: Book calendar events, manage attendees, and sync with CalDAV targets
- **Information Retrieval**: Query reminders and notifications using status, date range, or tag filters
- **Tag Filtering**: Group and retrieve records tagged by device, user, or workflow identifier

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
  -v ~/.local/share/oremi-isinmi:/oremi/data \
  -p 5073:5073 \
  demsking/oremi-isinmi
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#environment-variables) file containing the
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
      - oremi-isinmi-data:/oremi/data
    environment:
      OREMI_ISINMI_DATABASE_ENCRYPTION_KEY: ${OREMI_ISINMI_DATABASE_ENCRYPTION_KEY?Missing required environment variable}
    env_file:
      - .env

volumes:
  oremi-isinmi-data:
```

Run the container using `docker compose`:

```sh
docker compose up -d
```

## Environment Variables

When configuring **Oremi Isinmi**, several environment variables are used to
control its behavior and connect with external services. Below is a breakdown
of these variables, grouped by their purpose.

All runtime settings use the `OREMI_ISINMI_` prefix and can be provided through
the environment or a `.env` file in the working directory.

### Application and Server Settings

- `OREMI_ISINMI_SERVER_HOST`: Optional. Defaults to `127.0.0.1` (`0.0.0.0` in
  Docker image). Host interface used by the Oremi Isinmi server.
- `OREMI_ISINMI_SERVER_PORT`: Optional. Defaults to `5073`. Port used by the
  Oremi Isinmi server.
- `OREMI_ISINMI_API_PREFIX`: Optional. Defaults to `/`. Prefix for all API
  routes. Must start with `/`.

### Database Settings

- `OREMI_ISINMI_DATABASE_URL`: Optional. Defaults to
  `sqlite:///./oremi_isinmi.db` (`sqlite:////oremi/data/oremi_isinmi.db` in
  Docker image). Use `sqlite:///` for SQLCipher-backed local storage, or point
  the ORM at a supported PostgreSQL, MariaDB, or MySQL URL.
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

### Realtime Notification Settings

- `OREMI_ISINMI_SSE_RETRY_TIMEOUT_SECONDS`: Optional. Defaults to `30`.
  Server-Sent Events client retry interval in seconds. Valid range: `1` to
  `120`.

### CalDAV Settings

- `OREMI_ISINMI_CALDAV_REQUEST_TIMEOUT_SECONDS`: Optional. Defaults to `30`.
  Maximum time in seconds to wait for a CalDAV server response. Valid range:
  `1` to `300`.

### Logging Settings

- `OREMI_ISINMI_LOG_LEVEL`: Optional. Defaults to `INFO`. Logging level:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `OREMI_ISINMI_LOG_FILE`: Optional. Rotating application log file path.

## Storage Layer

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

## Model Context Protocol

Oremi Isinmi implements the Model Context Protocol (MCP) using a strongly-typed
server. It exposes its core functionality as a set of tools, resources and
prompts that LLM agents can call directly.

The MCP server uses the **Streamable HTTP transport** protocol and is mounted at:

```txt
/mcp
```

### Available MCP Tools

The server provides a rich catalog of strongly-typed tools representing scheduling, reminders, notifications, and synchronization operations:

#### Reminder Management

- `create_reminder`: Schedule a new encrypted reminder with metadata and tags.
- `list_reminders`: Retrieve reminders matching filters (status, tags, datetime range, upcoming).
- `update_reminder`: Update fields of an existing reminder.
- `complete_reminder`: Mark a reminder as completed.
- `delete_reminder`: Permanently remove a reminder.

#### Calendar Event Management

- `create_event`: Book a calendar event and generate corresponding notifications.
- `get_event`: Fetch details of a single event by ID.
- `list_events`: List calendar events matching tags, status, or date range.
- `update_event`: Modify properties of a booked event.
- `delete_event`: Cancel and delete a calendar event.

#### Notifications and Alerts

- `list_notifications`: Retrieve read/unread notification logs.
- `get_unread_count`: Query the count of unread alerts.
- `mark_notification_read`: Mark a specific notification as read.
- `mark_all_notifications_read`: Bulk mark notifications as read.

### Available MCP Resources

AI agents can directly inspect the state of resources using URI-based resource paths. The resource payloads are returned as raw JSON:

- `reminders:///{reminder_id}`: Retrieves detailed state of a specific reminder.
- `events:///{event_id}`: Retrieves detailed state of a specific calendar event.
- `notifications:///{notification_id}`: Retrieves detailed state of a specific notification.

### Available MCP Prompts

The server publishes high-level prompt templates to guide AI agents in multi-step workflows:

- `schedule_day_plan`: Helps the agent organize tasks and appointments for a specific day.
- `create_event_draft`: Guides the user/agent through gathering details to draft calendar events.
- `manage_unread_alerts`: Facilitates processing unread alerts.
- `set_reminder`: Guides drafting and creating a reminder.
- `list_reminders`: Fetches and lists existing reminders from the database.
- `find_reminder`: Text search over reminder titles and descriptions.
- `update_reminder`: Details proposed reminder changes.
- `complete_reminder`: Confirms completing a reminder.
- `postpone_reminder`: Guides delaying a reminder to a new datetime.
- `delete_reminder`: Requests confirmation to delete a reminder.
- `schedule_event`: Prepares and drafts a new calendar event.
- `list_events`: Lists calendar events matching criteria.
- `find_event`: Text search over calendar events.
- `update_event`: Details proposed event changes.
- `cancel_event`: Instructs cancelling an event.
- `find_free_time`: Analyzes busy blocks and suggests open slots.
- `daily_agenda`: Chronological timeline for a single day.
- `weekly_agenda`: Week-at-a-glance agenda starting from a given date.
- `schedule_recurring_reminder`: Configures recurring reminders.
- `reminder_suggestions`: Contextual reminder templates.
- `morning_briefing`: Daily overview of agenda, active reminders, and overdue items.

## Contributing

Oremi Isinmi is built with Python and uses `uv` for dependency management. The
project follows standard Python development practices with type hints, linting,
and automated testing.

For detailed information on setting up your development environment, running
tests, code style guidelines, and the pull request process, please refer to
[CONTRIBUTING.md](https://gitlab.com/demsking/oremi-isinmi/-/blob/main/CONTRIBUTING.md).

## Versioning

Oremi Isinmi project adheres to [Semantic Versioning](https://semver.org/)
(SemVer). Version numbers follow the `MAJOR.MINOR.PATCH` format:

- **MAJOR** version increments for incompatible API changes
- **MINOR** version increments for backward-compatible new functionality
- **PATCH** version increments for backward-compatible bug fixes

The current version can be found by running:

```bash
oremi-isinmi --version
```

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

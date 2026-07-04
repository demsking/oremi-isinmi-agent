**Oremi Isinmi Agent** is a lightweight, AI-powered personal assistant designed
to help you manage your alerts, reminders, and events effortlessly. As a core
subsystem of the Oremi personal assistant ecosystem, it combines the power of
local or hosted LLMs with structured data management to provide intelligent,
privacy-first time management.

Project repository: https://gitlab.com/demsking/oremi-isinmi-agent

![Oremi Isinmi Agent Logo](./static/logo.jpg)

## Why Oremi Isinmi?

In Yorùbá culture, _Oremi_ means "my friend" and _Isinmi_ means "rest" or
"appointment." Together, they represent a friendly companion that helps you find
peace of mind by keeping your commitments organized and your time well-managed.
This agent embodies that philosophy by offering:

- **Natural Language Interaction**: Simply tell the agent what you need, and it understands
- **Smart Organization**: Use tags to categorize and find your reminders and events instantly
- **Privacy First**: Everything stays on your device with encrypted local storage
- **Real-time Notifications**: Stay informed with Server-Sent Events for alerts and reminders
- **AI-Powered Understanding**: Uses a configurable LLM backend with Ollama as the default

## Core Capabilities

- **Intelligent Reminder Management**: Create, update, and track reminders with natural language
- **Smart Event Scheduling**: Plan events with automatic reminder generation
- **Alert Handling**: Manage critical notifications with acknowledgment workflows
- **Tag-Based Organization**: Filter and find items instantly using custom tags
- **Real-time Notifications**: SSE streaming for immediate updates
- **AI Conversation**: Chat with the agent to manage your schedule
- **Encrypted Storage**: SQLAlchemy ORM with SQLCipher-backed SQLite and support for other SQL databases
- **Lightweight Deployment**: Alpine-based [Docker image](https://hub.docker.com/r/demsking/oremi-isinmi-agent) for minimal resource usage

## Use Cases

- **Personal Time Management**: "Remind me to call the dentist tomorrow at 2pm"
- **Event Planning**: "Schedule a team meeting for Friday at 10am, tag it as 'work'"
- **Alert Monitoring**: "Create a critical alert for server downtime"
- **Information Retrieval**: "Show me all my personal reminders for next week"
- **Tag Organization**: "List all events tagged as 'urgent' and 'work'"

## Security & Privacy

- Default SQLite storage is encrypted locally via SQLCipher
- Encryption key required at startup (provided via environment variable)
- No external data transmission (except optional Ollama API)
- Local-first architecture ensures data sovereignty

## Deployment

### Docker Image

The [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
Docker image is officially available on Docker Hub, supporting both
`linux/amd64` and `linux/arm64` platforms. The image is configured to expose
port `7337`, which serves the API and documentation endpoints.

The local documentation can be accessed at `http://localhost:7337/docs` for easy
reference on available endpoints and usage instructions.

### Volumes

The Docker image defines one persistent volume for application data:

- **Container path:** `/oremi/data`
- **Purpose:** SQLite database files and any other data you place under that directory

The image does not define a dedicated logs volume. If you want log files to
persist across container recreation, set `OREMI_ISINMI_LOG_FILE` to a path under
`/oremi/data` and mount that directory on the host.

### Deploy with Docker

Use the official Docker image [`demsking/oremi-isinmi-agent`](https://hub.docker.com/r/demsking/oremi-isinmi-agent)
to run Oremi Isinmi Agent:

```sh
docker run -d \
  --env-file <path_to_env_file> \
  -v ~/.config/oremi-isinmi-agent:/oremi/data \
  -p 7337:7337 \
  demsking/oremi-isinmi-agent
```

Replace `<path_to_env_file>` with the path to your
[environment variables](#description/environment-variables) file containing the
necessary configurations.

### Deploy with Docker Compose

Create a `compose.yml` file:

```yaml
services:
  agent:
    image: demsking/oremi-isinmi-agent
    restart: unless-stopped
    depends_on:
      - ollama
    ports:
      - 7337:7337
    volumes:
      - ~/.config/oremi-isinmi-agent:/oremi/data
    environment:
      OREMI_ISINMI_DATABASE_ENCRYPTION_KEY: ${OREMI_ISINMI_DATABASE_ENCRYPTION_KEY?Missing required environment variable}
      OREMI_ISINMI_OLLAMA_BASE_URL: http://ollama:11434
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7337/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  ollama:
    image: ollama/ollama
    restart: always
    runtime: nvidia
    volumes:
      - ~/.ollama:/root/.ollama
```

Run the container using `docker compose`:

```sh
docker compose up -d
```

### Environment Variables

When configuring **Oremi Isinmi Agent**, several environment variables are used to
control its behavior and connect with external services. Below is a breakdown
of these variables, grouped by their purpose.

All runtime settings use the `OREMI_ISINMI_` prefix and can be provided through
the environment or a `.env` file in the working directory.

#### Application and Server Settings

- `OREMI_ISINMI_SERVER_HOST`: Optional. Defaults to `0.0.0.0`. Host interface used by
  the Oremi Isinmi server.
- `OREMI_ISINMI_SERVER_PORT`: Optional. Defaults to `7337`. Port used by the
  Oremi Isinmi server.
- `OREMI_ISINMI_API_PREFIX`: Optional. Defaults to `/`. Prefix for all API
  routes. Must start with `/`.

#### LLM Settings

- `OREMI_ISINMI_LLM_MODEL`: Optional. Defaults to `ollama:qwen3.5:2b` when
  omitted. Fully qualified Pydantic-AI model identifier. Use provider-prefixed
  values such as `ollama:qwen3.5:2b`, `openai:gpt-4.1-mini`, or
  `anthropic:claude-sonnet-4-0`.
- `OREMI_ISINMI_LLM_REQUEST_TIMEOUT`: Optional. Defaults to `15`. Timeout in
  seconds used for agent calls and Ollama pulls. Valid range: `1` to `300`.
- `OREMI_ISINMI_LLM_TEMPERATURE`: Optional. Defaults to `0.3`. Sampling
  temperature used by the configured LLM backend. Valid range: `0.0` to `2.0`.
- `OREMI_ISINMI_OLLAMA_BASE_URL`: Optional. Ollama API base URL used only when
  the active agent model runs on Ollama.

**Examples for `OREMI_ISINMI_LLM_MODEL`:**

- Ollama default:
  - `ollama:qwen3.5:2b`
  - Use this for local development or a self-hosted Ollama deployment.
- ChatGPT / OpenAI:
  - `openai:gpt-4.1-mini`
  - Use this when the OpenAI API key is available in the environment.
- Claude / Anthropic:
  - `anthropic:claude-sonnet-4-0`
  - Use this when the Anthropic API key is available in the environment.

#### LLM Behavior Settings

- `OREMI_ISINMI_LLM_SYSTEM_PROMPT`: Optional. Defaults to the built-in Oremi
  Isinmi prompt. System prompt used by the natural-language agent.

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

- `OREMI_ISINMI_SSE_RETRY_TIMEOUT`: Optional. Defaults to `30000`.
  Server-Sent Events retry timeout in milliseconds. Valid range: `1000` to
  `120000`.

#### Logging Settings

- `OREMI_ISINMI_LOG_LEVEL`: Optional. Defaults to `INFO`. Logging level:
  `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
- `OREMI_ISINMI_LOG_FILE`: Optional. Rotating application log file path.

#### Example

```env
OREMI_ISINMI_API_PREFIX=/
OREMI_ISINMI_SERVER_HOST=0.0.0.0
OREMI_ISINMI_SERVER_PORT=7337
OREMI_ISINMI_LLM_MODEL=ollama:qwen3.5:2b
OREMI_ISINMI_LLM_REQUEST_TIMEOUT=15
OREMI_ISINMI_LLM_TEMPERATURE=0.3
OREMI_ISINMI_OLLAMA_BASE_URL=http://localhost:11434
OREMI_ISINMI_DATABASE_URL=sqlite:///oremi/data/oremi_isinmi.db
OREMI_ISINMI_DATABASE_ENCRYPTION_KEY=replace-this-with-at-least-32-characters
OREMI_ISINMI_LOG_LEVEL=INFO
OREMI_ISINMI_SSE_RETRY_TIMEOUT=30000
```

For Docker Compose, point Ollama traffic at the Compose service name when the
agent backend is Ollama:

```env
OREMI_ISINMI_OLLAMA_BASE_URL=http://ollama:11434
```

### Storage Layer

The persistence layer uses SQLAlchemy ORM instead of hand-written SQL queries.
SQLite remains encrypted through SQLCipher, while the same repositories can be
backed by PostgreSQL or MariaDB when you need a server database.

### MCP Integration

Oremi Isinmi exposes a Model Context Protocol server.

The MCP HTTP transport is mounted at:

- `GET /mcp`
- `POST /mcp`
- `DELETE /mcp`

The MCP tool catalog is generated from the Oremi Isinmi API routes that belong
to these tags:

- `Alerts Endpoints`
- `Reminders Endpoints`
- `Events Endpoints`
- `Notifications Endpoints`

The following tags are intentionally excluded from MCP tools:

- `Agent Endpoints`
- `Server Endpoints`

The MCP server is configured in HTTP mode and reuses the Oremi Isinmi app's
OpenAPI schema, so tool descriptions stay in sync with the public API. Response
schemas are described in full for better client generation and assistant
planning.

## Contributing

Oremi Device is built with Python and uses `uv` for dependency management. The
project follows standard Python development practices with type hints, linting,
and automated testing.

For detailed information on setting up your development environment, running
tests, code style guidelines, and the pull request process, please refer to
[CONTRIBUTING.md](https://gitlab.com/demsking/oremi-isinmi-agent/-/blob/main/CONTRIBUTING.md).

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

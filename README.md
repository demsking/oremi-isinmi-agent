# Oremi Isinmi Agent

[![Buy me a beer](https://img.shields.io/badge/Buy%20me-a%20beer-1f425f.svg)](https://www.buymeacoffee.com/demsking)

Oremi Isinmi Agent is the alerts, reminders, scheduling, tags, and notification
subsystem for the Oremi personal assistant project. It uses FastAPI, Pydantic,
SQLCipher-encrypted SQLite, Server-Sent Events, and Pydantic-AI with Ollama as
the default backend.

The name **"Oremi Isinmi Agent"** comes from two Yorùbá words: _Oremi_,
meaning "my friend", and _Isinmi_, meaning "rest" or "appointment". Together,
the name conveys the idea of a friendly assistant that helps you manage your
time and commitments efficiently, bringing calm and order to your daily life.

![Oremi Isinmi Agent Logo](htdocs/logo.jpg)

## Documentation

Find the Oremi Isinmi Agent deployment and API documentation at
[https://demsking.gitlab.io/oremi-isinmi-agent](https://demsking.gitlab.io/oremi-isinmi-agent).

## Core Capabilities

- **Intelligent Reminder Management**: Create, update, and track reminders with natural language
- **Smart Event Scheduling**: Plan events with automatic reminder generation
- **Alert Handling**: Manage critical notifications with acknowledgment workflows
- **Tag-Based Organization**: Filter and find items instantly using custom tags
- **Real-time Notifications**: SSE streaming for immediate updates
- **AI Conversation**: Chat with the agent to manage your schedule
- **Encrypted Storage**: All data secured with SQLCipher
- **Lightweight Deployment**: Alpine-based [Docker image](https://hub.docker.com/r/demsking/oremi-isinmi-agent) for minimal resource usage

## Use Cases

- **Personal Time Management**: "Remind me to call the dentist tomorrow at 2pm"
- **Event Planning**: "Schedule a team meeting for Friday at 10am, tag it as 'work'"
- **Alert Monitoring**: "Create a critical alert for server downtime"
- **Information Retrieval**: "Show me all my personal reminders for next week"
- **Tag Organization**: "List all events tagged as 'urgent' and 'work'"

## Model Context Protocol

The app exposes an MCP HTTP endpoint at `/mcp`. The available tools are derived
from the `Alerts`, `Reminders`, `Events`, and `Notifications` API tags. `Agent`
and `Health` are not exported as MCP tools.

## Contribute

Please follow [CONTRIBUTING.md](https://gitlab.com/demsking/oremi-isinmi-agent/blob/main/CONTRIBUTING.md).

## Versioning

Given a version number `MAJOR.MINOR.PATCH`, increment the:

- `MAJOR` version when you make incompatible API changes,
- `MINOR` version when you add functionality in a backwards-compatible manner,
  and
- `PATCH` version when you make backwards-compatible bug fixes.

Additional labels for pre-release and build metadata are available as extensions
to the `MAJOR.MINOR.PATCH` format.

See [SemVer.org](https://semver.org/) for more details.

## License

Licensed under the Apache License, Version 2.0 (the "License"); you may not use
this file except in compliance with the License.
You may obtain a copy of the License at
[LICENSE](https://gitlab.com/demsking/oremi-isinmi-agent/blob/main/LICENSE).

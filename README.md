# Oremi Isinmi

[![Buy me a beer](https://img.shields.io/badge/Buy%20me-a%20beer-1f425f.svg)](https://www.buymeacoffee.com/demsking)

Oremi Isinmi is the reminders, scheduling, tags, and notification
subsystem for the Oremi personal assistant project. It uses FastAPI, Pydantic,
SQLCipher-encrypted SQLite, Server-Sent Events, and Pydantic-AI with Ollama as
the default backend.

The name **"Oremi Isinmi"** comes from two Yorùbá words: _Oremi_,
meaning "my friend", and _Isinmi_, meaning "rest" or "appointment". Together,
the name conveys the idea of a friendly assistant that helps you manage your
time and commitments efficiently, bringing calm and order to your daily life.

![Oremi Isinmi Logo](htdocs/logo.jpg)

## Documentation

Find the Oremi Isinmi deployment and API documentation at
[https://demsking.gitlab.io/oremi-isinmi](https://demsking.gitlab.io/oremi-isinmi).

## Core Capabilities

- **Intelligent Reminder Management**: Create, update, and track reminders with natural language
- **Smart Event Scheduling**: Plan events with automatic reminder generation
- **Tag-Based Organization**: Filter and find items instantly using custom tags
- **Real-time Notifications**: SSE streaming for immediate updates
- **AI Conversation**: Chat with the agent to manage your schedule
- **Encrypted Storage**: All data secured with SQLCipher
- **Lightweight Deployment**: Alpine-based [Docker image](https://hub.docker.com/r/demsking/oremi-isinmi) for minimal resource usage

## Use Cases

- **Personal Time Management**: "Remind me to call the dentist tomorrow at 2pm"
- **Event Planning**: "Schedule a team meeting for Friday at 10am, tag it as 'work'"
- **Information Retrieval**: "Show me all my personal reminders for next week"
- **Tag Organization**: "List all events tagged as 'urgent' and 'work'"

## Model Context Protocol

The app exposes an MCP HTTP endpoint at `/mcp`. The available tools are derived
from the `Reminders`, `Events`, and `Notifications` API tags. `Agent`
and `Health` are not exported as MCP tools.

## Contribute

Please follow [CONTRIBUTING.md](https://gitlab.com/demsking/oremi-isinmi/blob/main/CONTRIBUTING.md).

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

Copyright 2026 Sébastien Demanou. All Rights Reserved.

Licensed under the Apache License, Version 2.0. See the
[LICENSE](https://gitlab.com/demsking/oremi-isinmi/-/blob/main/LICENSE) for the
complete license text.

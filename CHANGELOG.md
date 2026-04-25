# Changelog

All notable changes to DecisionGraph are documented in this file.

## 2026-04-25

### Added
- Supersede flow across API, CLI, chat, and MCP.
- Assumption watcher with severity transitions, optional notifications, and benchmark gate support in CI.
- Decision timeline endpoint/command and evidence quality scoring.
- Decision merge/deduplicate flow for consolidating overlapping decisions.
- Governance policy mode (`off`, `warn`, `strict`) with configurable required fields.
- Audit log events and retrieval endpoints/commands/tools.
- Connector-aware watcher notifications via `webhook`, `slack`, `discord`, and `teams`.
- CLI command-level test coverage for newly added commands.

### Changed
- Store schema updated to support `watch_state` and `audit_logs`.
- Audit log retention is now configurable via `DECISIONGRAPH_AUDIT_LOG_RETENTION`.
- Ingestion API/CLI now return clean validation errors under governance strict mode.

### Docs
- README expanded to cover new API routes, CLI commands, environment variables, and usage examples.
- `.env.example` updated with governance, alert connector, and audit retention variables.

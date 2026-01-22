# Changelog

All notable changes to BentWookie will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Error capture and display in web UI for failed requests
- Auto-create bug-fix requests when processing errors occur
- Enhanced test phase prompts targeting 100% code coverage
- Edge case testing checklist in test phase

## [0.2.0] - 2025-01-21

### Added
- SQLite database for persistent state management
- Claude Agent SDK integration for automated processing
- Phase-based workflow: plan → dev → test → deploy → verify → document
- CLI interface with Click (`bw` command)
- Web UI dashboard with Flask
- Daemon mode for background processing
- Rate limit handling with automatic retry and backoff
- Project and request management
- Infrastructure configuration (compute, storage, queue, access)
- Learnings/notes system per project
- Test retry mechanism with configurable max retries
- Authentication modes: Claude Max (web auth) and API key

### Changed
- Complete rewrite from v1 file-based system to SQLite
- Replaced stage directories with phase field on requests

## [0.1.0] - 2025-01-18

### Added
- Initial proof of concept
- File-based task management
- Basic wizard for project setup
- Markdown task templates

[Unreleased]: https://github.com/bentwookie/bentwookie/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/bentwookie/bentwookie/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bentwookie/bentwookie/releases/tag/v0.1.0

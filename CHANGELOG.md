# Changelog

All notable changes to AmbientOps are documented in this file.

## [1.1.0] - 2026-10-11
### Added
- **Calm Mission Control UI**: Migrated from neon glassmorphic design to technical minimal off-white paper canvas, forest ink, and crisp 1px structural borders.
- **Human Approval Boundary**: Built explicit operator approval gate (`PENDING_OPERATOR_APPROVAL` -> `SIMULATION_APPROVED`) ensuring no automated actuation occurs without operator confirmation.
- **MCP Interoperability Suite**: Added `tests/test_mcp_interop.py` validating MCP specification v2025-11-25 handshake, tool discovery, and error handling.
- **Security Hardening**: Injected Content-Security-Policy, X-Content-Type-Options, Referrer-Policy, and X-Request-ID headers. Configured explicit CORS allowlists.
- **DOM Injection Protection**: Refactored `frontend/app.js` to eliminate unsafe `innerHTML` usage with untrusted strings.
- **Comprehensive Documentation**: Added architecture specs, demo script, product feedback report, test report, submission checklist, and CI workflow.

### Changed
- Renamed custom simulation layer to **Smart Entry Event Simulator** (`smart_entry_simulator.py`) with honest simulation disclosures. Removed unverified Ring track eligibility claims while retaining compatibility aliases.
- Raised automated test coverage from 78% to **92% measured coverage** with 35 passing tests.
- Updated Bedrock agent to standard AWS credential provider chain with explicit provider mode disclosures (`bedrock-live` vs `deterministic-simulator`).

## [1.0.0] - 2026-10-11
### Added
- Initial project scaffolding: Model Context Protocol (MCP) server, Bedrock cognitive triage agent, and Streamable HTTP SSE transport.

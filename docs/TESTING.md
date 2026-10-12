# Testing & Quality Assurance Guide

AmbientOps is backed by a comprehensive automated test suite verifying Model Context Protocol (MCP v2025-11-25) compliance, Amazon Bedrock reasoning pipelines, human operator approval workflows, security headers, and API integrity.

---

## 1. Measured Test Results Summary

* **Total Test Cases**: **46 passing**
* **Test Pass Rate**: **100% (46 passed, 0 failed)**
* **Measured Statement Coverage**: **87%** (703 total statements, 88 missed, 87.5%)
* **Accessibility Violations**: **0 (Axe-core WCAG 2.1 AA Compliant)**

### Breakdown by Module
| Module | Statements | Missed | Measured Coverage |
| :--- | :--- | :--- | :--- |
| `backend/__init__.py` | 0 | 0 | **100%** |
| `backend/smart_entry_simulator.py` | 46 | 0 | **100%** |
| `backend/mcp_protocol.py` | 54 | 0 | **100%** |
| `backend/config.py` | 26 | 0 | **100%** |
| `backend/ring_simulator.py` | 2 | 0 | **100%** |
| `backend/server.py` | 229 | 20 | **91%** |
| `backend/bedrock_agent.py` | 97 | 20 | **79%** |
| `backend/mcp_server.py` | 249 | 48 | **81%** |
| **Project Total** | **703** | **88** | **87%** |

---

## 2. Test Execution Commands

### Run Full Test Suite with Verbose Output
```bash
pytest tests/ -v
```

### Run Full Test Suite with Coverage Report
```bash
pytest --cov=backend --cov-report=term-missing tests/
```

### Run MCP Protocol Interoperability Tests Only
```bash
pytest tests/test_mcp_interop.py -v
```

### Run Human Approval Boundary & Operator Tests Only
```bash
pytest tests/test_approval_flow.py -v
```

### Run Security Headers & CORS Tests Only
```bash
pytest tests/test_security_headers.py -v
```

---

## 3. Test Suites Overview

1. **`tests/test_mcp_interop.py`**: Validates strict MCP v2025-11-25 Streamable HTTP transport and JSON-RPC 2.0 lifecycle:
   - Official Python MCP SDK (`mcp==2.3.0`) client handshake and tool invocation over Streamable HTTP `/mcp`.
   - Protocol negotiation, 202 bodyless notifications, session ID headers (`Mcp-Session-Id`).
   - App factory (`create_app`) and repeated lifespan lifecycle isolation without global task group leakage.
   - Tool discovery (`tools/list`), execution (`tools/call` for all 5 registered tools), resources, and prompts.
   - Structured JSON-RPC error codes (-32700 Parse error, -32600 Invalid request, -32601 Method not found, -32602 Invalid params).
2. **`tests/test_approval_flow.py`**: Validates the operator sequence:
   - Event trigger &rarr; Structured evidence creation &rarr; Bedrock analysis &rarr; Transition to `PENDING_OPERATOR_APPROVAL`
   - Explicit operator approval &rarr; Remediation execution &rarr; `SIMULATION_APPROVED` and outcome verification
   - Explicit operator rejection &rarr; `OPERATOR_REJECTED`
   - Idempotent approval transitions (409 Conflict on duplicate review) and 404 error handling.
3. **`tests/test_bedrock_mocking.py` & `tests/test_bedrock_agent.py`**: Validates AWS Bedrock client handling:
   - Mocked Claude 3.5 Sonnet JSON response parsing
   - Fallback and degraded mode handling when AWS services throttle or encounter errors
   - Safe deterministic offline simulator default requiring explicit opt-in for live Bedrock.
4. **`tests/test_security_headers.py`**: Validates security and middleware:
   - CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
   - `X-Request-ID` tracing header propagation
   - DNS rebinding prevention and explicit CORS allowlist validation
   - Runtime telemetry on `/api/runtime`.
5. **`tests/test_e2e_pipeline.py`**: End-to-end FastAPI integration testing.
6. **`tests/test_ring_simulator.py`**: Deterministic sensor and event simulation testing.
7. **`tests/test_browser_e2e.py`**: Playwright browser E2E test suite:
   - Responsive UI rendering across mobile (375px), tablet (768px), and desktop (1280px) viewports with zero horizontal overflow.
   - Full operator workflow: scenario triggering, evidence rendering, Bedrock triage verification, manual approval click, outcome confirmation, and simulated audio playback.
   - Automated Axe-core accessibility audit confirming 0 WCAG 2.1 AA violations.
   - MCP protocol runner verification checking for "5/5 automated MCP transport checks passed".

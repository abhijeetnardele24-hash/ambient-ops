# Testing & Quality Assurance Guide

AmbientOps is backed by a comprehensive automated test suite verifying Model Context Protocol (MCP v2025-11-25) compliance, Amazon Bedrock reasoning pipelines, human operator approval workflows, security headers, and API integrity.

---

## 1. Measured Test Results Summary

* **Total Test Cases**: **35 passing**
* **Test Pass Rate**: **100% (35 passed, 0 failed)**
* **Measured Statement Coverage**: **92%** (543 total statements, 46 missed)

### Breakdown by Module
| Module | Statements | Missed | Measured Coverage |
| :--- | :--- | :--- | :--- |
| `backend/smart_entry_simulator.py` | 46 | 0 | **100%** |
| `backend/mcp_protocol.py` | 54 | 0 | **100%** |
| `backend/config.py` | 19 | 0 | **100%** |
| `backend/ring_simulator.py` | 2 | 0 | **100%** |
| `backend/mcp_server.py` | 159 | 14 | **91%** |
| `backend/server.py` | 176 | 20 | **89%** |
| `backend/bedrock_agent.py` | 87 | 12 | **86%** |
| **Project Total** | **543** | **46** | **92%** |

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

1. **`tests/test_mcp_interop.py`**: Validates strict MCP v2025-11-25 JSON-RPC 2.0 lifecycle:
   - Handshake (`initialize` with protocol version negotiation)
   - Initialized notifications
   - Tool discovery (`tools/list`)
   - Tool execution (`tools/call` for all 5 registered tools)
   - Resource read and Prompt retrieval
   - Structured error codes (-32700 Parse error, -32600 Invalid request, -32601 Method not found, -32602 Invalid params).
2. **`tests/test_approval_flow.py`**: Validates the operator sequence:
   - Event trigger &rarr; Structured evidence creation &rarr; Bedrock analysis &rarr; Transition to `PENDING_OPERATOR_APPROVAL`
   - Explicit operator approval &rarr; Remediation execution &rarr; `SIMULATION_APPROVED` and outcome verification
   - Explicit operator rejection &rarr; `OPERATOR_REJECTED`
   - 404 error handling for non-existent events or incidents.
3. **`tests/test_bedrock_mocking.py`**: Validates AWS Bedrock client handling:
   - Mocked Claude 3.5 Sonnet JSON response parsing
   - Fallback and degraded mode handling when AWS services throttle or encounter errors
   - Automatic fallback to deterministic simulator when credentials are absent.
4. **`tests/test_security_headers.py`**: Validates security and middleware:
   - CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy
   - `X-Request-ID` tracing header propagation
   - Explicit CORS allowlist validation
   - Runtime telemetry on `/api/runtime`.
5. **`tests/test_e2e_pipeline.py`**: End-to-end FastAPI integration testing.
6. **`tests/test_ring_simulator.py`**: Deterministic sensor and event simulation testing.

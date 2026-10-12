# Challenge Requirements & Evidence Matrix

**Competition**: *Build, Ship, Shape: Amazon Developer Hackathon 2026*  
**Portal**: [amazonappdev2026.devpost.com](https://amazonappdev2026.devpost.com/)  
**Primary Track**: **Alexa+ Track** (Model Context Protocol, MCP specification v2025-11-25)  
**Mini-Challenge**: **AWS Builder Mini-Challenge** (Amazon Bedrock / Claude 3.5 Sonnet)  

---

## 1. Requirement-to-Evidence Matrix

| Challenge Requirement | Repository Evidence | Current Status | Required Change | Verification Result |
| :--- | :--- | :--- | :--- | :--- |
| **1. Primary Track: Alexa+ (MCP Integration)** | `backend/mcp_server.py`, `backend/mcp_protocol.py`, `frontend/index.html` (Web Simulator) | **5/5 MCP Transport Checks Passed** | Conformed to MCP specification v2025-11-25 with canonical Streamable HTTP transport (`/mcp`), official `mcp.server.mcpserver.MCPServer` (v2.3.0), and session-scoped lifecycle. Voice dispatch is simulated via browser Web Speech API (`window.speechSynthesis`). | Verified in `tests/test_mcp_interop.py` (handshake, tools/list, tools/call, session headers, error envelopes). |
| **2. AWS Builder Mini-Challenge (Amazon Bedrock)** | `backend/bedrock_agent.py` | **Verified (Safe Simulator Default)** | Uses Amazon Bedrock Converse API / Claude 3.5 Sonnet with standard AWS credential provider chain, requiring explicit opt-in (`ENABLE_LIVE_BEDROCK=true`) and defaulting safely to deterministic simulator mode. Optional verification script (`scripts/verify_live_bedrock.py`) validates live calls when credentials exist. | Verified in `tests/test_bedrock_agent.py` and `tests/test_bedrock_mocking.py`. |
| **3. Smart Entry Simulation (No Ring Track Claim)** | `backend/smart_entry_simulator.py` | **Fully Disclosed Simulation** | Evaluated via Smart Entry Event Simulator; marked all events as `is_simulated = True`. Does not claim official Ring developer SDK or Ring-track eligibility. | Verified: No claims of official Ring Developer Playground or hardware. |
| **4. Human Approval Boundary** | `backend/server.py`, `frontend/app.js` | **Fully Implemented** | Operator sequence implemented: Trigger &rarr; Observe evidence &rarr; Analyze &rarr; Review recommendation &rarr; **Approve simulation** &rarr; Verify outcome. | Verified in `tests/test_approval_flow.py` (transitions from `PENDING_OPERATOR_APPROVAL` to `SIMULATION_APPROVED`). |
| **5. Calm Mission Control UI** | `frontend/styles.css`, `frontend/index.html` | **Axe Scan Zero Violations** | Flat technical minimal UI: paper canvas (`#f8f9fa`), forest ink (`#0e1f18`), white surfaces, 1px structural borders, accessible contrast. Automated Axe scan found zero violations across mobile and desktop viewports. | Verified via browser subagent and automated Playwright Axe audit. |
| **6. Security Hardening** | `backend/server.py`, `SECURITY.md` | **Fully Implemented** | CSP, X-Content-Type-Options, X-Frame-Options, X-Request-ID, DNS rebinding host protection, CORS allowlist, and zero-innerHTML DOM construction. | Verified in `tests/test_security_headers.py`. |
| **7. Measured Automated Test Coverage** | `tests/` (46 tests) | **46 Passed (87% Coverage)** | 46 tests passing with 87% measured statement coverage across backend, including Streamable HTTP interop, approval flow, and Playwright E2E + Axe accessibility tests. | Verified: `pytest --cov=backend tests/` reports 87.5% coverage with 0 failures. |
| **8. Official Developer Friction Log (+10% Bonus)** | `docs/FRICTION_LOG.md` | **Fully Documented** | 4-pillar technical friction log in official 7-field format evaluating Alexa+ MCP Streamable HTTP transports, bounding box normalization, Bedrock schema validation, and DNS rebinding protections. | Accessible via UI modal and documented in repo. |
| **9. Deployment Readiness** | `Dockerfile`, `docker-compose.yml`, `requirements.txt` | **Fully Prepared** | Single local command start (`uvicorn backend.server:app`), safe default deterministic simulator mode, Docker healthcheck endpoint verification in CI. | Verified local server startup and container health check at `/health`. |
| **10. Devpost Submission Package** | `docs/DEVPOST_SUBMISSION.md`, `docs/DEMO_SCRIPT.md` | **Fully Prepared** | Complete copy aligned with judging rubric, conditional video demo script, shot list, tags, and feedback report ready for submission. | Ready for owner review before final submission. |

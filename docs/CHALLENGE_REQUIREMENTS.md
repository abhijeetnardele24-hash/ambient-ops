# Challenge Requirements & Evidence Matrix

**Competition**: *Build, Ship, Shape: Amazon Developer Hackathon 2026*  
**Portal**: [amazonappdev2026.devpost.com](https://amazonappdev2026.devpost.com/)  
**Primary Track**: **Alexa+ Track** (Model Context Protocol, MCP specification v2025-11-25)  
**Mini-Challenge**: **AWS Builder Mini-Challenge** (Amazon Bedrock / Claude 3.5 Sonnet)  

---

## 1. Requirement-to-Evidence Matrix

| Challenge Requirement | Repository Evidence | Current Status | Required Change | Verification Result |
| :--- | :--- | :--- | :--- | :--- |
| **1. Primary Track: Alexa+ (MCP Integration)** | `backend/mcp_server.py`, `backend/mcp_protocol.py`, `frontend/index.html` (Web Simulator) | **100% Implemented** | Conformed to MCP specification v2025-11-25 with Streamable HTTP SSE transport (`/mcp/sse`) and JSON-RPC 2.0 (`/mcp`). | Verified in `tests/test_mcp_interop.py` (handshake, tools/list, tools/call, error envelopes). |
| **2. AWS Builder Mini-Challenge (Amazon Bedrock)** | `backend/bedrock_agent.py` | **100% Implemented** | Uses Amazon Bedrock Converse API / Claude 3.5 Sonnet with standard AWS credential provider chain and explicit offline deterministic simulator mode. | Verified in `tests/test_bedrock_agent.py` and `tests/test_bedrock_mocking.py`. |
| **3. Ring Integration Realism** | `backend/smart_entry_simulator.py` | **100% Honest Disclosure** | Renamed to Smart Entry Event Simulator; marked all events as `is_simulated = True`; removed unverified Ring-track eligibility claims. | Verified: No fake claims of official Ring Developer Playground. |
| **4. Human Approval Boundary** | `backend/server.py`, `frontend/app.js` | **100% Implemented** | Operator sequence implemented: Trigger &rarr; Observe evidence &rarr; Analyze &rarr; Review recommendation &rarr; **Approve simulation** &rarr; Verify outcome. | Verified in `tests/test_approval_flow.py` (transitions from `PENDING_OPERATOR_APPROVAL` to `SIMULATION_APPROVED`). |
| **5. Calm Mission Control UI** | `frontend/styles.css`, `frontend/index.html` | **100% Implemented** | Flat technical minimal UI: paper canvas (`#f8f9fa`), forest ink (`#0e1f18`), white surfaces, 1px structural borders, accessible contrast. | Verified via browser subagent audit across desktop and responsive viewports. |
| **6. Security Hardening** | `backend/server.py`, `SECURITY.md` | **100% Implemented** | CSP, X-Content-Type-Options, X-Frame-Options, X-Request-ID, CORS allowlist, and zero-innerHTML DOM construction. | Verified in `tests/test_security_headers.py`. |
| **7. Measured Automated Test Coverage** | `tests/` (35 tests) | **100% Passing (92% Coverage)** | Raised test count from 18 to 35 tests, achieving 92% measured coverage across critical backend modules. | Verified: `pytest --cov=backend tests/` reports 92% coverage. |
| **8. Official Developer Friction Log (+10% Bonus)** | `docs/FRICTION_LOG.md` | **100% Implemented** | 4-pillar technical friction log evaluating Alexa+ MCP SSE transports, bounding box normalization, and Bedrock schema validation. | Accessible via UI modal and documented in repo. |
| **9. Deployment Readiness** | `Dockerfile`, `docker-compose.yml`, `requirements.txt` | **100% Prepared** | Single local command start (`uvicorn backend.server:app`), zero paid credential dependencies for default simulator. | Verified local server startup at `http://localhost:8000`. |
| **10. Devpost Submission Package** | `docs/DEVPOST_SUBMISSION.md`, `docs/DEMO_SCRIPT.md` | **100% Prepared** | Complete copy, 3-minute video demo script, shot list, tags, and feedback report ready for submission. | Ready for owner review before final submission. |

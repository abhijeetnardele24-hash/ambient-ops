# Developer Friction Log: Amazon Alexa+ MCP & Smart Entry Ecosystem
**Event**: *Build, Ship, Shape: Amazon Developer Hackathon 2026*  
**Tracks**: Alexa+ (MCP & Agent Skills), AWS Builder Mini-Challenge  
**Participant**: Team MetaMask (Abhijeet Nardele)  
**Deliverable**: Official +10% Evaluation Bonus Entry  
**Status**: Verified against Implemented Architecture  

---

## 1. Executive Summary
This friction log documents concrete technical obstacles, protocol nuances, and developer experience (DX) friction discovered during the architectural design, implementation, and verification of **AmbientOps**—an autonomous multi-device incident response console uniting smart entry sensors, Amazon Bedrock reasoning, and Alexa+ proactive voice dispatch via Model Context Protocol (v2025-11-25).

Each log entry strictly adheres to the standard 7-field incident evaluation rubric:
1. **Task Attempted**
2. **Steps Taken**
3. **Expected Result**
4. **Actual Result**
5. **Severity**
6. **Workaround Implemented in AmbientOps**
7. **Actionable Recommendation for Amazon Engineering**

---

## 2. Friction Log Entry 1: Alexa+ Streamable HTTP MCP Notifications & Response Formatting

* **Task Attempted**: Implement official Model Context Protocol (v2025-11-25) Streamable HTTP transport handshake between web client and backend (`POST /mcp`).
* **Steps Taken**:
  1. Client sends `initialize` request (`method: "initialize"`, `protocolVersion: "2025-11-25"`).
  2. Server returns JSON-RPC response with `Mcp-Session-Id` header.
  3. Client acknowledges initialization by transmitting JSON-RPC notification `notifications/initialized` with `Mcp-Session-Id`.
* **Expected Result**: Clean 200 or 202 acknowledgment consistent across HTTP client frameworks.
* **Actual Result**:
  - The official MCP Streamable HTTP specification dictates that JSON-RPC notifications must return an HTTP 202 Accepted response with **no body** (`text == ""`).
  - Standard browser `fetch()` and client libraries expecting JSON payloads threw `SyntaxError: Unexpected end of JSON input` when calling `.json()` on notification responses.
  - Furthermore, when servers return `text/event-stream` framing for responses without `json_response=True`, standard JSON parsers fail on `event: message\ndata: {...}` framing.
* **Severity**: Major (causes client handshake crashes and connection dropouts).
* **Workaround Implemented in AmbientOps**:
  - Built an ASGI notification interceptor ensuring `notifications/initialized` strictly issues an empty HTTP 202 response body without JSON serialization attempts.
  - Implemented `parseMcpResponseBody()` in `frontend/app.js` with dual-mode parsing capable of extracting raw JSON-RPC envelopes from both direct `application/json` bodies and SSE-framed `data: ` chunks.
* **Actionable Recommendation for Amazon Engineering**:
  - Provide an official `@amazon/alexa-mcp-client` JavaScript/TypeScript browser SDK that encapsulates Streamable HTTP transport framing, notification empty-body handling, and automatic session header injection.
  - Document client-side bodyless response handling explicitly in the Alexa+ MCP Quickstart documentation.

---

## 3. Friction Log Entry 2: Smart Entry Computer Vision Bounding Box Normalization

* **Task Attempted**: Translate simulated smart doorbell and perimeter camera detections into responsive SVG viewports and Bedrock multimodal context.
* **Steps Taken**:
  1. Ingest camera event detection records containing bounding box coordinates.
  2. Map bounding boxes to SVG overlay canvas (`viewBox="0 0 640 360"`).
  3. Format bounding coordinates for agent prompt reasoning.
* **Expected Result**: Standardized coordinate ordering consistent across AWS AI services and web standards (`[x, y, width, height]`).
* **Actual Result**:
  - Camera detection telemetry delivered bounding coordinates in normalized `[ymin, xmin, ymax, xmax]` format (0.0 to 1.0).
  - SVG canvases require absolute pixel values for `(x, y)` top-left anchor, `width`, and `height`.
  - Discrepancy required manual coordinate conversion math and edge clamping to prevent bounding boxes from rendering off-stage.
* **Severity**: Moderate (developer friction and coordinate misalignment bugs during visual validation).
* **Workaround Implemented in AmbientOps**:
  - Implemented typed coordinate normalization helpers in `backend/smart_entry_simulator.py` and DOM node builders in `frontend/app.js`:
    ```javascript
    const [ymin, xmin, ymax, xmax] = d.box_normalized;
    const boxX = xmin * 640;
    const boxY = ymin * 360;
    const boxW = (xmax - xmin) * 640;
    const boxH = (ymax - ymin) * 360;
    ```
* **Actionable Recommendation for Amazon Engineering**:
  - Provide typed Pydantic models and TypeScript interfaces for smart vision events in the Amazon smart home developer kits, including built-in `.to_rect()` helper methods.

---

## 4. Friction Log Entry 3: Amazon Bedrock Converse API Tool Schema Strictness

* **Task Attempted**: Expose MCP tool specifications directly into Amazon Bedrock Converse API (`bedrock-runtime.converse`) for model tool-use.
* **Steps Taken**:
  1. Register tools with the MCP server using Pydantic models.
  2. Extract JSON schemas via `tools/list`.
  3. Transform schemas into `toolConfig.tools[].toolSpec` structures for `boto3.client("bedrock-runtime").converse`.
* **Expected Result**: Bedrock Converse API accepts standard JSON Schema outputs generated by MCP tool declarations.
* **Actual Result**:
  - Bedrock Converse API rejects JSON Schemas containing `$defs`, complex `anyOf`/`oneOf` unions, or arbitrary metadata fields (`ValidationException: invalid tool specification`).
  - Dynamic MCP tools from third-party servers easily trigger validation rejections if schemas are not stripped and sanitized before dispatch.
* **Severity**: Major (blocks autonomous agent reasoning if tool schemas violate strict subsets).
* **Workaround Implemented in AmbientOps**:
  - Developed strict Pydantic schemas in `backend/bedrock_agent.py` and `backend/mcp_server.py` that avoid unsupported JSON Schema constructs and provide explicit fallback sanitization before calling Bedrock.
  - Implemented deterministic simulator mode ensuring full triage reliability and zero unhandled exceptions when credentials or regions are unavailable.
* **Actionable Recommendation for Amazon Engineering**:
  - Publish an open-source AWS Bedrock MCP Bridge package (`boto3-bedrock-mcp`) that automatically resolves, strips, and formats MCP tool definitions into compliant Bedrock `toolSpec` structures.

---

## 5. Friction Log Entry 4: DNS Rebinding Protection vs. Local Development Port Flexibility

* **Task Attempted**: Run local integration testing and automated end-to-end browser tests across dynamically allocated local ports.
* **Steps Taken**:
  1. Configure `TransportSecuritySettings` on `MCPServer`.
  2. Run automated Playwright tests binding to dynamic ephemeral localhost ports (e.g. `127.0.0.1:54321`).
  3. Execute MCP tools over Streamable HTTP from test harness and browser.
* **Expected Result**: Valid localhost loopback traffic is accepted while remote DNS rebinding attacks are prevented.
* **Actual Result**:
  - Rigid `allowed_hosts` string matching without port wildcard support (`localhost:*`, `127.0.0.1:*`) resulted in HTTP 421 Misdirected Request errors during automated test runs using random port assignment.
  - Origin headers from test servers without exact port matches were rejected with HTTP 403 Forbidden.
* **Severity**: Major (breaks CI pipelines and dynamic test harnesses).
* **Workaround Implemented in AmbientOps**:
  - Configured wildcard port patterns (`127.0.0.1:*`, `localhost:*`, `0.0.0.0:*`) in `TransportSecuritySettings` and added hostname normalization in custom middleware.
* **Actionable Recommendation for Amazon Engineering**:
  - Ensure official Alexa+ MCP tooling explicitly supports loopback interface wildcarding in development modes (`ENABLE_LOCAL_DEV_BYPASS=true`) to streamline CI/CD workflows while maintaining strict enforcement in production.

---

## 6. Summary & Positive Highlights
Despite these initial developer friction points, Amazon’s architectural choice to build Alexa+ on open Model Context Protocol standards represents a transformative leap forward for ambient computing:
- **Decoupled Architecture**: Device state and actions are decoupled from proprietary cloud silos.
- **Universal Tooling**: Any compliant MCP client or agent can reason over smart entry telemetry without bespoke SDK rewrites.
- **Human-in-the-Loop Safety**: Combining structured Bedrock reasoning with an explicit operator approval gate provides the ideal balance of ambient speed and operational safety.

# Devpost Submission Package: AmbientOps

## Project Title
**AmbientOps: Ambient Incident Response Console for Alexa+ & Smart Sensors**

## Tagline (Under 140 chars)
*Ambient operational incident response connecting smart sensors and Amazon Bedrock to Alexa+ through the Model Context Protocol.*

---

## Tracks Entered
1. **Alexa+ Track (Primary)**: Building next-generation ambient add-ons using the **Model Context Protocol (MCP)** open standard (specification v2025-11-25) for Agent Skills and Streamable HTTP transports.
2. **AWS Builder Mini-Challenge**: Advanced generative AI reasoning and triage using **Amazon Bedrock (Claude 3.5 Sonnet / Bedrock Converse API)**.

*(Note: Smart entry cameras and sensors are tested via our internal Smart Entry Event Simulator; all events are explicitly disclosed as simulated).*

---

## Inspiration
Today’s smart homes suffer from "notification fatigue." When a security camera spots movement, it pings your phone with a generic alert. When a courier drops off a package in the pouring rain, you often find out hours later when the box is already soaked. When an elderly relative remains motionless in a hallway, traditional motion sensors remain passive until a crisis unfolds.

With Amazon introducing the **Model Context Protocol (MCP)** for **Alexa+**, we realized we could bridge passive camera streams with intelligent, contextual ambient voice assistants. Instead of blasting phones with noisy alerts, smart homes should possess **situational awareness**—reasoning about whether to whisper, speak up, or silently remediate, while always maintaining an **explicit human approval boundary**.

---

## What It Does
**AmbientOps** is an ambient incident-response console that connects smart sensor feeds with Alexa+ using standard MCP protocols and Amazon Bedrock reasoning:

1. **Trigger Simulated Event**: Ingests realistic environmental sensor events from simulated smart entry cameras—including packages left in rain, care recipient prolonged immobility, pet perimeters, and night loitering.
2. **Observe Structured Evidence**: Normalizes detections (bounding boxes, confidence levels), environmental telemetry (precipitation forecasts, ambient lux), and resident context into structured evidence.
3. **Bedrock Cognitive Triage**: Evaluates events using Amazon Bedrock (Claude 3.5 Sonnet) to compute a dynamic **Risk Index (0-100)**, assess environmental conditions, and formulate a concise **Decision Rationale** and **Recommended Action**.
4. **Human Approval Boundary**: The system pauses at an explicit operator gate (`PENDING_OPERATOR_APPROVAL`). The human operator inspects the evidence and recommendation, and must click **"Approve Simulation"** before any action executes.
5. **Proactive Alexa+ Voice Dispatch**: If vocal intervention is recommended and approved, the agent dispatches natural, conversational speech directly to the Alexa+ endpoint (*"Excuse me, Resident. Your front porch camera observed a package delivery, and rain is forecast in 15 minutes. Would you like me to unlock the porch storage bench?"*).
6. **Simulated Action & Outcome Verification**: Executes the remediation simulation (e.g. unlocking porch storage benches, illuminating pathway lights) and records an auditable entry in the incident ledger.
7. **Live MCP Protocol Inspector**: Displays real-time, bidirectional JSON-RPC 2.0 messages, Streamable HTTP streams, tool schemas, and latencies.

---

## How We Built It
* **Official MCP Server Engine**: Implemented using the official Model Context Protocol SDK (`mcp==2.3.0` / `MCPServer`) adhering to specification v2025-11-25. Exposes 5 canonical tools (`smart_entry_poll_events`, `smart_entry_trigger_scenario`, `bedrock_reason_triage`, `alexa_proactive_dispatch`, `household_action_execute`), resources (`ambient://household/context`), and prompts (`triage_incident`).
* **Canonical Streamable HTTP Transport**: Implemented official Streamable HTTP transport at `/mcp` with `Mcp-Session-Id` session management, bodyless notification handling (HTTP 202 Accepted), and DNS rebinding protections.
* **Cognitive Layer (AWS Builder Mini-Challenge)**: Integrated Amazon Bedrock Converse API with Claude 3.5 Sonnet using standard AWS credential provider chains, paired with an offline deterministic simulator for reliable, zero-cost verification.
* **Frontend Design**: Built according to the **Calm Mission Control** design system (paper canvas, forest ink, 1px structural borders, zero glassmorphism or neon blur, WCAG 2.1 AA compliant).
* **Security & Quality**: Enforced CSP, X-Frame-Options, X-Request-ID headers, CORS allowlists, safe DOM manipulation (zero untrusted `innerHTML`), and an automated 45-test test suite with **88% measured statement coverage** including Playwright E2E and Axe-core accessibility verification.

---

## Challenges We Ran Into
* **MCP Streamable HTTP Handshake & Notification Semantics**: The official MCP v2025-11-25 specification requires that notifications (e.g., `notifications/initialized`) receive a bodyless HTTP 202 response, while request responses may be framed via SSE `data: ` chunks or JSON. Handling this across browser `fetch()` and official Python client sessions required rigorous protocol engineering. We documented this extensively in our **Developer Friction Log** to provide actionable feedback for Amazon's SDK teams.
* **Calibrating Voice Interruptions**: Ensuring Bedrock only interrupts the resident when actionable intervention is required (e.g., incoming rain or medical inactivity), while logging benign events (like routine postal carriers) silently.

---

## Accomplishments We're Proud Of
* 100% adherence to official MCP standard v2025-11-25 using `mcp.server.mcpserver.MCPServer`.
* An explicit, unmistakable human approval boundary that prevents rogue AI actuation.
* 45 automated unit, integration, and browser E2E tests passing with **88% measured statement coverage**.
* Automated Axe-core audit confirming zero WCAG 2.1 AA accessibility violations.
* Comprehensive 4-entry Developer Friction Log in official 7-field format submitted for the +10% evaluation bonus.

---

## What We Learned
* How transformative the open Model Context Protocol is for ambient AI: instead of locking voice assistants into proprietary siloed skills, MCP allows ambient agents to orchestrate physical devices safely and composably.
* The critical importance of the operator-in-the-loop pattern in smart home automation.

---

## What's Next for AmbientOps
* Integration with physical smart home devices via OAuth2 device authorization.
* Direct skill deployment to the upcoming production Alexa+ Developer Portal.
* Expanding sensor presets with fine-grained radar dwell telemetry.

---

## Built With
* `Amazon Bedrock`
* `Claude 3.5 Sonnet`
* `Model Context Protocol (MCP v2025-11-25)`
* `FastAPI`
* `Python 3.11`
* `Streamable HTTP Transport`
* `Playwright & Axe-core`
* `Web Speech API`
* `Pytest (88% Statement Coverage)`
* `Docker`

# AmbientOps Technical Architecture & Specification

## 1. System Overview
**AmbientOps** is an ambient incident-response console designed for **Alexa+** and connected smart entry sensors, powered by **Amazon Bedrock** (Claude 3.5 Sonnet / AgentCore).

The primary operator sequence strictly enforces a **human approval boundary**:
```
Trigger Simulated Event 
  → Ingest & Normalize Evidence 
  → MCP Bedrock Triage 
  → Review Decision Rationale & Recommendation 
  → Explicit Human Operator Approval 
  → Execute Simulated Action 
  → Verify Observable Outcome
```

---

## 2. End-to-End Architectural Diagram

```mermaid
graph TD
    classDef sim fill:#fffbeb,stroke:#b45309,stroke-width:1px;
    classDef core fill:#ffffff,stroke:#0e1f18,stroke-width:2px;
    classDef gate fill:#fef2f2,stroke:#991b1b,stroke-width:2px;
    classDef ext fill:#eff6ff,stroke:#1e40af,stroke-width:1px;

    subgraph SIM_BOUNDARY ["Simulation Boundary (Local Device Fleet)"]
        D1["Doorbell Pro (Simulated)"]:::sim
        D2["Hallway Motion (Simulated)"]:::sim
        D3["Perimeter Cam (Simulated)"]:::sim
        SIM_BUS["Smart Entry Event Simulator<br/>(Deterministic Preset Bus)"]:::sim
        D1 --> SIM_BUS
        D2 --> SIM_BUS
        D3 --> SIM_BUS
    end

    subgraph TRUST_BOUNDARY ["AmbientOps Core Backend (FastAPI / Streamable HTTP)"]
        INGEST["FastAPI Ingestion & Normalizer<br/>(/api/events/trigger)"]:::core
        SIM_BUS -->|Event Webhook Payload| INGEST
        
        EVID["Structured Evidence Store<br/>(Bounding Boxes, Lux, Rain %, Audio dB)"]:::core
        INGEST --> EVID

        subgraph MCP_CORE ["Model Context Protocol (v2025-11-25)"]
            MCP_ENG["MCP Server Engine<br/>(Canonical /mcp Streamable HTTP)"]:::core
            T_POLL["Tool: smart_entry_poll_events"]:::core
            T_TRIAGE["Tool: bedrock_reason_triage"]:::core
            T_DISPATCH["Tool: alexa_proactive_dispatch"]:::core
            T_ACTION["Tool: household_action_execute"]:::core
            MCP_ENG --- T_POLL
            MCP_ENG --- T_TRIAGE
            MCP_ENG --- T_DISPATCH
            MCP_ENG --- T_ACTION
        end
        EVID -->|tools/call| T_TRIAGE
    end

    subgraph CLOUD_BOUNDARY ["External Services (AWS Cloud Boundary)"]
        BEDROCK["Amazon Bedrock (Converse API)<br/>Model: Claude 3.5 Sonnet"]:::ext
        EMULATOR["Deterministic Offline Simulator<br/>(Zero-credential fallback)"]:::ext
        T_TRIAGE -->|boto3 credential chain| BEDROCK
        T_TRIAGE -.->|offline / local mode| EMULATOR
    end

    subgraph OPERATOR_GATE ["Human Operator Gate (Trust Boundary)"]
        DECISION["Validated Structured Decision<br/>• Risk Index (0-100)<br/>• Confidence Score<br/>• Decision Rationale<br/>• Recommended Action"]:::core
        BEDROCK --> DECISION
        EMULATOR --> DECISION

        GATE{"Human Operator Approval Boundary<br/>(/api/operator/approve)"}:::gate
        DECISION -->|Status: PENDING_APPROVAL| GATE
    end

    subgraph OUTCOME_STAGE ["Action Execution & Outcome Verification"]
        DISPATCH_VOICE["Alexa Ambient Voice Dispatch<br/>(Simulated Browser Web Speech Synthesis)"]:::core
        EXEC_ACTION["Simulated Smart Hardware Actuator<br/>(Door Lock, Porch Bench, Spotlight)"]:::sim
        AUDIT["Incident Audit Ledger<br/>(Outcome Verified & Timestamps)"]:::core

        GATE -->|OPERATOR APPROVES| DISPATCH_VOICE
        GATE -->|OPERATOR APPROVES| EXEC_ACTION
        GATE -->|OPERATOR REJECTS| AUDIT
        DISPATCH_VOICE --> AUDIT
        EXEC_ACTION --> AUDIT
    end

    subgraph CLIENT_UI ["Calm Mission Control Interface"]
        UI_WORKSPACE["Web Workspace (HTML5 / Vanilla JS)<br/>• Dominant Evidence Canvas<br/>• Operator Approval Boundary Card<br/>• Live MCP Protocol Inspector"]:::core
        MCP_ENG <-->|Streamable HTTP /mcp| UI_WORKSPACE
        AUDIT --> UI_WORKSPACE
    end
```

---

## 3. Trust Boundaries & Security Architecture
1. **Simulation vs Production Boundary**: All smart entry cameras and motion detectors run in local simulated mode (`is_simulated = True`). No unverified third-party hardware commands are transmitted to external IoT networks.
2. **AWS Cloud Boundary**: Communication with Amazon Bedrock occurs over HTTPS via `boto3.client('bedrock-runtime').converse()`. If AWS credentials are not configured in the host environment, the system strictly isolates execution within the deterministic local simulator, guaranteeing zero unexpected cloud bills.
3. **Human Approval Boundary**: The application explicitly requires an operator confirmation step (`/api/operator/approve/{incident_id}`) before executing simulated remediations (such as unlocking smart locks or triggering floodlights). Automated escalation cannot bypass this boundary.
4. **Model Context Protocol Boundary**: All external tool execution from an Alexa+ client passes through strict Pydantic input schemas and JSON-RPC 2.0 error validation (-32600, -32601, -32602, -32603).

# AmbientOps Architecture & Technical Specification

## System Overview
**AmbientOps** is an autonomous multi-device Model Context Protocol (MCP) agent designed for **Alexa+** and **Ring**, powered by **Amazon Bedrock** (Claude 3.5 Sonnet / AgentCore).

It continuously observes environmental sensor events and computer vision detections from Ring cameras, performs cognitive risk triage through Amazon Bedrock, and autonomously dispatches proactive vocal notifications to Alexa+ endpoints while executing connected home remediations.

---

## Architectural Diagram

```mermaid
graph TD
    subgraph "1. Physical / Simulated Smart Home Devices"
        R1["Ring Porch Doorbell Pro<br/>(Camera & Rain Sensor)"] -->|Event Webhook / Telemetry| BUS["Ring Event Bus / Playground"]
        R2["Ring Hallway Cam<br/>(Motion & Inactivity)"] -->|CV Detections| BUS
        R3["Ring Backyard Floodlight<br/>(Perimeter Sensors)"] -->|Gate & Pet Detection| BUS
        R4["Ring Driveway Spotlight<br/>(Infrared & Noise)"] -->|Night Movement| BUS
    end

    subgraph "2. AmbientOps Core Server (FastAPI / SSE)"
        BUS -->|Simulated Trigger| SERVER["FastAPI Backend Server"]
        
        subgraph "Model Context Protocol (MCP v2025-11-25)"
            MCP_S["MCP Server Engine"]
            TOOLS["MCP Tools:<br/>• ring_poll_events<br/>• ring_trigger_scenario<br/>• bedrock_reason_triage<br/>• alexa_proactive_dispatch<br/>• household_action_execute"]
            RES["MCP Resources:<br/>• ambient://devices/ring/live<br/>• ambient://household/context<br/>• ambient://telemetry/mcp"]
            PROMPTS["MCP Prompts:<br/>• triage_incident<br/>• daily_ambient_brief"]
        end
        
        SERVER <--> MCP_S
    end

    subgraph "3. Cognitive Engine (AWS Builder Challenge)"
        MCP_S -->|JSON-RPC tools/call| BEDROCK["Amazon Bedrock<br/>(Claude 3.5 Sonnet Converse API)"]
        BEDROCK -->|Risk Index 0-100<br/>Severity & Chain-of-Thought<br/>Spoken Prompt Synthesis| MCP_S
    end

    subgraph "4. Ambient Action & Voice Actuators"
        MCP_S -->|alexa_proactive_dispatch| ALEXA["Alexa+ Voice Endpoint<br/>(Spoken Ambient Dialogue)"]
        MCP_S -->|household_action_execute| HOME["Smart Home Actuators<br/>(Smart Locks, Floodlights, Chimes)"]
    end

    subgraph "5. Interactive Real-Time Dashboard"
        SERVER -->|Streamable HTTP SSE| UI["Web UI Control Center<br/>• Ring Camera Stage & Bounding Boxes<br/>• Alexa+ Waveform Visualizer & Speech<br/>• Live MCP Protocol Inspector"]
    end
```

---

## MCP Tool Schemas

### 1. `ring_poll_events`
* **Description**: Queries recent motion, doorbell press, and linger events from connected Ring devices.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "limit": { "type": "integer", "description": "Max events to retrieve (default: 5)" }
    }
  }
  ```

### 2. `bedrock_reason_triage`
* **Description**: Evaluates an event using Amazon Bedrock to calculate risk scores and formulate conversational speech.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "event_id": { "type": "string", "description": "Ring event unique identifier" }
    },
    "required": ["event_id"]
  }
  ```

### 3. `alexa_proactive_dispatch`
* **Description**: Dispatches synthesized voice audio or notification chime to a target Alexa+ endpoint.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "spoken_text": { "type": "string" },
      "urgency": { "type": "string", "enum": ["low", "moderate", "critical"] },
      "target_room": { "type": "string" }
    },
    "required": ["spoken_text", "urgency"]
  }
  ```

### 4. `household_action_execute`
* **Description**: Executes connected smart home hardware automations.
* **Input Schema**:
  ```json
  {
    "type": "object",
    "properties": {
      "action_name": { "type": "string" },
      "parameters": { "type": "object" }
    },
    "required": ["action_name"]
  }
  ```

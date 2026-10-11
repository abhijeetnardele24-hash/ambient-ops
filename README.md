# AmbientOps 🌐
### Autonomous Multi-Device MCP Agent for Alexa+ & Ring powered by Amazon Bedrock

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![MCP Spec](https://img.shields.io/badge/MCP%20Spec-2025--11--25-blueviolet.svg)](https://modelcontextprotocol.io/)
[![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock%20Claude%203.5-ff9900.svg)](https://aws.amazon.com/bedrock/)
[![Tests](https://img.shields.io/badge/tests-18%2F18%20passing-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Built for **Build, Ship, Shape: Amazon Developer Hackathon 2026**  
> Tracks: **Alexa+ (MCP & Agent Skills)** • **Ring Appstore & Vision** • **AWS Builder Mini-Challenge**  
> Includes the official **+10% Bonus Developer Friction Log** (`docs/FRICTION_LOG.md`).

---

## 📸 Product Overview & Live Demo

![AmbientOps Control Center](assets/screenshots/overview.png)

### 🎥 Interactive Video Walkthrough
An interactive video recording demonstrating real-time scenario triggering, Alexa+ audio speech synthesis, and live MCP protocol inspection is available in [assets/demo/ambient_ops_walkthrough.webp](assets/demo/ambient_ops_walkthrough.webp).

---

## 🖼️ Feature Gallery

| Ring Vision Bounding Boxes & Immobility Alert | Night Anomaly & Autonomous Smart Lights |
| :---: | :---: |
| ![Care Immobility Alert](assets/screenshots/care_immobility.png) | ![Night Loitering Anomaly](assets/screenshots/night_loitering.png) |

| Live MCP Protocol Inspector & Tool Runner | Official Developer Friction Log (+10% Bonus) |
| :---: | :---: |
| ![MCP Protocol Inspector](assets/screenshots/mcp_tool_execution.png) | ![Friction Log Modal](assets/screenshots/friction_log_modal.png) |


---

## ⚡ What is AmbientOps?
**AmbientOps** is a next-generation ambient operations copilot that eliminates smart home notification fatigue. Rather than blasting mobile devices with raw push alerts whenever a sensor trips, AmbientOps connects **Ring** computer vision feeds with **Amazon Bedrock (Claude 3.5 Sonnet)** through the open **Model Context Protocol (MCP)**. 

When a critical or actionable event occurs—such as a package left in incoming rain, an elderly resident remaining motionless past medical reminder times, or a pet escaping through an unlatched gate—AmbientOps reasons across environmental context and dispatches natural, proactive spoken dialogues directly to **Alexa+** ambient endpoints while autonomously executing smart home remedies.

---

## 🏛️ System Architecture

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

## 🧰 Model Context Protocol (MCP) Capabilities

Conforming strictly to **MCP v2025-11-25**, AmbientOps provides standard tools, resources, and prompt templates:

### 1. Registered MCP Tools
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `ring_poll_events` | `limit: int` | Polls recent motion, door press, and linger events from Ring cameras. |
| `ring_trigger_scenario` | `scenario_id: string` | Triggers a simulated scenario in the Ring Playground. |
| `bedrock_reason_triage` | `event_id: string` | Invokes Amazon Bedrock Converse API for cognitive risk assessment. |
| `alexa_proactive_dispatch` | `spoken_text, urgency, target_room` | Dispatches vocal speech or chime to the Alexa+ ambient audio layer. |
| `household_action_execute` | `action_name, parameters` | Executes physical hardware actions (locks, lights, sirens). |

### 2. Registered MCP Resources
* `ambient://devices/ring/live`: Real-time telemetry, signal RSSI, and battery levels for the Ring camera fleet.
* `ambient://household/context`: Resident profiles, quiet-hour schedules, and emergency contacts.
* `ambient://telemetry/mcp`: Real-time MCP message counters, latencies, and active transports.

---

## 🚀 Quickstart Guide

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/abhijeetnardele24-hash/ambient-ops.git
cd ambient-ops

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment (Optional for Live AWS Bedrock)
```bash
cp .env.example .env
```
*Note: By default, `USE_BEDROCK_MOCK=true` allows full offline evaluation without AWS API keys or cloud bills.*

### 3. Launch the Application
```bash
uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload
```
Open your browser at **`http://localhost:8000`** to interact with the full three-panel control center!

---

## 🧪 Automated Test Suite

Run the full automated test suite verifying MCP protocol compliance, Bedrock triage, Ring simulator logic, and end-to-end API workflows:

```bash
pytest tests/ -v
```

**Results**: 18 passing tests with 100% pass rate.

---

## 🐳 Docker Deployment

Run with Docker in a single command:

```bash
docker-compose up --build
```
Access the application at `http://localhost:8000`.

---

## 📄 Hackathon Deliverables & Documents
* 📘 [Technical Architecture](docs/ARCHITECTURE.md)
* 📝 [Official Developer Friction Log (+10% Bonus)](docs/FRICTION_LOG.md)
* 🏆 [Devpost Submission Package](docs/DEVPOST_SUBMISSION.md)

---

## 📜 License
This project is open-source under the [MIT License](LICENSE).

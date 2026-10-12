# AmbientOps: 3-Minute Video Demo Script & Shot List

**Target Duration**: 2 minutes 45 seconds (Strictly under 3:00 Devpost competition limit)  
**Hackathon**: *Build, Ship, Shape: Amazon Developer Hackathon 2026*  
**Presenter**: AmbientOps Presenter  

---

## 📹 Mandatory Video Submission Guidelines
Before recording and submitting the demo video, ensure compliance with the official contest rules:
1. **Duration**: Must be strictly **under 3 minutes** (the shot list below is calibrated for 2:45).
2. **Language**: Spoken audio and on-screen text must be in **English**.
3. **Platform**: Uploaded publicly to **YouTube** or **Vimeo** (unlisted or public; private videos cannot be evaluated by judges).
4. **Music & Footage**: Zero copyrighted background music, sound effects, or unlicensed third-party stock footage. Use clear presenter voiceover and UI audio.
5. **Required Demonstrations**:
   - Visibly show the working MCP protocol lifecycle in the right rail inspector: `initialize`, `tools/list`, and `tools/call`.
   - Visibly show the header provider badge: whether Bedrock is in **LIVE** (`bedrock-live`) or **SIMULATED** (`bedrock-simulator`) mode.
   - **CRITICAL**: The presenter **must use the exact narration line matching the visible badge**. Never claim an event was evaluated by live Bedrock if the badge displays simulator mode.

---

## 🛠️ Optional Live Bedrock Pre-Flight Verification
If you have configured AWS credentials and wish to demonstrate live Bedrock Converse API triage during recording:
```bash
# PowerShell
$env:ENABLE_LIVE_BEDROCK="true"
$env:FORCE_BEDROCK_SIMULATOR="false"
python scripts/verify_live_bedrock.py

# Bash (Linux/macOS)
export ENABLE_LIVE_BEDROCK=true
export FORCE_BEDROCK_SIMULATOR=false
python scripts/verify_live_bedrock.py
```
*Note: If live AWS credentials or Bedrock model access are unavailable, keep the default deterministic simulator mode and use the offline simulation narration below. Do not fabricate live evidence.*

---

## 🎬 Shot List & Execution Sequence

| Timestamp | Shot / UI Focus | Exact Operator Action | Visual Screen State | Spoken Voiceover Narration |
| :--- | :--- | :--- | :--- | :--- |
| **0:00 – 0:25** | Wide view: Calm Mission Control Header & 3-Panel Layout | Cursor hovers over header mode badges (`SIMULATED`, `CONNECTED`, and Bedrock provider badge). | Clean off-white paper canvas with forest ink typography. System indicates active canonical MCP Streamable HTTP transport and connected simulated sensor fleet. | *"Hi everyone, this is AmbientOps. In modern smart homes, cameras blast phones with noisy notifications, but they lack ambient situational intelligence. With Amazon opening the Model Context Protocol for Alexa+, AmbientOps bridges smart camera vision with Amazon Bedrock reasoning and an explicit human operator approval boundary."* |
| **0:25 – 1:00** | Scenario 1: Package in Incoming Rain | Click left rail preset **"Package in Rain"**. | Camera viewport renders door steps with bounding boxes (`package_box 96%`, `delivery_person 91%`). Precipitation telemetry reads 92%. | **[Select line matching visible header badge]**<br><br>**If visible badge is LIVE (`bedrock-live`):**<br>*"Let's observe our first incident. A delivery courier drops off a package on exposed front steps, but local weather sensors detect incoming rain in 15 minutes. The evidence is ingested into our MCP server and evaluated live via Amazon Bedrock Converse API with Claude 3.5 Sonnet."*<br><br>**If visible badge is SIMULATED (`bedrock-simulator`):**<br>*"Let's observe our first incident. A delivery courier drops off a package on exposed front steps, but local weather sensors detect incoming rain in 15 minutes. The evidence is ingested into our MCP server and evaluated through our deterministic offline Bedrock simulator, demonstrating identical cognitive schemas without requiring live AWS cloud credentials."* |
| **1:00 – 1:30** | Human Approval Boundary & Decision Rationale | Highlight Decision Rationale block. Click **"Approve Simulation &rarr;"**. | Decision rationale displays risk score 68/100, confidence 96%, and recommended action `unlock_porch_storage`. Upon clicking Approve, badge turns green: `✓ SIMULATION APPROVED`. Outcome verified block displays. | *"Notice our human approval boundary: the agent never performs autonomous physical actions without operator confirmation. Bedrock formulates the decision rationale and recommends unlocking the porch bench. As the operator, I approve the simulation—actions execute, and the outcome is verified in the audit ledger."* |
| **1:30 – 1:50** | Alexa Ambient Spoken Dialogue Simulation | Click **"Replay Voice"** button in Alexa Voice Box. | Spoken transcript displays conversational prompt. Browser Web Speech API (`window.speechSynthesis`) outputs simulated audio: *"Excuse me, your front porch camera observed a package delivery..."* | *"Simultaneously, the system synthesizes a natural proactive ambient voice alert simulated via browser Web Speech audio output, demonstrating how an ambient Alexa device alerts the resident before their package gets soaked—without claiming physical Echo hardware."* |
| **1:50 – 2:20** | Scenario 2: Care Recipient Inactivity Alert | Click left rail preset **"Care Inactivity (52m Dwell)"**. | Viewport updates to hallway camera. Bounding box shows `person_stationary 94%`. Risk score jumps to 94/100 (CRITICAL). | **[Select line matching visible header badge]**<br><br>**If visible badge is LIVE (`bedrock-live`):**<br>*"Now let's test a non-security caretaking use case. An elderly family member remains stationary on the floor for 52 minutes while their scheduled medication is overdue. Amazon Bedrock evaluates the multimodal scene in real time, scoring a critical wellness risk and formulating an empathetic check-in dialogue."*<br><br>**If visible badge is SIMULATED (`bedrock-simulator`):**<br>*"Now let's test a non-security caretaking use case. An elderly family member remains stationary on the floor for 52 minutes while their scheduled medication is overdue. Our offline Bedrock simulator evaluates the multimodal scene deterministically, scoring a critical wellness risk and formulating an empathetic check-in dialogue."* |
| **2:20 – 2:35** | Live MCP Protocol Inspector | Scroll down right rail inspector. Click **"Call Tool (JSON-RPC)"**. | Inspector displays real-time JSON-RPC 2.0 messages: `initialize`, `tools/list`, and `tools/call`. Tool executes and appends output. | *"On the right rail, our live MCP Inspector exposes the underlying Streamable HTTP JSON-RPC 2.0 stream adhering to the MCP 2025-11-25 standard, allowing any Alexa+ client to discover and execute tools securely."* |
| **2:35 – 2:45** | Developer Friction Log Modal & Wrap-up | Click **"Friction Log (+10% Bonus)"** button. Press Escape key to close. | Modal opens displaying the 4-pillar architectural feedback report for Amazon SDK engineers. Closes cleanly via keyboard. | *"Finally, we compiled a comprehensive Developer Friction Log evaluating the Alexa+ MCP developer experience. AmbientOps represents the future of ambient, operator-in-the-loop home intelligence. Thank you!"* |


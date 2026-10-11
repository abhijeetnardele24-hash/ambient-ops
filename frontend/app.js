/**
 * AmbientOps — Calm Mission Control Client Application.
 * Secure, zero-innerHTML-injection DOM manipulation.
 * Implements Operator Sequence: Trigger -> Observe Evidence -> Analyze -> Review -> Approve Simulation.
 */

let activeIncidentId = null;
let currentEvent = null;
let activeModalTrigger = null;
let rawMcpEntries = [];

document.addEventListener('DOMContentLoaded', () => {
  initLiveClock();
  initDeviceFleet();
  initMcpSseTransport();
  loadMcpHistory();
  initModalAccessibility();

  // Load initial preset
  selectScenario('delivery_weather_risk');

  // Auto-refresh MCP logs every 3 seconds
  setInterval(loadMcpHistory, 3000);
});

// --- Live Clock ---
function initLiveClock() {
  const clockEl = document.getElementById('liveTimestamp');
  setInterval(() => {
    if (clockEl) {
      const now = new Date();
      clockEl.textContent = now.toLocaleTimeString();
    }
  }, 1000);
}

// --- Device Catalog (Secure DOM Building) ---
async function initDeviceFleet() {
  const catalogList = document.getElementById('deviceCatalogList');
  if (!catalogList) return;

  try {
    const res = await fetch('/api/devices');
    const devices = await res.json();

    catalogList.textContent = ''; // clear

    devices.forEach(d => {
      const row = document.createElement('div');
      row.className = 'device-row';

      const infoDiv = document.createElement('div');
      const nameSpan = document.createElement('strong');
      nameSpan.textContent = d.name;
      const metaSpan = document.createElement('span');
      metaSpan.className = 'device-meta';
      metaSpan.style.display = 'block';
      metaSpan.textContent = `${d.device_id} • ${d.battery}`;
      infoDiv.appendChild(nameSpan);
      infoDiv.appendChild(metaSpan);

      const statusSpan = document.createElement('span');
      statusSpan.className = 'device-meta';
      statusSpan.style.color = 'var(--status-success-text)';
      statusSpan.textContent = `● ${d.mode || 'SIMULATED'}`;

      row.appendChild(infoDiv);
      row.appendChild(statusSpan);
      catalogList.appendChild(row);
    });
  } catch (err) {
    console.warn('Failed to load device catalog:', err);
  }
}

// --- MCP SSE Transport ---
function initMcpSseTransport() {
  const badge = document.getElementById('transportBadge');
  if (!window.EventSource) {
    if (badge) badge.textContent = '● MCP: HTTP FALLBACK';
    return;
  }

  const evtSource = new EventSource('/mcp/sse');
  evtSource.addEventListener('endpoint', () => {
    if (badge) badge.textContent = '● MCP SSE: CONNECTED';
  });

  evtSource.onerror = () => {
    if (badge) badge.textContent = '▲ MCP: RECONNECTING';
  };
}

// --- Scenario Selection & Operator Flow ---
async function selectScenario(scenarioId) {
  // Update UI active buttons
  document.querySelectorAll('.scenario-card-btn').forEach(btn => {
    const isTarget = btn.id === `btn-${scenarioId}`;
    btn.classList.toggle('active', isTarget);
  });

  const outcomeBlock = document.getElementById('verifiedOutcomeBlock');
  if (outcomeBlock) outcomeBlock.style.display = 'none';

  const approvalBadge = document.getElementById('approvalStatusBadge');
  if (approvalBadge) {
    approvalBadge.className = 'gate-badge pending';
    approvalBadge.textContent = 'ANALYZING INCIDENT EVIDENCE...';
  }

  try {
    // 1. Trigger Scenario
    const triggerRes = await fetch(`/api/events/trigger/${scenarioId}`, { method: 'POST' });
    const triggerData = await triggerRes.json();
    currentEvent = triggerData.event;

    // Render Evidence
    renderVisualEvidence(currentEvent);

    // 2. Analyze via MCP Bedrock Tool
    const analyzeRes = await fetch(`/api/agent/analyze/${currentEvent.event_id}`, { method: 'POST' });
    const analyzeData = await analyzeRes.json();

    activeIncidentId = analyzeData.incident_id;
    const incident = analyzeData.incident;

    renderIncidentDecision(incident.triage_decision);

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge pending';
      approvalBadge.textContent = 'AWAITING OPERATOR APPROVAL';
    }

    const btnApprove = document.getElementById('btnApprove');
    const btnReject = document.getElementById('btnReject');
    if (btnApprove) btnApprove.disabled = false;
    if (btnReject) btnReject.disabled = false;

  } catch (err) {
    console.error('Error during scenario pipeline:', err);
    if (approvalBadge) {
      approvalBadge.className = 'gate-badge rejected';
      approvalBadge.textContent = 'ANALYSIS PIPELINE ERROR';
    }
  } finally {
    loadMcpHistory();
  }
}

// --- Render Visual Evidence (Safe SVG Nodes) ---
function renderVisualEvidence(event) {
  const cameraLabel = document.getElementById('cameraNameLabel');
  if (cameraLabel) cameraLabel.textContent = event.device_name;

  const rainEl = document.getElementById('telemetryPrecipitation');
  const luxEl = document.getElementById('telemetryLux');
  const confEl = document.getElementById('telemetryConfidence');

  if (rainEl) rainEl.textContent = event.ambient_conditions.rain_probability ? `${Math.round(event.ambient_conditions.rain_probability * 100)}%` : 'N/A';
  if (luxEl) luxEl.textContent = event.ambient_conditions.ambient_lux ? `${event.ambient_conditions.ambient_lux} lx` : '40 lx';
  if (confEl && event.detections.length > 0) {
    confEl.textContent = event.detections[0].confidence.toFixed(2);
  }

  // Render SVG Bounding Boxes using secure DOM methods
  const svgGroup = document.getElementById('svgBoundingBoxes');
  if (!svgGroup) return;

  svgGroup.textContent = ''; // clear

  const w = 640;
  const h = 360;

  (event.detections || []).forEach(d => {
    const [ymin, xmin, ymax, xmax] = d.box_normalized;
    const boxX = xmin * w;
    const boxY = ymin * h;
    const boxW = (xmax - xmin) * w;
    const boxH = (ymax - ymin) * h;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');

    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', boxX);
    rect.setAttribute('y', boxY);
    rect.setAttribute('width', boxW);
    rect.setAttribute('height', boxH);
    rect.setAttribute('fill', 'rgba(45, 106, 79, 0.15)');
    rect.setAttribute('stroke', '#2d6a4f');
    rect.setAttribute('stroke-width', '2');
    rect.setAttribute('stroke-dasharray', '4 2');

    const labelBg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    const labelWidth = Math.max(80, d.label.length * 8 + 30);
    labelBg.setAttribute('x', boxX);
    labelBg.setAttribute('y', Math.max(0, boxY - 18));
    labelBg.setAttribute('width', labelWidth);
    labelBg.setAttribute('height', '18');
    labelBg.setAttribute('fill', '#0e1f18');
    labelBg.setAttribute('rx', '2');

    const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    labelText.setAttribute('x', boxX + 4);
    labelText.setAttribute('y', Math.max(12, boxY - 5));
    labelText.setAttribute('fill', '#ffffff');
    labelText.setAttribute('font-size', '10');
    labelText.setAttribute('font-family', "'JetBrains Mono', monospace");
    labelText.setAttribute('font-weight', '600');
    labelText.textContent = `${d.label} ${(d.confidence * 100).toFixed(0)}%`;

    g.appendChild(rect);
    g.appendChild(labelBg);
    g.appendChild(labelText);
    svgGroup.appendChild(g);
  });
}

// --- Render Decision Rationale & Recommendation ---
function renderIncidentDecision(decision) {
  const rationaleEl = document.getElementById('decisionRationaleText');
  const riskEl = document.getElementById('riskIndexVal');
  const confEl = document.getElementById('confidenceVal');
  const sevEl = document.getElementById('severityText');
  const actionEl = document.getElementById('recommendedActionText');
  const promptEl = document.getElementById('spokenTranscriptText');
  const providerBadge = document.getElementById('providerBadge');

  if (rationaleEl) rationaleEl.textContent = decision.decision_rationale;
  if (riskEl) riskEl.textContent = `${decision.risk_score} / 100`;
  if (confEl) confEl.textContent = `${Math.round(decision.confidence_score * 100)}%`;
  if (sevEl) sevEl.textContent = decision.severity.toUpperCase();
  if (actionEl) actionEl.textContent = `${decision.recommended_action} • ${decision.suggested_actions.join(', ')}`;
  if (promptEl) promptEl.textContent = `"${decision.spoken_alexa_prompt}"`;

  if (providerBadge) {
    if (decision.provider_mode === 'bedrock-live') {
      providerBadge.className = 'mode-badge live';
      providerBadge.textContent = '■ AWS BEDROCK: LIVE';
    } else {
      providerBadge.className = 'mode-badge mock';
      providerBadge.textContent = '■ ENGINE: DETERMINISTIC SIMULATOR';
    }
  }
}

// --- Operator Human Approval Actions ---
async function approveCurrentIncident() {
  if (!activeIncidentId) return;

  const btnApprove = document.getElementById('btnApprove');
  const btnReject = document.getElementById('btnReject');
  const approvalBadge = document.getElementById('approvalStatusBadge');
  const outcomeBlock = document.getElementById('verifiedOutcomeBlock');

  if (btnApprove) btnApprove.disabled = true;
  if (btnReject) btnReject.disabled = true;

  try {
    const res = await fetch(`/api/operator/approve/${activeIncidentId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ operator_notes: 'Approved from Calm Mission Control console' }),
    });
    const data = await res.json();

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge approved';
      approvalBadge.textContent = '✓ SIMULATION APPROVED';
    }

    if (outcomeBlock) {
      outcomeBlock.style.display = 'block';
      const small = outcomeBlock.querySelector('small');
      if (small) {
        small.textContent = `✓ SIMULATED OUTCOME VERIFIED: Remediations [${data.incident.executed_actions.join(', ')}] executed and logged.`;
      }
    }

    // Play vocal prompt
    const decision = data.incident.triage_decision;
    if (decision && decision.should_interrupt_user) {
      speakVocalPrompt(decision.spoken_alexa_prompt);
    }
  } catch (err) {
    console.error('Failed to approve incident:', err);
  } finally {
    loadMcpHistory();
  }
}

async function rejectCurrentIncident() {
  if (!activeIncidentId) return;

  const btnApprove = document.getElementById('btnApprove');
  const btnReject = document.getElementById('btnReject');
  const approvalBadge = document.getElementById('approvalStatusBadge');

  if (btnApprove) btnApprove.disabled = true;
  if (btnReject) btnReject.disabled = true;

  try {
    await fetch(`/api/operator/reject/${activeIncidentId}`, { method: 'POST' });

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge rejected';
      approvalBadge.textContent = '✗ DISMISSED BY OPERATOR';
    }
  } catch (err) {
    console.error('Failed to reject incident:', err);
  } finally {
    loadMcpHistory();
  }
}

// --- Web Speech API Synthesis ---
function speakCurrentTranscript() {
  const textEl = document.getElementById('spokenTranscriptText');
  if (textEl) {
    const cleanText = textEl.textContent.replace(/"/g, '');
    speakVocalPrompt(cleanText);
  }
}

function speakVocalPrompt(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  const voices = window.speechSynthesis.getVoices();
  const natural = voices.find(v => v.name.includes('Natural') || v.name.includes('Google') || v.lang.startsWith('en'));
  if (natural) utterance.voice = natural;

  window.speechSynthesis.speak(utterance);
}

// --- Live MCP Log Inspector (Safe DOM Nodes) ---
async function loadMcpHistory() {
  try {
    const res = await fetch('/api/mcp/history');
    const logs = await res.json();
    rawMcpEntries = logs;
    renderMcpLogs();
  } catch (err) {
    console.warn('Failed to load MCP history:', err);
  }
}

function renderMcpLogs() {
  const container = document.getElementById('mcpLogFeed');
  const countEl = document.getElementById('mcpMsgCount');
  if (countEl) countEl.textContent = rawMcpEntries.length;
  if (!container) return;

  container.textContent = ''; // clear

  rawMcpEntries.slice(0, 30).forEach(entry => {
    const item = document.createElement('div');
    item.className = 'mcp-entry-item';

    const header = document.createElement('div');
    header.className = 'mcp-entry-header';

    const dirTag = document.createElement('span');
    const dir = entry.direction || 'internal';
    dirTag.className = `mcp-dir-tag ${dir.replace('_', '')}`;
    dirTag.textContent = dir.toUpperCase();

    const timeSpan = document.createElement('span');
    const t = new Date(entry.timestamp * 1000).toLocaleTimeString();
    timeSpan.textContent = `${t} ${entry.latency_ms ? `(${entry.latency_ms}ms)` : ''}`;

    header.appendChild(dirTag);
    header.appendChild(timeSpan);

    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.textContent = JSON.stringify(entry.payload, null, 2);
    pre.className = 'mcp-code-view';
    pre.appendChild(code);

    item.appendChild(header);
    item.appendChild(pre);
    container.appendChild(item);
  });
}

function clearMcpDisplay() {
  rawMcpEntries = [];
  renderMcpLogs();
}

// --- Interactive Judge Tool Executor ---
function updateToolArgPlaceholder() {
  const select = document.getElementById('judgeToolSelect');
  const input = document.getElementById('judgeToolArgs');
  if (!select || !input) return;

  const defaults = {
    smart_entry_poll_events: '{"limit": 3}',
    smart_entry_trigger_scenario: '{"scenario_id": "pet_escape_risk"}',
    bedrock_reason_triage: '{"event_id": "latest"}',
    alexa_proactive_dispatch: '{"spoken_text": "Perimeter alert verified.", "urgency": "low"}',
    household_action_execute: '{"action_name": "latch_gate_lock"}',
  };
  input.placeholder = defaults[select.value] || '{}';
}

async function executeSelectedTool() {
  const select = document.getElementById('judgeToolSelect');
  const input = document.getElementById('judgeToolArgs');
  if (!select || !input) return;

  let args = {};
  const raw = input.value.trim() || input.placeholder;
  try {
    args = JSON.parse(raw);
  } catch (e) {
    alert('Please enter valid JSON parameters.');
    return;
  }

  const payload = {
    jsonrpc: '2.0',
    id: `judge-${Date.now()}`,
    method: 'tools/call',
    params: {
      name: select.value,
      arguments: args,
    },
  };

  try {
    await fetch('/mcp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    loadMcpHistory();
  } catch (err) {
    console.error('Judge tool call failed:', err);
  }
}

// --- Accessible Modal (Escape, Focus Trap, Return Focus) ---
function initModalAccessibility() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = document.getElementById('frictionModal');
      if (modal && modal.classList.contains('open')) {
        closeFrictionModal();
      }
    }
  });
}

async function openFrictionModal() {
  activeModalTrigger = document.activeElement;
  const modal = document.getElementById('frictionModal');
  const content = document.getElementById('frictionContentArea');
  if (!modal) return;

  modal.classList.add('open');
  modal.focus();

  try {
    const res = await fetch('/api/friction-log');
    const data = await res.json();
    if (content) {
      content.textContent = ''; // clear

      // Render markdown safely using text content blocks
      const lines = data.content.split('\n');
      let inCodeBlock = false;
      let codeBuffer = [];

      lines.forEach(line => {
        if (line.startsWith('```')) {
          if (inCodeBlock) {
            const pre = document.createElement('pre');
            pre.textContent = codeBuffer.join('\n');
            content.appendChild(pre);
            codeBuffer = [];
            inCodeBlock = false;
          } else {
            inCodeBlock = true;
          }
          return;
        }

        if (inCodeBlock) {
          codeBuffer.push(line);
          return;
        }

        if (line.startsWith('# ')) {
          const h1 = document.createElement('h1');
          h1.textContent = line.slice(2);
          content.appendChild(h1);
        } else if (line.startsWith('## ')) {
          const h2 = document.createElement('h2');
          h2.textContent = line.slice(3);
          h2.style.marginTop = '16px';
          content.appendChild(h2);
        } else if (line.startsWith('### ')) {
          const h3 = document.createElement('h3');
          h3.textContent = line.slice(4);
          h3.style.marginTop = '12px';
          content.appendChild(h3);
        } else if (line.startsWith('* ') || line.startsWith('- ')) {
          const li = document.createElement('li');
          li.textContent = line.slice(2);
          content.appendChild(li);
        } else if (line.trim().length > 0) {
          const p = document.createElement('p');
          p.textContent = line;
          content.appendChild(p);
        }
      });
    }
  } catch (err) {
    if (content) content.textContent = 'Failed to load friction log.';
  }
}

function closeFrictionModal() {
  const modal = document.getElementById('frictionModal');
  if (modal) modal.classList.remove('open');
  if (activeModalTrigger && typeof activeModalTrigger.focus === 'function') {
    activeModalTrigger.focus();
  }
}

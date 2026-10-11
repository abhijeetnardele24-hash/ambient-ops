/**
 * AmbientOps Frontend Logic & MCP Event Orchestrator.
 * Connects Ring Vision Simulator, Alexa+ Voice Synthesis, and Bedrock Triage.
 */

let speechEnabled = true;
let currentScenario = 'delivery_weather_risk';
let mcpFilter = 'all';
let rawMcpHistory = [];

document.addEventListener('DOMContentLoaded', () => {
  initLiveClock();
  initRingDevices();
  initMcpSseTransport();
  loadMcpHistory();
  // Trigger initial default scenario to populate UI
  triggerScenario('delivery_weather_risk', false);
  // Auto-refresh MCP log every 3 seconds
  setInterval(loadMcpHistory, 3000);
});

// --- Live Clock ---
function initLiveClock() {
  const clockEl = document.getElementById('liveTimestamp');
  setInterval(() => {
    const now = new Date();
    if (clockEl) {
      clockEl.textContent = now.toLocaleTimeString();
    }
  }, 1000);
}

// --- Ring Device Catalog ---
async function initRingDevices() {
  try {
    const res = await fetch('/api/ring/devices');
    const devices = await res.json();
    const listEl = document.getElementById('fleetList');
    const countEl = document.getElementById('deviceCount');
    if (countEl) countEl.textContent = `${devices.length} Devices Online`;

    if (listEl) {
      listEl.innerHTML = devices.map(d => `
        <div class="fleet-item">
          <div>
            <span class="fleet-name">${d.name}</span>
            <small style="display:block; color: #64748b;">${d.device_id} • ${d.battery}</small>
          </div>
          <span class="fleet-status-tag">● ${d.status.toUpperCase()}</span>
        </div>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load Ring devices:', err);
  }
}

// --- SSE MCP Transport ---
function initMcpSseTransport() {
  const statusEl = document.getElementById('transportStatus');
  if (!window.EventSource) {
    if (statusEl) statusEl.textContent = 'HTTP Fallback';
    return;
  }

  const evtSource = new EventSource('/mcp/sse');
  evtSource.addEventListener('endpoint', (e) => {
    if (statusEl) statusEl.textContent = 'Streamable SSE (Live)';
  });

  evtSource.addEventListener('ping', (e) => {
    // Keepalive ping received
  });

  evtSource.onerror = () => {
    if (statusEl) statusEl.textContent = 'SSE Reconnecting...';
  };
}

// --- Trigger Scenario (End-to-End Triage) ---
async function triggerScenario(scenarioId, shouldSpeak = true) {
  currentScenario = scenarioId;

  // Highlight active button
  document.querySelectorAll('.btn-scenario').forEach(btn => {
    const isThis = btn.getAttribute('onclick')?.includes(scenarioId);
    btn.classList.toggle('active', !!isThis);
  });

  // UI state: Loading
  const orbStatus = document.getElementById('orbStatus');
  const waveform = document.getElementById('waveform');
  if (orbStatus) orbStatus.textContent = 'Reasoning via Amazon Bedrock...';
  if (waveform) waveform.classList.add('active');

  try {
    const res = await fetch(`/api/agent/triage/${scenarioId}`, { method: 'POST' });
    const data = await res.json();

    if (data.status === 'success') {
      renderEventToUi(data.event, data.decision, data.executed_actions);
      if (shouldSpeak && speechEnabled && data.decision.should_interrupt_user) {
        speakText(data.decision.spoken_alexa_prompt);
      }
    }
  } catch (err) {
    console.error('Triage execution failed:', err);
  } finally {
    if (waveform && !window.speechSynthesis?.speaking) {
      setTimeout(() => waveform.classList.remove('active'), 1200);
    }
    loadMcpHistory();
  }
}

// --- Render Event to Viewport & Console ---
function renderEventToUi(event, decision, actions) {
  // Update Camera Viewport
  const camName = document.getElementById('currentCameraName');
  if (camName) camName.textContent = event.device_name;

  const rainEl = document.getElementById('telemetryRain');
  const luxEl = document.getElementById('telemetryLux');
  const confEl = document.getElementById('telemetryConfidence');

  if (rainEl) rainEl.textContent = event.ambient_conditions.rain_probability ? `${Math.round(event.ambient_conditions.rain_probability * 100)}%` : 'N/A';
  if (luxEl) luxEl.textContent = event.ambient_conditions.ambient_lux ? `${event.ambient_conditions.ambient_lux} lx` : '50 lx';
  if (confEl && event.detections.length > 0) {
    confEl.textContent = event.detections[0].confidence.toFixed(2);
  }

  // Render SVG Bounding Boxes
  renderSvgDetections(event.detections);

  // Update Bedrock Card
  const riskGauge = document.getElementById('riskScoreGauge');
  const riskVal = document.getElementById('riskScoreVal');
  const severityBadge = document.getElementById('severityBadge');
  const interruptBadge = document.getElementById('interruptBadge');
  const reasoningText = document.getElementById('reasoningText');
  const latencyTag = document.getElementById('bedrockLatency');
  const modelEngine = document.getElementById('modelEngine');

  if (riskGauge) riskGauge.style.setProperty('--val', decision.risk_score);
  if (riskVal) riskVal.textContent = decision.risk_score;

  if (severityBadge) {
    severityBadge.className = `badge-severity ${decision.severity}`;
    severityBadge.textContent = decision.severity.toUpperCase();
  }

  if (interruptBadge) {
    interruptBadge.textContent = decision.should_interrupt_user ? 'VOICE DISPATCH ACTIVE' : 'SILENT LOG ONLY';
    interruptBadge.style.background = decision.should_interrupt_user ? 'rgba(139, 92, 246, 0.18)' : 'rgba(100, 116, 139, 0.2)';
    interruptBadge.style.color = decision.should_interrupt_user ? '#8b5cf6' : '#94a3b8';
  }

  if (reasoningText) reasoningText.textContent = decision.reasoning_summary;
  if (latencyTag) latencyTag.textContent = `Latency: ${decision.latency_ms}ms`;
  if (modelEngine) modelEngine.textContent = decision.model_used;

  // Update Spoken Prompt Text
  const promptEl = document.getElementById('spokenPromptText');
  if (promptEl) promptEl.textContent = `"${decision.spoken_alexa_prompt}"`;

  const orbStatus = document.getElementById('orbStatus');
  if (orbStatus) {
    orbStatus.textContent = decision.should_interrupt_user
      ? 'Vocal triage delivered to Alexa+ endpoint'
      : 'Monitoring ambient perimeter silently';
  }

  // Update Actions List
  const actionsEl = document.getElementById('actionsList');
  if (actionsEl) {
    actionsEl.innerHTML = (actions || []).map(act => `
      <div class="action-tag success"><span>✓</span> ${act}</div>
    `).join('');
  }
}

// --- Render SVG Detection Boxes on Camera ---
function renderSvgDetections(detections) {
  const container = document.getElementById('svgDetections');
  if (!container) return;

  const w = 640;
  const h = 360;

  container.innerHTML = (detections || []).map(d => {
    const [ymin, xmin, ymax, xmax] = d.box_normalized;
    const boxX = xmin * w;
    const boxY = ymin * h;
    const boxW = (xmax - xmin) * w;
    const boxH = (ymax - ymin) * h;

    return `
      <g>
        <rect x="${boxX}" y="${boxY}" width="${boxW}" height="${boxH}"
              fill="rgba(0, 229, 255, 0.12)" stroke="#00e5ff" stroke-width="2" stroke-dasharray="4 2"/>
        <rect x="${boxX}" y="${boxY - 20}" width="${d.label.length * 8 + 35}" height="18" fill="#00e5ff" rx="3"/>
        <text x="${boxX + 5}" y="${boxY - 6}" fill="#040711" font-size="11" font-weight="700" font-family="'JetBrains Mono', monospace">
          ${d.label} ${(d.confidence * 100).toFixed(0)}%
        </text>
      </g>
    `;
  }).join('');
}

// --- Web Speech API (Alexa+ Voice Engine) ---
function toggleAudioSpeech() {
  speechEnabled = !speechEnabled;
  const btn = document.getElementById('speechToggleBtn');
  if (btn) {
    btn.style.opacity = speechEnabled ? '1' : '0.4';
    btn.title = speechEnabled ? 'Voice Output ON' : 'Voice Output OFF';
  }
  if (!speechEnabled && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
}

function speakCurrentPrompt() {
  const text = document.getElementById('spokenPromptText')?.textContent?.replace(/"/g, '');
  if (text) speakText(text);
}

function speakText(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.05;
  utterance.pitch = 1.0;

  // Try to find a pleasant English voice
  const voices = window.speechSynthesis.getVoices();
  const naturalVoice = voices.find(v => v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha') || v.lang.startsWith('en'));
  if (naturalVoice) utterance.voice = naturalVoice;

  const waveform = document.getElementById('waveform');
  utterance.onstart = () => {
    if (waveform) waveform.classList.add('active');
  };
  utterance.onend = () => {
    if (waveform) waveform.classList.remove('active');
  };
  utterance.onerror = () => {
    if (waveform) waveform.classList.remove('active');
  };

  window.speechSynthesis.speak(utterance);
}

// --- MCP History Inspector ---
async function loadMcpHistory() {
  try {
    const res = await fetch('/api/mcp/history');
    const data = await res.json();
    rawMcpHistory = data;
    renderMcpLogs();
  } catch (err) {
    console.error('Failed to load MCP history:', err);
  }
}

function renderMcpLogs() {
  const container = document.getElementById('mcpLogContainer');
  const countEl = document.getElementById('mcpCount');
  if (countEl) countEl.textContent = rawMcpHistory.length;

  if (!container) return;

  const filtered = rawMcpHistory.filter(entry => {
    if (mcpFilter === 'all') return true;
    const str = JSON.stringify(entry).toLowerCase();
    if (mcpFilter === 'tools') return str.includes('tool');
    if (mcpFilter === 'resources') return str.includes('resource');
    return true;
  });

  container.innerHTML = filtered.map(item => {
    const dirClass = item.direction || 'inbound';
    const timeStr = new Date(item.timestamp * 1000).toLocaleTimeString();
    const payloadJson = JSON.stringify(item.payload, null, 2);

    return `
      <div class="mcp-entry">
        <div class="mcp-entry-header">
          <span class="mcp-dir-tag ${dirClass}">${dirClass.toUpperCase()}</span>
          <span class="mcp-time">${timeStr} ${item.latency_ms ? `• ${item.latency_ms}ms` : ''}</span>
        </div>
        <pre class="mcp-code-block"><code>${escapeHtml(payloadJson)}</code></pre>
      </div>
    `;
  }).join('');
}

function filterMcp(type) {
  mcpFilter = type;
  document.querySelectorAll('.mcp-filter-tabs .tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('onclick')?.includes(type));
  });
  renderMcpLogs();
}

function clearMcpLog() {
  rawMcpHistory = [];
  renderMcpLogs();
}

// --- Interactive Judge Tool Execution ---
function updateToolParamsPlaceholder() {
  const tool = document.getElementById('judgeToolSelect').value;
  const input = document.getElementById('judgeToolArgs');
  const defaults = {
    ring_poll_events: '{"limit": 2}',
    ring_trigger_scenario: '{"scenario_id": "pet_escape_risk"}',
    bedrock_reason_triage: '{"event_id": "latest"}',
    alexa_proactive_dispatch: '{"spoken_text": "Perimeter secured.", "urgency": "low"}',
    household_action_execute: '{"action_name": "turn_on_floodlight"}',
  };
  if (input) input.placeholder = defaults[tool] || '{}';
}

async function executeJudgeTool() {
  const toolName = document.getElementById('judgeToolSelect').value;
  const rawArgs = document.getElementById('judgeToolArgs').value.trim() || document.getElementById('judgeToolArgs').placeholder;

  let args = {};
  try {
    args = JSON.parse(rawArgs);
  } catch (e) {
    alert('Please enter valid JSON parameters.');
    return;
  }

  const rpcPayload = {
    jsonrpc: '2.0',
    id: `judge-${Date.now()}`,
    method: 'tools/call',
    params: {
      name: toolName,
      arguments: args,
    },
  };

  try {
    const res = await fetch('/mcp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rpcPayload),
    });
    const result = await res.json();
    loadMcpHistory();
  } catch (err) {
    console.error('Judge tool call failed:', err);
  }
}

// --- Friction Log Modal ---
async function openFrictionLogModal() {
  const modal = document.getElementById('frictionModal');
  const contentEl = document.getElementById('frictionLogContent');
  if (modal) modal.classList.add('open');

  try {
    const res = await fetch('/api/friction-log');
    const data = await res.json();
    if (contentEl) {
      // Basic markdown render for headings, lists, and codeblocks
      contentEl.innerHTML = parseMarkdownBasic(data.content);
    }
  } catch (e) {
    if (contentEl) contentEl.textContent = 'Failed to load friction log.';
  }
}

function closeFrictionLogModal() {
  const modal = document.getElementById('frictionModal');
  if (modal) modal.classList.remove('open');
}

function parseMarkdownBasic(md) {
  return md
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/\*(.*)\*/gim, '<em>$1</em>')
    .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
    .replace(/\n\n/gim, '<p></p>')
    .replace(/\n/gim, '<br>');
}

function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

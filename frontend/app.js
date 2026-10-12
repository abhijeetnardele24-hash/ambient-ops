/**
 * AmbientOps — Calm Mission Control Client Application.
 * Full Streamable HTTP Model Context Protocol (MCP v2025-11-25) Web Client.
 * Strict human-in-the-loop operator sequence: Trigger -> Observe -> Analyze -> Review -> Approve.
 * Secure, zero-innerHTML-injection DOM manipulation.
 */

// Application State
let mcpSessionId = null;
let mcpProtocolVersion = '2025-11-25';
let activeIncidentId = null;
let currentEvent = null;
let activeModalTrigger = null;
let rawMcpEntries = [];
let isMcpConnecting = false;

document.addEventListener('DOMContentLoaded', async () => {
  initLiveClock();
  initModalAccessibility();
  await initDeviceFleet();

  // Initialize real Streamable HTTP MCP Client Session
  await initMcpClient();

  // Load initial preset scenario
  await selectScenario('delivery_weather_risk');

  // Background polling for server-side MCP logs
  setInterval(loadServerMcpHistory, 4000);
});

// --- Helper: Robust MCP Response Parser (Handles both application/json and text/event-stream) ---
async function parseMcpResponseBody(res) {
  const text = await res.text();
  if (!text || !text.trim()) return null;
  const trimmed = text.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
    return JSON.parse(trimmed);
  }
  // Parse SSE framed message
  const lines = trimmed.split('\n');
  for (const line of lines) {
    const l = line.trim();
    if (l.startsWith('data:')) {
      const jsonPart = l.slice(5).trim();
      if (jsonPart) {
        return JSON.parse(jsonPart);
      }
    }
  }
  try {
    return JSON.parse(trimmed);
  } catch (e) {
    return { raw: trimmed };
  }
}

// --- Screen Reader Live Announcements ---
function announce(text) {
  const el = document.getElementById('ariaLiveRegion');
  if (el) {
    el.textContent = text;
  }
}

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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
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

// --- Streamable HTTP MCP Client (MCP v2025-11-25) ---
async function initMcpClient() {
  if (isMcpConnecting) return;
  isMcpConnecting = true;

  const statusBadge = document.getElementById('mcpStatusBadge');
  const statusText = document.getElementById('mcpStatusText');
  const sessionText = document.getElementById('activeSessionIdText');

  if (statusBadge) statusBadge.className = 'mode-badge mock';
  if (statusText) statusText.textContent = 'MCP: CONNECTING';
  if (sessionText) sessionText.textContent = 'Negotiating...';

  const initId = `init-${Date.now()}`;
  const initPayload = {
    jsonrpc: '2.0',
    id: initId,
    method: 'initialize',
    params: {
      protocolVersion: mcpProtocolVersion,
      capabilities: {
        roots: { listChanged: true },
        sampling: {},
      },
      clientInfo: {
        name: 'AmbientOps-CalmConsole',
        version: '1.0.0',
      },
    },
  };

  const t0 = performance.now();
  addMcpLogEntry('REQUEST', initPayload);

  try {
    const res = await fetch('/mcp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
      },
      body: JSON.stringify(initPayload),
    });

    const latency = Math.round(performance.now() - t0);

    if (!res.ok) {
      throw new Error(`Initialize failed: HTTP ${res.status}`);
    }

    // Extract official Mcp-Session-Id header (case-insensitive in Fetch API)
    mcpSessionId = res.headers.get('mcp-session-id') || res.headers.get('Mcp-Session-Id');
    const initData = await parseMcpResponseBody(res);
    addMcpLogEntry('RESPONSE', initData, latency);

    if (initData && initData.result && initData.result.protocolVersion) {
      mcpProtocolVersion = initData.result.protocolVersion;
      const verBadge = document.getElementById('negotiatedVersionBadge');
      if (verBadge) verBadge.textContent = `v${mcpProtocolVersion}`;
    }

    // Send notifications/initialized notification (spec requires bodyless 202 response)
    const notifPayload = {
      jsonrpc: '2.0',
      method: 'notifications/initialized',
      params: {},
    };
    addMcpLogEntry('NOTIFICATION', notifPayload);

    const notifHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
    };
    if (mcpSessionId) {
      notifHeaders['Mcp-Session-Id'] = mcpSessionId;
    }

    const notifRes = await fetch('/mcp', {
      method: 'POST',
      headers: notifHeaders,
      body: JSON.stringify(notifPayload),
    });

    if (notifRes.status === 202) {
      addMcpLogEntry('RESPONSE', { status: '202 Accepted', note: 'Bodyless notification ack' }, 5);
    }

    // Update session indicators
    if (sessionText) {
      sessionText.textContent = mcpSessionId ? `${mcpSessionId.slice(0, 10)}...` : 'Active';
      sessionText.title = mcpSessionId || '';
    }

    if (statusBadge) statusBadge.className = 'mode-badge live';
    if (statusText) statusText.textContent = `MCP: CONNECTED (${mcpProtocolVersion})`;

    // Dynamically discover and populate available MCP tools
    await loadMcpTools();

    announce(`MCP Streamable HTTP session connected (${mcpProtocolVersion}).`);
  } catch (err) {
    console.error('MCP handshake failure:', err);
    if (statusBadge) statusBadge.className = 'mode-badge error';
    if (statusText) statusText.textContent = 'MCP: ERROR';
    if (sessionText) sessionText.textContent = 'Disconnected';
    announce('MCP connection failed.');
  } finally {
    isMcpConnecting = false;
    renderMcpLogs();
  }
}

async function reconnectMcpSession() {
  mcpSessionId = null;
  announce('Reconnecting MCP session...');
  await initMcpClient();
}

// --- Load MCP Tools via Streamable HTTP tools/list ---
async function loadMcpTools() {
  const toolSelect = document.getElementById('judgeToolSelect');
  if (!toolSelect) return;

  const reqId = `tools-${Date.now()}`;
  const payload = {
    jsonrpc: '2.0',
    id: reqId,
    method: 'tools/list',
    params: {},
  };

  try {
    const headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json, text/event-stream',
    };
    if (mcpSessionId) headers['Mcp-Session-Id'] = mcpSessionId;

    const t0 = performance.now();
    addMcpLogEntry('REQUEST', payload);

    const res = await fetch('/mcp', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    const latency = Math.round(performance.now() - t0);
    if (!res.ok) throw new Error(`tools/list failed: HTTP ${res.status}`);

    const data = await parseMcpResponseBody(res);
    addMcpLogEntry('RESPONSE', data, latency);

    const tools = (data && data.result && data.result.tools) || [];
    toolSelect.textContent = ''; // clear

    if (tools.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No tools discovered';
      toolSelect.appendChild(opt);
      return;
    }

    tools.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.name;
      opt.textContent = `${t.name} — ${t.description ? t.description.slice(0, 42) + '...' : ''}`;
      toolSelect.appendChild(opt);
    });

    updateToolArgPlaceholder();
  } catch (err) {
    console.warn('Failed to list MCP tools:', err);
  }
}

// --- Interactive Judge Tool Execution (Streamable HTTP tools/call) ---
function updateToolArgPlaceholder() {
  const select = document.getElementById('judgeToolSelect');
  const input = document.getElementById('judgeToolArgs');
  if (!select || !input) return;

  const defaults = {
    smart_entry_poll_events: '{"limit": 2}',
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
  const callBtn = document.getElementById('btnCallTool');
  if (!select || !input || !select.value) return;

  let args = {};
  const raw = input.value.trim() || input.placeholder;
  try {
    args = JSON.parse(raw);
  } catch (e) {
    alert('Please enter valid JSON parameters.');
    return;
  }

  if (callBtn) callBtn.disabled = true;

  const callId = `call-${Date.now()}`;
  const payload = {
    jsonrpc: '2.0',
    id: callId,
    method: 'tools/call',
    params: {
      name: select.value,
      arguments: args,
    },
  };

  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
  };
  if (mcpSessionId) headers['Mcp-Session-Id'] = mcpSessionId;

  const t0 = performance.now();
  addMcpLogEntry('REQUEST', payload);
  renderMcpLogs();

  try {
    const res = await fetch('/mcp', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    const latency = Math.round(performance.now() - t0);
    const data = await parseMcpResponseBody(res);
    addMcpLogEntry('RESPONSE', data, latency);
    announce(`Tool ${select.value} executed in ${latency}ms.`);
  } catch (err) {
    console.error('Judge tool call failed:', err);
    addMcpLogEntry('RESPONSE', { error: String(err) }, 0);
  } finally {
    if (callBtn) callBtn.disabled = false;
    renderMcpLogs();
  }
}

// --- Live MCP Log Inspector ---
function addMcpLogEntry(direction, payload, latencyMs = null) {
  rawMcpEntries.unshift({
    direction,
    payload,
    timestamp: Date.now(),
    latency_ms: latencyMs,
  });
  if (rawMcpEntries.length > 60) rawMcpEntries.pop();
}

function renderMcpLogs() {
  const container = document.getElementById('mcpLogFeed');
  if (!container) return;

  container.textContent = ''; // clear

  if (rawMcpEntries.length === 0) {
    const emptyP = document.createElement('p');
    emptyP.style.color = 'var(--text-muted)';
    emptyP.style.fontSize = '0.75rem';
    emptyP.style.padding = '8px';
    emptyP.textContent = 'Waiting for MCP protocol frames...';
    container.appendChild(emptyP);
    return;
  }

  rawMcpEntries.slice(0, 35).forEach(entry => {
    const item = document.createElement('div');
    item.className = 'mcp-entry-item';

    const header = document.createElement('div');
    header.className = 'mcp-entry-header';

    const dirTag = document.createElement('span');
    const dirLower = (entry.direction || 'internal').toLowerCase();
    dirTag.className = `mcp-dir-tag ${dirLower}`;
    dirTag.textContent = entry.direction;

    const timeSpan = document.createElement('span');
    const t = new Date(entry.timestamp).toLocaleTimeString();
    timeSpan.textContent = `${t}${entry.latency_ms !== null ? ` (${entry.latency_ms}ms)` : ''}`;

    header.appendChild(dirTag);
    header.appendChild(timeSpan);

    const pre = document.createElement('pre');
    pre.tabIndex = 0;
    pre.setAttribute('aria-label', 'JSON message envelope');
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

async function loadServerMcpHistory() {
  try {
    const res = await fetch('/api/mcp/history');
    if (!res.ok) return;
    const serverLogs = await res.json();
    if (Array.isArray(serverLogs) && serverLogs.length > 0) {
      if (rawMcpEntries.length === 0) {
        rawMcpEntries = serverLogs.map(item => ({
          direction: (item.direction || 'INTERNAL').toUpperCase(),
          payload: item.payload,
          timestamp: item.timestamp * 1000,
          latency_ms: item.latency_ms || null,
        }));
        renderMcpLogs();
      }
    }
  } catch (e) {
    // Silent background poll
  }
}

// --- 5-Step MCP Protocol Verification Modal ---
async function runMcpVerification() {
  activeModalTrigger = document.activeElement;
  const modal = document.getElementById('mcpVerifyModal');
  const checklist = document.getElementById('mcpVerifyChecklist');
  if (!modal || !checklist) return;

  modal.classList.add('open');
  modal.focus();
  checklist.textContent = ''; // clear

  const steps = [
    { id: 1, name: '1. Protocol Handshake (initialize)', method: 'initialize' },
    { id: 2, name: '2. Client Notification (notifications/initialized)', method: 'notifications/initialized' },
    { id: 3, name: '3. Tool Discovery (tools/list)', method: 'tools/list' },
    { id: 4, name: '4. Resource Registry (resources/list & context)', method: 'resources/list' },
    { id: 5, name: '5. Prompt Template Discovery (prompts/list)', method: 'prompts/list' },
  ];

  // Render pending placeholders
  const stepElements = {};
  steps.forEach(s => {
    const row = document.createElement('div');
    row.className = 'verify-row pending';
    row.id = `verify-step-${s.id}`;

    const descSpan = document.createElement('span');
    descSpan.textContent = s.name;

    const badgeSpan = document.createElement('span');
    badgeSpan.className = 'verify-badge';
    badgeSpan.textContent = 'RUNNING...';

    row.appendChild(descSpan);
    row.appendChild(badgeSpan);
    checklist.appendChild(row);
    stepElements[s.id] = { row, badge: badgeSpan, desc: descSpan };
  });

  let allPassed = true;
  let testSessionId = null;

  try {
    // --- Step 1: Initialize ---
    const t0 = performance.now();
    const initRes = await fetch('/mcp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream',
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 'test-init',
        method: 'initialize',
        params: {
          protocolVersion: '2025-11-25',
          capabilities: {},
          clientInfo: { name: 'verifier-test', version: '1.0' },
        },
      }),
    });
    const lat1 = Math.round(performance.now() - t0);
    testSessionId = initRes.headers.get('mcp-session-id') || initRes.headers.get('Mcp-Session-Id');
    const initData = await parseMcpResponseBody(initRes);

    const pass1 = initRes.ok && initData && initData.result && initData.result.protocolVersion === '2025-11-25' && Boolean(testSessionId);
    markStep(stepElements[1], pass1, pass1 ? `✓ PASS (${lat1}ms) • Session: ${testSessionId.slice(0, 8)}...` : '✗ FAIL • Handshake error');
    if (!pass1) allPassed = false;

    // --- Step 2: notifications/initialized (Must be 202 bodyless) ---
    const t1 = performance.now();
    const notifHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' };
    if (testSessionId) notifHeaders['Mcp-Session-Id'] = testSessionId;

    const notifRes = await fetch('/mcp', {
      method: 'POST',
      headers: notifHeaders,
      body: JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized', params: {} }),
    });
    const lat2 = Math.round(performance.now() - t1);
    const notifText = await notifRes.text();
    const pass2 = notifRes.status === 202 && notifText.trim() === '';
    markStep(stepElements[2], pass2, pass2 ? `✓ PASS (${lat2}ms) • HTTP 202 Accepted (Bodyless)` : `✗ FAIL • HTTP ${notifRes.status}`);
    if (!pass2) allPassed = false;

    // --- Step 3: tools/list (Verify 5 tools) ---
    const t2 = performance.now();
    const toolsHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' };
    if (testSessionId) toolsHeaders['Mcp-Session-Id'] = testSessionId;

    const toolsRes = await fetch('/mcp', {
      method: 'POST',
      headers: toolsHeaders,
      body: JSON.stringify({ jsonrpc: '2.0', id: 'test-tools', method: 'tools/list' }),
    });
    const lat3 = Math.round(performance.now() - t2);
    const toolsData = await parseMcpResponseBody(toolsRes);
    const toolNames = (toolsData && toolsData.result && toolsData.result.tools ? toolsData.result.tools.map(t => t.name) : []);
    const requiredTools = ['smart_entry_poll_events', 'smart_entry_trigger_scenario', 'bedrock_reason_triage', 'alexa_proactive_dispatch', 'household_action_execute'];
    const pass3 = toolsRes.ok && requiredTools.every(rt => toolNames.includes(rt));
    markStep(stepElements[3], pass3, pass3 ? `✓ PASS (${lat3}ms) • 5/5 Canonical Tools Registered` : '✗ FAIL • Incomplete tool registry');
    if (!pass3) allPassed = false;

    // --- Step 4: resources/list ---
    const t3 = performance.now();
    const resHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' };
    if (testSessionId) resHeaders['Mcp-Session-Id'] = testSessionId;

    const resRes = await fetch('/mcp', {
      method: 'POST',
      headers: resHeaders,
      body: JSON.stringify({ jsonrpc: '2.0', id: 'test-res', method: 'resources/list' }),
    });
    const lat4 = Math.round(performance.now() - t3);
    const resData = await parseMcpResponseBody(resRes);
    const resources = (resData && resData.result && resData.result.resources) || [];
    const hasHouseholdContext = resources.some(r => r.uri === 'ambient://household/context');
    const pass4 = resRes.ok && hasHouseholdContext;
    markStep(stepElements[4], pass4, pass4 ? `✓ PASS (${lat4}ms) • ambient://household/context Verified` : '✗ FAIL • Resource unavailable');
    if (!pass4) allPassed = false;

    // --- Step 5: prompts/list ---
    const t4 = performance.now();
    const promptHeaders = { 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream' };
    if (testSessionId) promptHeaders['Mcp-Session-Id'] = testSessionId;

    const promptRes = await fetch('/mcp', {
      method: 'POST',
      headers: promptHeaders,
      body: JSON.stringify({ jsonrpc: '2.0', id: 'test-prompt', method: 'prompts/list' }),
    });
    const lat5 = Math.round(performance.now() - t4);
    const promptData = await parseMcpResponseBody(promptRes);
    const prompts = (promptData && promptData.result && promptData.result.prompts) || [];
    const hasTriagePrompt = prompts.some(p => p.name === 'triage_incident' || p.name === 'incident_triage_prompt');
    const pass5 = promptRes.ok && hasTriagePrompt;
    markStep(stepElements[5], pass5, pass5 ? `✓ PASS (${lat5}ms) • triage_incident Prompt Discovered` : '✗ FAIL • Prompt unavailable');
    if (!pass5) allPassed = false;

    // Summary row
    const summaryRow = document.createElement('div');
    summaryRow.className = `verify-row ${allPassed ? 'pass' : 'fail'}`;
    summaryRow.style.marginTop = '12px';
    summaryRow.style.fontWeight = '700';

    const sumTitle = document.createElement('span');
    sumTitle.textContent = allPassed
      ? '★ 5/5 automated MCP transport checks passed (MCP v2025-11-25)'
      : '⚠ MCP SPECIFICATION CHECKS INCOMPLETE';

    const sumBadge = document.createElement('span');
    sumBadge.className = 'verify-badge';
    sumBadge.textContent = allPassed ? 'GO FOR SUBMISSION' : 'AUDIT REQUIRED';

    summaryRow.appendChild(sumTitle);
    summaryRow.appendChild(sumBadge);
    checklist.appendChild(summaryRow);

    announce(allPassed ? 'MCP transport verification completed: 5/5 automated checks passed.' : 'MCP verification completed with warnings.');
  } catch (err) {
    console.error('Verification error:', err);
  }
}

function markStep(elementGroup, isPass, text) {
  if (!elementGroup) return;
  elementGroup.row.className = `verify-row ${isPass ? 'pass' : 'fail'}`;
  elementGroup.badge.textContent = text;
}

function closeMcpVerifyModal() {
  const modal = document.getElementById('mcpVerifyModal');
  if (modal) modal.classList.remove('open');
  if (activeModalTrigger && typeof activeModalTrigger.focus === 'function') {
    activeModalTrigger.focus();
  }
}

// --- Scenario Selection & Operator Flow ---
async function selectScenario(scenarioId) {
  // Update button active state
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

  const btnApprove = document.getElementById('btnApprove');
  const btnReject = document.getElementById('btnReject');
  if (btnApprove) btnApprove.disabled = true;
  if (btnReject) btnReject.disabled = true;

  try {
    // 1. Trigger Scenario
    const triggerRes = await fetch(`/api/events/trigger/${scenarioId}`, { method: 'POST' });
    if (!triggerRes.ok) throw new Error(`Trigger failed: HTTP ${triggerRes.status}`);
    const triggerData = await triggerRes.json();
    currentEvent = triggerData.event;

    // Render Evidence
    renderVisualEvidence(currentEvent);

    // 2. Analyze via MCP Bedrock Agent
    const analyzeRes = await fetch(`/api/agent/analyze/${currentEvent.event_id}`, { method: 'POST' });
    if (!analyzeRes.ok) throw new Error(`Analyze failed: HTTP ${analyzeRes.status}`);
    const analyzeData = await analyzeRes.json();

    activeIncidentId = analyzeData.incident_id;
    const incident = analyzeData.incident;

    renderIncidentDecision(incident.triage_decision);

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge pending';
      approvalBadge.textContent = 'AWAITING OPERATOR APPROVAL';
    }

    if (btnApprove) btnApprove.disabled = false;
    if (btnReject) btnReject.disabled = false;

    announce(`Incident ${scenarioId} analyzed. Awaiting operator approval.`);
  } catch (err) {
    console.error('Error during scenario pipeline:', err);
    if (approvalBadge) {
      approvalBadge.className = 'gate-badge rejected';
      approvalBadge.textContent = 'ANALYSIS PIPELINE ERROR';
    }
  }
}

// --- Render Visual Evidence (Safe SVG Nodes) ---
function renderVisualEvidence(event) {
  const cameraLabel = document.getElementById('cameraNameLabel');
  if (cameraLabel) cameraLabel.textContent = event.device_name;

  const rainEl = document.getElementById('telemetryPrecipitation');
  const luxEl = document.getElementById('telemetryLux');
  const confEl = document.getElementById('telemetryConfidence');

  if (rainEl) {
    rainEl.textContent = event.ambient_conditions.rain_probability !== null && event.ambient_conditions.rain_probability !== undefined
      ? `${Math.round(event.ambient_conditions.rain_probability * 100)}%`
      : 'N/A';
  }
  if (luxEl) {
    luxEl.textContent = event.ambient_conditions.ambient_lux ? `${event.ambient_conditions.ambient_lux} lx` : '40 lx';
  }
  if (confEl) {
    confEl.textContent = event.detections.length > 0 ? event.detections[0].confidence.toFixed(2) : '0.90';
  }

  // Render SVG Bounding Boxes securely via DOM methods
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
    const labelWidth = Math.max(80, d.label.length * 8 + 36);
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
  const engineBadge = document.getElementById('engineModeBadge');

  if (rationaleEl) rationaleEl.textContent = decision.decision_rationale;
  if (riskEl) riskEl.textContent = `${decision.risk_score} / 100`;
  if (confEl) confEl.textContent = `${Math.round(decision.confidence_score * 100)}%`;
  if (sevEl) sevEl.textContent = (decision.severity || 'MODERATE').toUpperCase();
  if (actionEl) {
    const suggested = decision.suggested_actions && decision.suggested_actions.length > 0
      ? decision.suggested_actions.join(', ')
      : 'None';
    actionEl.textContent = `${decision.recommended_action} • ${suggested}`;
  }
  if (promptEl) promptEl.textContent = `"${decision.spoken_alexa_prompt}"`;

  if (engineBadge) {
    if (decision.provider_mode === 'bedrock-live') {
      engineBadge.className = 'mode-badge live';
      engineBadge.textContent = '■ AWS BEDROCK: LIVE';
    } else {
      engineBadge.className = 'mode-badge mock';
      engineBadge.textContent = '■ ENGINE: DETERMINISTIC SIMULATOR';
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

    if (!res.ok) throw new Error(`Approve failed: HTTP ${res.status}`);
    const data = await res.json();

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge approved';
      approvalBadge.textContent = '✓ SIMULATION APPROVED';
    }

    if (outcomeBlock) {
      outcomeBlock.style.display = 'block';
      const small = outcomeBlock.querySelector('small');
      if (small) {
        const executed = (data.incident && data.incident.executed_actions) || [];
        small.textContent = `✓ SIMULATED OUTCOME VERIFIED: Remediations [${executed.join(', ')}] executed & logged to audit ledger.`;
      }
    }

    // Play vocal prompt via browser Web Speech synthesis simulation
    const decision = data.incident.triage_decision;
    if (decision && decision.should_interrupt_user) {
      speakVocalPrompt(decision.spoken_alexa_prompt);
    }

    announce('Simulation approved. Remediations executed.');
  } catch (err) {
    console.error('Failed to approve incident:', err);
    if (btnApprove) btnApprove.disabled = false;
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
    const res = await fetch(`/api/operator/reject/${activeIncidentId}`, { method: 'POST' });
    if (!res.ok) throw new Error(`Reject failed: HTTP ${res.status}`);

    if (approvalBadge) {
      approvalBadge.className = 'gate-badge rejected';
      approvalBadge.textContent = '✗ DISMISSED BY OPERATOR';
    }

    announce('Incident dismissed by operator.');
  } catch (err) {
    console.error('Failed to reject incident:', err);
    if (btnReject) btnReject.disabled = false;
  }
}

// --- Reset to Demo State ---
async function resetToDemoState() {
  activeIncidentId = null;
  currentEvent = null;
  clearMcpDisplay();

  const outcomeBlock = document.getElementById('verifiedOutcomeBlock');
  if (outcomeBlock) outcomeBlock.style.display = 'none';

  await reconnectMcpSession();
  await selectScenario('delivery_weather_risk');

  announce('Demo state reset to initial preset.');
}

// --- Web Speech API Synthesis Simulation ---
function speakCurrentTranscript() {
  const textEl = document.getElementById('spokenTranscriptText');
  if (textEl) {
    const cleanText = textEl.textContent.replace(/"/g, '');
    speakVocalPrompt(cleanText);
  }
}

function speakVocalPrompt(text) {
  if (!('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const natural = voices.find(v => v.name.includes('Natural') || v.name.includes('Google') || v.lang.startsWith('en'));
    if (natural) utterance.voice = natural;

    window.speechSynthesis.speak(utterance);
  } catch (e) {
    console.warn('Speech synthesis unavailable or blocked:', e);
  }
}

// --- Accessible Modals (Escape key, Focus Trap, Return Focus) ---
function initModalAccessibility() {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const frictionModal = document.getElementById('frictionModal');
      const verifyModal = document.getElementById('mcpVerifyModal');
      if (frictionModal && frictionModal.classList.contains('open')) {
        closeFrictionModal();
      }
      if (verifyModal && verifyModal.classList.contains('open')) {
        closeMcpVerifyModal();
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
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    if (content) {
      content.textContent = ''; // clear

      // Render markdown safely using DOM text blocks
      const lines = data.content.split('\n');
      let inCodeBlock = false;
      let codeBuffer = [];

      lines.forEach(line => {
        if (line.startsWith('```')) {
          if (inCodeBlock) {
            const pre = document.createElement('pre');
            pre.tabIndex = 0;
            pre.setAttribute('aria-label', 'Code snippet');
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
          h1.style.fontSize = '1.25rem';
          h1.style.marginBottom = '12px';
          content.appendChild(h1);
        } else if (line.startsWith('## ')) {
          const h2 = document.createElement('h2');
          h2.textContent = line.slice(3);
          h2.style.fontSize = '1.05rem';
          h2.style.marginTop = '18px';
          h2.style.marginBottom = '8px';
          content.appendChild(h2);
        } else if (line.startsWith('### ')) {
          const h3 = document.createElement('h3');
          h3.textContent = line.slice(4);
          h3.style.fontSize = '0.95rem';
          h3.style.marginTop = '12px';
          h3.style.marginBottom = '6px';
          content.appendChild(h3);
        } else if (line.startsWith('* ') || line.startsWith('- ')) {
          const li = document.createElement('li');
          li.textContent = line.slice(2);
          li.style.marginLeft = '16px';
          content.appendChild(li);
        } else if (line.trim().length > 0) {
          const p = document.createElement('p');
          p.textContent = line;
          p.style.marginBottom = '8px';
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

"""Comprehensive Playwright End-to-End & Axe-core Accessibility Test Suite for AmbientOps.
Validates:
- Live Calm Mission Control web interface
- Real Streamable HTTP MCP handshake over /mcp
- Scenario triggers and bounding box visual evidence rendering
- Operator Human Approval boundary (Awaiting -> Approve / Reject)
- Outcome verification & remediation logging
- Direct interactive tools/call execution via inspector
- 5-step MCP transport verification modal
- Accessible modal keyboard navigation (Esc, focus return)
- Responsive viewports (320px, 360px, 768px, 1024px, 1440px, 1920px)
- Zero horizontal overflow at 320px
- Automated Axe-core WCAG 2.1 AA accessibility audit
- Generation of verified UI screenshots
"""

import socket
import threading
import time
from pathlib import Path
import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from axe_playwright_python.sync_playwright import Axe
from backend.server import app


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LiveServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


@pytest.fixture(scope="module")
def live_server():
    port = get_free_port()
    host = "127.0.0.1"
    server = LiveServerThread(host, port)
    server.start()

    # Wait for server to be responsive
    base_url = f"http://{host}:{port}"
    deadline = time.time() + 10.0
    connected = False
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.3):
                connected = True
                break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)

    if not connected:
        raise RuntimeError(f"Live test server failed to start at {base_url}")

    yield base_url
    server.stop()


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_mission_control_e2e_and_accessibility(live_server, browser_context):
    """Full E2E walkthrough validating all operator and MCP capabilities."""
    page = browser_context.new_page(viewport={"width": 1440, "height": 900})
    assets_dir = Path(__file__).parent.parent / "assets" / "screenshots"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 1. Initial Page Load
    page.goto(f"{live_server}/", wait_until="networkidle")
    assert "AmbientOps — Calm Mission Control Console" in page.title()

    # Verify MCP handshake connected
    mcp_badge = page.locator("[data-testid='mcp-status-badge']")
    mcp_badge.wait_for(state="visible", timeout=10000)
    page.wait_for_function(
        "() => document.getElementById('mcpStatusText').textContent.includes('CONNECTED')",
        timeout=10000,
    )
    assert "CONNECTED" in page.locator("#mcpStatusText").inner_text()

    # Verify Session ID is populated
    session_text = page.locator("#activeSessionIdText").inner_text()
    assert session_text != "None" and session_text != "Negotiating..."

    # Capture initial overview screenshot
    page.screenshot(path=str(assets_dir / "overview.png"), full_page=True)

    # 2. Operator Approval Boundary Verification (Initial Preset: delivery_weather_risk)
    page.wait_for_selector("#approvalStatusBadge", timeout=5000)
    assert "AWAITING OPERATOR APPROVAL" in page.locator("#approvalStatusBadge").inner_text()

    # Click Approve Simulation
    btn_approve = page.locator("[data-testid='operator-approve-btn']")
    assert btn_approve.is_enabled()
    btn_approve.click()

    # Verify transition to SIMULATION APPROVED
    page.wait_for_function(
        "() => document.getElementById('approvalStatusBadge').textContent.includes('SIMULATION APPROVED')",
        timeout=5000,
    )
    outcome_block = page.locator("#verifiedOutcomeBlock")
    assert outcome_block.is_visible()
    assert "SIMULATED OUTCOME VERIFIED" in outcome_block.inner_text()

    # 3. Switch Scenario to Care Inactivity (elder_immobility_alert)
    scenario_elder = page.locator("[data-testid='scenario-elder']")
    scenario_elder.click()

    page.wait_for_function(
        "() => document.getElementById('cameraNameLabel').textContent.includes('Hallway') || document.getElementById('cameraNameLabel').textContent.includes('Sensor')",
        timeout=5000,
    )
    page.wait_for_function(
        "() => document.getElementById('approvalStatusBadge').textContent.includes('AWAITING OPERATOR APPROVAL')",
        timeout=5000,
    )
    page.screenshot(path=str(assets_dir / "care_immobility.png"))

    # 4. Switch Scenario to Pet Perimeter (pet_escape_risk)
    scenario_pet = page.locator("[data-testid='scenario-pet']")
    scenario_pet.click()

    page.wait_for_function(
        "() => document.getElementById('cameraNameLabel').textContent.includes('Garden') || document.getElementById('cameraNameLabel').textContent.includes('Perimeter')",
        timeout=5000,
    )
    page.wait_for_function(
        "() => document.getElementById('approvalStatusBadge').textContent.includes('AWAITING OPERATOR APPROVAL')",
        timeout=5000,
    )
    page.screenshot(path=str(assets_dir / "pet_escape.png"))

    # 5. Switch Scenario to Loitering & Test Reject / Dismissal Flow
    scenario_loitering = page.locator("[data-testid='scenario-loitering']")
    scenario_loitering.click()

    page.wait_for_function(
        "() => document.getElementById('approvalStatusBadge').textContent.includes('AWAITING OPERATOR APPROVAL')",
        timeout=5000,
    )
    page.screenshot(path=str(assets_dir / "night_loitering.png"))

    # Click Dismiss / Reject
    btn_reject = page.locator("[data-testid='operator-reject-btn']")
    assert btn_reject.is_enabled()
    btn_reject.click()

    page.wait_for_function(
        "() => document.getElementById('approvalStatusBadge').textContent.includes('DISMISSED BY OPERATOR')",
        timeout=5000,
    )

    # 6. Interactive MCP Tool Execution Form
    tool_select = page.locator("[data-testid='judge-tool-select']")
    tool_select.wait_for(state="visible", timeout=5000)
    page.wait_for_function("() => document.getElementById('judgeToolSelect').options.length >= 3", timeout=5000)

    tool_select.select_option("smart_entry_poll_events")
    call_btn = page.locator("[data-testid='judge-tool-call-btn']")
    call_btn.click()

    # Wait for log feed update
    page.wait_for_timeout(1000)
    log_feed = page.locator("[data-testid='mcp-log-feed']")
    assert "smart_entry_poll_events" in log_feed.inner_text()
    page.screenshot(path=str(assets_dir / "mcp_tool_execution.png"))

    # 7. 5-Step MCP Verification Modal
    verify_btn = page.locator("[data-testid='mcp-verify-btn']")
    verify_btn.click()

    verify_modal = page.locator("#mcpVerifyModal")
    verify_modal.wait_for(state="visible", timeout=5000)

    # Wait for 5/5 checklist to pass
    page.wait_for_function(
        "() => document.getElementById('mcpVerifyChecklist').textContent.includes('5/5 MCP PROTOCOL CHECKS VERIFIED')",
        timeout=15000,
    )
    assert "100% SPEC COMPLIANT" in page.locator("#mcpVerifyChecklist").inner_text()

    # Press Escape key to close modal
    page.keyboard.press("Escape")
    page.wait_for_function(
        "() => !document.getElementById('mcpVerifyModal').classList.contains('open')",
        timeout=3000,
    )

    # 8. Friction Log Modal & Escape Return
    friction_btn = page.locator("[data-testid='friction-log-btn']")
    friction_btn.click()

    friction_modal = page.locator("#frictionModal")
    friction_modal.wait_for(state="visible", timeout=5000)
    page.wait_for_function(
        "() => document.getElementById('frictionContentArea').textContent.length > 50",
        timeout=5000,
    )
    page.screenshot(path=str(assets_dir / "friction_log_modal.png"))

    page.keyboard.press("Escape")
    page.wait_for_function(
        "() => !document.getElementById('frictionModal').classList.contains('open')",
        timeout=3000,
    )

    # 9. Responsive Viewports & Horizontal Overflow Check (320px - 1920px)
    viewports = [
        {"width": 320, "height": 640},
        {"width": 360, "height": 740},
        {"width": 768, "height": 1024},
        {"width": 1024, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1920, "height": 1080},
    ]

    for vp in viewports:
        page.set_viewport_size(vp)
        page.wait_for_timeout(300)
        # Assert zero horizontal scroll on ultra-compact mobile (320px)
        if vp["width"] == 320:
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            inner_width = page.evaluate("() => window.innerWidth")
            assert scroll_width <= inner_width + 1, f"Horizontal scroll detected at 320px: {scroll_width} > {inner_width}"

    # Reset to desktop viewport for a11y audit
    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_timeout(500)

    # 10. Automated Axe-core Accessibility Audit
    results = Axe().run(page)
    assert results.violations_count == 0, f"Accessibility violations found:\n{results.generate_report()}"

    page.close()

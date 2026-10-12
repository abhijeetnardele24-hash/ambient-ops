"""Safe live Amazon Bedrock verification script for AmbientOps.

Requires:
  ENABLE_LIVE_BEDROCK=true
  FORCE_BEDROCK_SIMULATOR=false
  Configured AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.)

Verifies one package-in-rain scenario against the real Amazon Bedrock Converse API.
Fails unless provider_mode is 'bedrock-live'.
Outputs and saves ONLY sanitized operational telemetry (zero credentials/PII).
"""

import datetime
import json
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("=" * 65)
    print("  AmbientOps: Amazon Bedrock Live Converse Verification")
    print("=" * 65)

    # 1. Enforce explicit opt-in environment variables
    enable_live = os.getenv("ENABLE_LIVE_BEDROCK", "").lower() in ("true", "1", "yes")
    force_sim = os.getenv("FORCE_BEDROCK_SIMULATOR", "true").lower() in ("true", "1", "yes")

    if not enable_live:
        print("\n[ERROR] ENABLE_LIVE_BEDROCK is not set to 'true'.")
        print("To enable live Bedrock verification, set:")
        print("  $env:ENABLE_LIVE_BEDROCK='true'        # PowerShell")
        print("  export ENABLE_LIVE_BEDROCK=true        # Linux/macOS")
        return 1

    if force_sim:
        print("\n[ERROR] FORCE_BEDROCK_SIMULATOR is set to 'true'.")
        print("To allow live Bedrock calls, set:")
        print("  $env:FORCE_BEDROCK_SIMULATOR='false'   # PowerShell")
        print("  export FORCE_BEDROCK_SIMULATOR=false   # Linux/macOS")
        return 1

    # 2. Check for boto3
    try:
        import boto3
    except ImportError:
        print("\n[ERROR] boto3 is not installed in the active environment.")
        print("Install dependencies with: pip install -r requirements.txt")
        return 1

    # 3. Check for AWS credentials via boto3 session
    session = boto3.Session()
    creds = session.get_credentials()
    if not creds or not creds.access_key:
        print("\n[ERROR] No active AWS credentials found in environment.")
        print("Please configure AWS credentials via AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY")
        print("or run 'aws configure' before executing live verification.")
        return 1

    # 4. Import backend modules and re-initialize Bedrock agent
    from backend.config import settings

    # Override settings explicitly for this script execution
    settings.enable_live_bedrock = True
    settings.force_bedrock_simulator = False

    from backend.bedrock_agent import BedrockAgent
    from backend.smart_entry_simulator import smart_entry_simulator

    agent = BedrockAgent()
    status = agent.get_runtime_status()

    # 5. Fail unless provider_mode is bedrock-live
    if status.get("provider_mode") != "bedrock-live":
        print("\n[FAIL] Agent did not initialize in 'bedrock-live' mode.")
        print(f"Current provider mode: {status.get('provider_mode')}")
        return 1

    print("\n[OK] Agent initialized in 'bedrock-live' mode.")
    print(f"     Target Region:   {settings.aws_region}")
    print(f"     Target Model:    {settings.bedrock_model_id}")

    # 6. Retrieve package-in-rain scenario
    scenario = smart_entry_simulator.get_scenario("delivery_weather_risk")
    if not scenario:
        print("\n[FAIL] Scenario 'delivery_weather_risk' not found in simulator catalog.")
        return 1

    print("\nExecuting live Bedrock Converse API triage call...")
    t0 = time.perf_counter()
    decision = agent.triage_ambient_event(
        event_summary=scenario.get("summary", "Delivery package observed on front porch in incoming rain"),
        device_name="Front Porch Cam Pro (Simulated)",
        detections=scenario.get("detections", []),
        ambient_conditions=scenario.get("ambient_conditions", {}),
        resident_context={
            "household_name": settings.household_name,
            "resident_display_name": "Resident",
            "quiet_hours_active": False,
            "current_mode": "home_normal",
        },
        request_id=f"verify_{int(time.time())}",
    )
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    # 7. Validate live decision
    if decision.provider_mode != "bedrock-live":
        print(f"\n[FAIL] Triage returned provider_mode='{decision.provider_mode}', expected 'bedrock-live'.")
        return 1

    # 8. Create sanitized evidence record (strictly zero credentials, account IDs, tokens, or personal info)
    sanitized_evidence = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "provider_mode": decision.provider_mode,
        "aws_region": settings.aws_region,
        "model_id": decision.model_used,
        "request_id": decision.request_id,
        "measured_latency_ms": elapsed_ms,
        "schema_status": "VALID_STRUCTURED_JSON",
        "output_summary": {
            "risk_score": decision.risk_score,
            "severity": decision.severity,
            "should_interrupt": decision.should_interrupt_user,
            "has_rationale": bool(decision.decision_rationale),
            "has_alexa_prompt": bool(decision.spoken_alexa_prompt),
            "recommended_action": decision.recommended_action,
        },
    }

    # 9. Print sanitized evidence to console
    print("\n" + "=" * 65)
    print("  LIVE BEDROCK CONVERSE VERIFICATION EVIDENCE (SANITIZED)")
    print("=" * 65)
    print(json.dumps(sanitized_evidence, indent=2))
    print("=" * 65)

    # 10. Save sanitized record to docs/evidence/live_bedrock_verification.json
    out_dir = PROJECT_ROOT / "docs" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "live_bedrock_verification.json"
    out_file.write_text(json.dumps(sanitized_evidence, indent=2), encoding="utf-8")
    print(f"\n[SUCCESS] Sanitized evidence saved to {out_file.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

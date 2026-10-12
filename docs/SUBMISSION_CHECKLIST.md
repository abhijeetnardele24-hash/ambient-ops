# Amazon Developer Hackathon 2026: Submission Checklist

**Competition**: *Build, Ship, Shape: Amazon Developer Hackathon 2026*  
**Deadline**: Friday, October 23, 2026, at 12:00 PM PDT  
**Project**: **AmbientOps**  
**Submission Owner**: Abhijeet Nardele (`abhinardele006@gmail.com`)  
**Repository**: `https://github.com/abhijeetnardele24-hash/ambient-ops`  

---

## 1. Compliance & Eligibility Verification

- [x] **Primary Track Confirmed**: **Alexa+ Track** (Implemented using Model Context Protocol open standard v2025-11-25 with Streamable HTTP transports and official `MCPServer`).
- [x] **Mini-Challenge Confirmed**: **AWS Builder Mini-Challenge** (Integrated Amazon Bedrock Converse API with Claude 3.5 Sonnet and deterministic offline simulator).
- [x] **Honest Simulation Disclosure**: Smart entry cameras and sensors explicitly disclosed as simulated via deterministic preset simulator (`backend/smart_entry_simulator.py`). Alexa voice is simulated via browser Web Speech API (`window.speechSynthesis`) with no real physical Echo endpoint claimed.
- [x] **Human Approval Boundary**: Explicit operator approval gate enforced before simulating any physical smart home remediation.
- [x] **Calm Mission Control UI**: Off-white paper canvas, forest ink, structural borders; zero glassmorphism, floating orbs, or neon glow. Automated Axe scan found zero violations.
- [x] **Security Hardening**: CSP, X-Frame-Options, X-Content-Type-Options, X-Request-ID, DNS rebinding defenses, strict CORS allowlist, and zero-innerHTML DOM manipulation.
- [x] **Automated Tests & Coverage**: 46 passing tests with **87% measured statement coverage** (exceeding >=85% threshold), including unit, integration, Streamable HTTP interop, and Playwright E2E + Axe-core tests.
- [x] **Official Developer Friction Log**: 4-entry technical friction report in official 7-field format prepared for the +10% bonus evaluation (`docs/FRICTION_LOG.md`).
- [x] **Public Code Repository**: Live at `https://github.com/abhijeetnardele24-hash/ambient-ops` with open-source MIT license.
- [x] **Docker Deployment**: `Dockerfile` and `docker-compose.yml` included.
- [x] **3-Minute Video Script**: Detailed shot list, timings, and voiceover prepared in `docs/DEMO_SCRIPT.md`.
- [x] **Devpost Draft Copy**: Complete text ready in `docs/DEVPOST_SUBMISSION.md`.
- [x] **Public Demo Walkthrough Video**: `https://youtu.be/0qtmY3y9X4g` (Public, 2:47, English narration, no copyrighted music/unlicensed footage, visibly demonstrates MCP `initialize`, `tools/list`, and `tools/call`, and identifies Bedrock as **SIMULATED** in the recorded run).

---

## 2. Final Owner Actions Before Hitting "Submit" on Devpost

1. [x] **Video Recording**: The 2:47 English walkthrough is public at `https://youtu.be/0qtmY3y9X4g` and follows `docs/DEMO_SCRIPT.md`. Verified:
   - Uploaded publicly to YouTube or Vimeo (no private videos).
   - Zero copyrighted background music or unlicensed third-party footage.
   - Shows the working MCP flow (`initialize`, `tools/list`, and `tools/call`).
   - Visibly shows whether Bedrock is in **LIVE** or **SIMULATED** mode (narrator must match visible badge).
   - Public video link is ready for the Devpost form.
2. [ ] **Devpost Form Filling**: Copy fields from `docs/DEVPOST_SUBMISSION.md` into the Devpost submission portal.
3. [ ] **Final Confirmation**: Review all fields and click **"Submit Project"** before the October 23, 2026, deadline.

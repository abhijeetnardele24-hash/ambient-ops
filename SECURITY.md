# Security Policy

## Reporting Security Issues
If you discover a security vulnerability or security defect in AmbientOps, please report it privately by contacting the project maintainer at `abhinardele006@gmail.com`. Please do not create public GitHub issues for security vulnerabilities.

---

## Demo Limitations & Scope
* **Simulation Scope**: AmbientOps is designed as an incident response demonstration for the Amazon Developer Hackathon 2026. Connected entry cameras and motion sensors run in a **deterministic simulation mode** (`SIMULATED_ENTRY_DEVICE`) to prevent accidental unauthorized hardware actuation during judging.
* **AWS Credential Isolation**: The codebase contains **zero hardcoded credentials or API keys**. Live Bedrock connectivity relies entirely on standard AWS credential provider chains (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or IAM role assumptions). When credentials are absent, the application defaults to an offline deterministic emulator without attempting external network calls.
* **CORS & Network Policy**: Cross-Origin Resource Sharing (CORS) is restricted to configured origins via `CORS_ALLOWED_ORIGINS` (defaulting to local loopback addresses). Wildcard credentials (`*`) are explicitly disabled.
* **Security Headers**: Standard defense-in-depth headers are injected on all HTTP responses:
  - `Content-Security-Policy`: Restricts script and resource origins.
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: strict-origin-when-cross-origin`
* **DOM Injection Protection**: All client-side DOM rendering in `frontend/app.js` uses strict DOM node construction (`document.createElement`, `textContent`) rather than raw `innerHTML` string parsing, mitigating Cross-Site Scripting (XSS) risks.

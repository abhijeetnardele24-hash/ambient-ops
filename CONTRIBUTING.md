# Contributing to AmbientOps

Thank you for your interest in contributing to AmbientOps!

## Development Guidelines
1. **Model Context Protocol (MCP)**: Any new tool, prompt, or resource must adhere to the MCP specification v2025-11-25 or newer. Always update `backend/mcp_server.py` and add unit test coverage in `tests/test_mcp_interop.py`.
2. **Honest Simulation Labeling**: Do not label custom simulators as official OEM developer playgrounds unless verified against official SDKs. Keep all synthetic events typed as `is_simulated = True`.
3. **Calm Mission Control Design**: All frontend modifications must follow the technical-minimalist design system (off-white paper canvas, forest ink, structural borders, zero neon glow or glassmorphic blur).
4. **Automated Testing**: Ensure all tests pass with at least 90% measured test coverage (`pytest --cov=backend tests/`).
5. **No Secrets**: Never commit `.env` files, credentials, or private API keys. Use `.env.example` as a template.

## Running Tests Locally
```bash
pytest --cov=backend tests/ -v
```

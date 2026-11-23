# Codex validation results

Updated: 2026-11-22

## Local commands

| Command | Result |
|---|---|
| `pnpm typecheck` | PASS |
| `pnpm build` | PASS |
| `services/api/.venv/Scripts/python.exe -m ruff check src tests` | PASS |
| `services/api/.venv/Scripts/python.exe -m pytest -q` | PASS — 159 passed, 1 skipped, 1 deselected |
| `scripts/test-backup-integrity.ps1` | PASS — 8/8 cases |
| `scripts/verify-restored-db.ps1` | NOT RUN — refused because `SFI_RESTORE_DATABASE_URL` is unset |
| `cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml` | BLOCKED — MSVC `link.exe` not installed |
| `services/api/.venv/Scripts/python.exe -m pytest -q tests/test_postgres_precision.py tests/test_postgres_concurrency.py` | 2 skipped — no `SFI_TEST_POSTGRES_URL` |
| `services/api/.venv/Scripts/python.exe -m pytest -q tests/test_finance.py tests/test_credit.py tests/test_transfer_reversal.py` | PASS — 27 passed |

## Notes

- The API test suite uses the repository's default `not e2e` marker expression.
- One Starlette deprecation warning reports that the installed TestClient path will eventually prefer `httpx2`; this did not fail the suite.
- No test result is inferred from CI links or historical planning documents.
- The API virtual environment is generated/ignored and was repaired locally; no tracked dependency files were changed.
- Docker is unavailable locally, so the PostgreSQL precision workflow remains unverified in this environment.
- Rust dependencies resolved, but the Tauri compile cannot proceed without the Visual C++ build tools/linker.
- The invoice payment path now locks the invoice row with PostgreSQL `FOR UPDATE`; a dedicated concurrent-payment test is gated on `SFI_TEST_POSTGRES_URL` and is not locally executed without an isolated PostgreSQL database.
- No Neon MCP, GitHub connector, or local database secret was exposed to this session; no remote database operation was attempted.
- The affected financial routes pass the targeted regression suite after adding account and invoice row locks.
- After extending locks to both reversal endpoints, the targeted finance/credit/transfer suite remains green: 27 passed.
- Existing local packaging alternatives were checked without installation: only `x86_64-pc-windows-msvc` is installed for Rust; `gcc`, `clang`, `clang-cl`, `zig`, `makensis`, and `7z` are absent.
- PyInstaller sidecar build: PASS; `services/api/dist/sfi-api.exe`, 47,831,680 bytes, SHA-256 `B6DD139F73C0E283EDD2D4E1F868DB33AC2ADF2C045C2CCD64F84EC5FE6DD60F`.
- `scripts/test-desktop-sidecar.ps1 -ExecutablePath services/api/dist/sfi-api.exe`: PASS; two launches validated SQLite readiness, graceful shutdown, and DPAPI migration/reuse.
- Complete desktop `SFI.exe`: NOT PRODUCED; local Tauri linking needs unavailable `link.exe`.
- Final workflow validation: PyYAML `BaseLoader` parsed `.github/workflows/desktop.yml`; `git diff --check` passed. The workflow stages/uploads only the NSIS `SFI.exe` and reports size/SHA-256 in its Actions summary.
- Hosted Tauri build: NOT RUN; connected GitHub capability is read-only, so no remote commit or artifact is claimed.

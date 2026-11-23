# Codex completion matrix

Updated: 2026-11-22

| Area | Status | Evidence / limitation |
|---|---|---|
| API lint | COMPLETE AND VERIFIED | `services/api/.venv/Scripts/python.exe -m ruff check src tests` passed. |
| API automated tests | COMPLETE AND VERIFIED | `159 passed, 1 skipped, 1 deselected`; E2E marker excluded by project configuration. |
| Web typecheck | COMPLETE AND VERIFIED | `pnpm typecheck` passed. |
| Web production build | COMPLETE AND VERIFIED | `pnpm build` passed. |
| Backup integrity | COMPLETE AND VERIFIED | `scripts/test-backup-integrity.ps1` passed all 8 cases. |
| Restored database verification | BLOCKED | `scripts/verify-restored-db.ps1` requires an explicitly configured isolated `SFI_RESTORE_DATABASE_URL`; it was not supplied. |
| PostgreSQL concurrency and extreme Numeric round-trip | IMPLEMENTED, NOT VERIFIED | Invoice payment and account/transfer lock hardening are implemented; precision and concurrent invoice-payment tests run in the PostgreSQL CI service job, but the supplied Neon console is unauthenticated and no isolated test URL is available locally. |
| Desktop Windows installer | BLOCKED | Local `cargo check` failed before source compilation because MSVC `link.exe` is unavailable; physical install and runtime homologation also remain pending. |
| Security review | PARTIALLY IMPLEMENTED | Automated tests and Ruff pass; external review, infrastructure, LGPD decisions, and signing remain pending. |
| Release readiness | PARTIALLY IMPLEMENTED | Candidate build evidence exists in repository history, but physical homologation and external reconciliation remain open. |
| CI single-file staging | PREPARED, NOT EXECUTED | `.github/workflows/desktop.yml` builds NSIS only, stages `release/SFI.exe`, reports size/SHA-256 in the Actions summary, and uploads only the EXE; static YAML validation passed. |
| API sidecar self-contained executable | COMPLETE AND VERIFIED | PyInstaller output: `services/api/dist/sfi-api.exe`, 47,831,680 bytes, SHA-256 `B6DD139F73C0E283EDD2D4E1F868DB33AC2ADF2C045C2CCD64F84EC5FE6DD60F`; sidecar smoke test passed 2/2. |
| Single-file `SFI.exe` desktop artifact | BLOCKED | No existing non-MSVС compiler/packager is installed. Tauri requires the unavailable MSVC linker; the sidecar is not a complete desktop application. |

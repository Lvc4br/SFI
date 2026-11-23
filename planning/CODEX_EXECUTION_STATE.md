# Codex execution state

Updated: 2026-11-22

## Current checkpoint

- Working branch: `fix/backup-automation-dpapi-integrity`.
- HEAD: `a16e169` (`style(security): wrap DPAPI migration envelope assignment`).
- Existing user change preserved: `pnpm-workspace.yaml`.
- Repository is a GitHub checkout; Git commands require `-c safe.directory=E:/SFI/SFI` in this mounted environment.
- Backend virtual environment was recreated because its tracked-ignored `pyvenv.cfg` referenced the unavailable `C:\Python312` interpreter.

## Verified

- Web TypeScript typecheck: passed.
- Web production build: passed.
- API Ruff: passed.
- API tests: `159 passed, 1 skipped, 1 deselected`.

## Blocked or pending

- PostgreSQL-specific concurrency/precision validation was not run locally.
- Windows installer installation, offline lifecycle, DPAPI, OCR, backup/restore, upgrade, and uninstall require physical Windows homologation.
- GitHub PR/issue reconciliation is pending because the `gh` CLI is unavailable in this environment.

## Next actions

1. Run backup integrity and restored-database checks.
2. Inspect CI/Desktop workflows and release artifacts for stale or contradictory claims.
3. Fix only evidenced repository defects; do not modify the preserved workspace change.
4. Update the completion matrix and validation report with exact commands and outcomes.

## Latest checkpoint

- Backup integrity script: passed all 8 cases.
- Restored-database verifier: intentionally not run; it rejected the missing `SFI_RESTORE_DATABASE_URL`.
- Docker is unavailable locally, so the PostgreSQL service job cannot be reproduced here.
- Cargo/Rust are available, but the Windows Tauri installer requires the Windows CI environment and bundled sidecar/OCR assets.
- `cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml` reached compilation but failed because the MSVC linker `link.exe` is not installed.
- Fixed a PostgreSQL concurrency gap in invoice payments by locking the invoice row with `FOR UPDATE` before checking `paid_amount`.
- Fixed account lifecycle races by locking active accounts during archival, transaction creation, and transfer creation; transfer account locks use deterministic ordering.
- Extended the lifecycle guard to transaction and transfer reversals, which now lock their source/account rows and reject compensating entries after archival.
- Added `tests/test_postgres_concurrency.py`; it is gated on an isolated `SFI_TEST_POSTGRES_URL` and currently skips locally because no PostgreSQL URL is configured.
- Added [NEON_VALIDATION.md](../docs/NEON_VALIDATION.md) with secret-free isolation and restore procedures. No Neon connector or local credential is available in this environment.
- The supplied Neon console opened unauthenticated; no remote inspection or write was possible without an authorized session.

## Release artifact checkpoint

- No further MSVC, Visual Studio, Build Tools, Docker, container, or compiler installation attempts will be made.
- Existing local alternatives were checked: only the MSVC Rust target is installed; `gcc`, `clang`, `clang-cl`, `zig`, `makensis`, and `7z` are unavailable. `dotnet` is present but no equivalent desktop packaging path exists in this Tauri project.
- PyInstaller produced the self-contained API sidecar `services/api/dist/sfi-api.exe` (47,831,680 bytes; SHA-256 `B6DD139F73C0E283EDD2D4E1F868DB33AC2ADF2C045C2CCD64F84EC5FE6DD60F`). The sidecar smoke test passed twice, including SQLite readiness, graceful shutdown, and DPAPI migration/reuse.
- A complete portable `SFI.exe` was not produced: the current desktop shell is Tauri and cannot be linked with the only installed Rust target without MSVC; the API sidecar alone does not contain the frontend or desktop shell. Renaming it would be functionally incorrect.

## Encerramento local

- `.github/workflows/desktop.yml` now runs on `fix/**`, builds only the Tauri NSIS package, stages it as `release/SFI.exe`, reports size/SHA-256 in the Actions summary, and uploads only that executable.
- Workflow YAML parsing and `git diff --check` passed. The hosted workflow itself was not run; the available GitHub connector is read-only, local changes are uncommitted, and local HEAD (`a16e169`) differs from the remote branch head observed (`71b6590`). Therefore no complete desktop `SFI.exe` is claimed as produced.
- Neon and physical restore remain external validations; production Neon was not accessed. The already-built `sfi-api.exe` remains a separate, validated API sidecar.

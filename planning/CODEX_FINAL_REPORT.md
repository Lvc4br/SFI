# Codex final report

Status: in progress — baseline validation is complete; release work is not yet declared complete.

## Current evidence

- API: Ruff passed; 159 tests passed, 1 skipped, 1 deselected.
- Web: typecheck and production build passed.
- Backup integrity: 8/8 cases passed.
- Desktop Rust check: blocked by missing MSVC `link.exe`.
- Invoice payment concurrency: corrected with a PostgreSQL row lock; isolated concurrency coverage added to CI but not executed locally.
- Account archival, transaction posting, and transfer creation now serialize on active account rows.
- Transaction and transfer reversals now serialize on source/account rows and reject new compensating entries after archival.
- Existing planning documents identify physical Windows homologation, PostgreSQL concurrency/precision validation, and external operational/security decisions as remaining release gates.
- Neon integration remains unverified: the supplied console requires login and no local secret/MCP connector is available.
- The self-contained API sidecar was built and verified: 47,831,680 bytes, SHA-256 `B6DD139F73C0E283EDD2D4E1F868DB33AC2ADF2C045C2CCD64F84EC5FE6DD60F`; two smoke launches passed SQLite and DPAPI lifecycle checks.
- The requested complete single-file `SFI.exe` is not available. The current Tauri desktop build requires the absent MSVC linker, and no installed alternative compiler/packager can produce an equivalent artifact without changing the architecture.

## External validations not performed

- Hosted Windows build and runtime homologation: workflow is prepared, but the connected GitHub capability is read-only and local changes are uncommitted.
- Neon PostgreSQL and physical restore: pending external credentials/environment; production Neon was not accessed.


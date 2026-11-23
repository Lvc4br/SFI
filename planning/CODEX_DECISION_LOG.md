# Codex decision log

Updated: 2026-11-22

1. Preserve the existing modification in `pnpm-workspace.yaml`; it predates this execution and is outside the requested audit evidence.
2. Use per-command Git safe-directory configuration because the mounted filesystem does not expose normal ownership metadata; do not change global Git configuration.
3. Recreate only the ignored API virtual environment because its interpreter path was invalid; do not alter tracked source or data.
4. Treat physical Windows, PostgreSQL, GitHub PR/issue, and production/Neon operations as unverified or externally blocked unless an actual local command provides evidence.
5. Add `FOR UPDATE` to invoice payment reads: concurrent PostgreSQL payments with distinct idempotency keys must serialize on the invoice row before checking and updating `paid_amount`.
6. Document Neon validation as an isolated, secret-free procedure; do not attempt the operator's production branch without an authorized test connection.
7. Lock active account rows while archiving, posting transactions, or creating transfers; transfer locks are acquired in account-id order to avoid inconsistent concurrent decisions and reduce deadlock risk.
8. Serialize transfer and transaction reversals on their source records and account rows; reject new compensating entries after account archival.
9. Do not fabricate a single-file desktop artifact by renaming the API sidecar. With no installed non-MSVC compiler/packager and Tauri requiring `link.exe`, retain the verified sidecar as partial evidence and document the complete `SFI.exe` gate.
10. Close the release workflow locally by including `fix/**`, building NSIS only, uploading only `SFI.exe`, and publishing its size/SHA-256 in the Actions summary; do not claim the artifact exists until the hosted job actually runs.

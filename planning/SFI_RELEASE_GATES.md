# SFI — Release Gates & Test Strategy

## Gates

### Gate A — Financial correctness
- Decimal arithmetic and rounding reference tests.
- Balance, income/expense, transfer and reversal invariants.
- Duplicate request, retry, concurrency and failure recovery.
- Date/time, recurrence and currency cases.
- Database constraints and transaction atomicity.

### Gate B — Security
- Authentication and authorization tests for every protected resource.
- Cross-user isolation tests.
- Session rotation/revocation/reuse/concurrent refresh.
- Input validation, injection, XSS and CSRF/CORS/CSP checks.
- Secret/logging audit, dependency scanning and threat model.

### Gate C — Data reliability
- Backup integrity; restore into isolated environment.
- Failure/interruption tests during backup and restore.
- Migration tests from supported prior versions.
- Export completeness, import deduplication and reconciliation.

### Gate D — UX and accessibility
- Keyboard-only navigation, focus visibility and screen reader basics.
- Contrast, accessible labels and status announcements.
- Responsive layout and touch targets.
- Loading, empty, error, success and confirmation states.
- Usability task validation.

### Gate E — Desktop and distribution
- Install, launch, upgrade, downgrade policy, rollback and uninstall.
- Signature and provenance of installers.
- Offline and network-loss tests.
- Data directory permissions, backup/restore and crash recovery.
- Sidecar lifecycle and shutdown behavior.

### Gate F — Release
- All relevant gates pass.
- No open P0; no unresolved P1 in scope.
- CI and artifacts verified; documentation and release notes complete.
- Human release approval and rollback plan.

## Test layers
- Domain unit tests (fast, deterministic).
- Property-based invariant tests for money, transfers, reversals and dates.
- API integration tests with isolated database.
- Web component tests for forms, navigation, states and accessibility.
- E2E critical journeys.
- Desktop smoke tests and manual Windows homologation.
- Security/dependency/static analysis.
- Performance/load tests for identified bottlenecks.
- Migration/backup/restore tests.

## Evidence record
Record test name, command, commit SHA, environment, result, artifact/log reference, limitations and tester. Never report a test as executed based solely on its presence in source or CI badge.

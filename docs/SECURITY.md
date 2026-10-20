# Security boundaries

Implemented and tested:

- Passwords use Werkzeug scrypt hashes. No default runtime admin or hardcoded application secrets.
- Random 256-bit server-side session tokens stored only as SHA-256 digests in SQLite, with expiry and rotation on login/register/logout.
- HttpOnly + SameSite=Strict cookie; optional Secure flag for HTTPS deployments.
- Per-session CSRF token required on all writes, and cross-origin writes rejected.
- Parameterized SQL, role checks on every admin route, per-user cart/order scoping, server-enforced prices and quantities.
- Atomic orders with stock checks and owner-scoped idempotency keys; no arbitrary shell/code execution features.
- DOM text nodes rather than interpolated customer HTML; self-only content security policy; no third-party scripts/fonts/assets.
- Basic in-memory authentication rate limit (20 attempts per remote address per minute) and 32 KiB body limit.
- Loopback binding, debug disabled and localhost/127.0.0.1 allowed hosts by default.

Not a production security claim:

- SQLite/database and delivery-address text are not encrypted at rest; use synthetic data only. Do not host this demo publicly with real customer records.
- No verified email, password recovery, MFA, account deletion/export flow or fraud controls. Test-account credentials in tests are public examples, not shipped runtime accounts.
- Rate limits are process-local, not distributed; expired session rows are ignored, not periodically purged. Monitoring, backups, access audits, retention, migrations beyond schema v1 and managed deployment require further work.
- Flask's development server is not a production WSGI service. No public deployment, TLS/HTTPS end-to-end validation or penetration test was performed.
- Browser E2E was run in Chromium, not a complete Safari/Firefox/accessibility certification matrix.
- Stock and total consistency are protected in the database, but there are no payment, delivery, refund or cancellation integrations.
- Synthetic UI addresses should never be mistaken for a real dispatch instruction. The admin order statuses are simulated only.

If adapting the code, keep credentials, `.env` files, SQLite databases and personal data out of Git. Generate real deployment secrets outside source control if you later introduce services that need them.

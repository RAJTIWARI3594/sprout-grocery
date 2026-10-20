# Validation report

Validated on the Linux Computer during this build, using synthetic data only. These are local test results, not production security certification or evidence of a live grocery service.

## Results

| Check | Actual result |
| --- | --- |
| Backend/API suite, Python 3.10.21 | 42 passed |
| Backend/API suite, Python 3.14.7 | 42 passed |
| Frontend pure JavaScript helpers, Node built-in runner | 12 passed, 0 failed |
| Real full-stack browser checks, Chromium 140 / Playwright 1.55.0 | 14 passed, no uncaught page errors |

The Python version runs exercise the same 42 tests; they are not 84 distinct cases. The 14 browser checks are end-to-end scenario assertions, not additional unit tests. Test output is retained in `backend-python310.txt`, `backend-tests.txt`, `frontend-tests.txt` and `browser-results.json` alongside this file.

## What was exercised

Backend: catalog/filtering; invalid registrations and duplicate accounts; password hashes and role-injection rejection; login/session rotation, logout and expiry; cookies, CSRF, cross-origin guards and security headers; basket validation/persistence; server-authoritative order totals; idempotent submissions; stock rollback; concurrent checkout of the final unit; account-owned order privacy; unauthenticated/customer admin refusal; admin inventory and order progression; parameterized-input handling; auth throttling and request body limits.

Frontend helpers: integer-paise formatting, cart validation, quantity and malformed-storage handling.

Actual browser: catalog, categories and search; guest basket reload; register/login/logout; guest-to-account basket merge; order placement and history after reload; customer refusal at the admin API; admin price/stock update and next-stage order update; storefront sync; escaped stored markup; 390px mobile layout and dialog fit without horizontal page overflow. The harness starts a real local Flask server against a temporary SQLite database, then shuts it down and deletes it. It never changes your normal demo database.

## Screenshots from the running app

These are actual Chromium captures, not mockups. Product names, inventory, accounts and order/address examples are synthetic. The inventory was deliberately changed in the admin scenario, so screenshots may differ from the fresh seed prices.

- [Desktop storefront](screenshots/market-desktop.png)
- [Admin inventory](screenshots/admin-desktop.png)
- [390px mobile storefront](screenshots/market-mobile.png)

All three captures were visually inspected. The desktop storefront is captured before the admin update; the mobile capture follows the scenario and shows the updated price where visible.

## Reproduce

From the project root:

```bash
uv sync --frozen --group dev
uv run --python 3.10 pytest -q
node --test tests/core.test.mjs
uv run playwright install chromium
uv run python scripts/check_browser.py
```

For Linux browser dependencies, use `uv run playwright install-deps chromium` if needed. Browser screenshots and scenario results are refreshed by the last command. No credentials or external paid service are required.

## Boundaries

No real payments, delivery, emails or SMS are sent. No public deployment was created. Safari/Firefox, physical phones, Windows/macOS runtime, a full accessibility audit, penetration testing, load testing and production HTTPS were not tested. SQLite records are not encrypted at rest; use only invented data. The local admin is created explicitly through the CLI, not by a shipped runtime password. Test credentials are public fixtures isolated to test databases. See `SECURITY.md` and the README for remaining production requirements.

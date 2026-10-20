# API and data model

All writes use JSON, same-origin cookies and the `X-CSRF-Token` header. Obtain the token and session cookie using `GET /api/session`; refresh the token from successful registration/login/logout responses. Cookies are HttpOnly, SameSite=Strict and expire after 12 hours; `SPROUT_HTTPS=1` enables Secure cookies. Do not store passwords or session secrets in local storage.

| Endpoint | Purpose | Access |
|---|---|---|
| GET /api/session | `{user, csrf}` | Guest/session |
| GET /api/products?q=&category= | `{products: [...]}` | Public |
| POST /api/register | `{name,email,password}` → signed-in customer | Guest + CSRF |
| POST /api/login | `{email,password}` → rotated session | CSRF |
| POST /api/logout | `{}` → new guest session | CSRF |
| GET /api/cart | `{items:[{product_id,quantity}]}` | Signed in |
| PUT /api/cart | Replace entire validated basket | Signed in + CSRF |
| POST /api/orders | `{address,request_key}` from server basket | Signed in + CSRF |
| GET /api/orders | Only current user's immutable order snapshots | Signed in |
| GET /api/admin | Catalog and all demo orders | Admin |
| PATCH /api/admin/products/:id | `{price,stock}`, integer paise and integer count | Admin + CSRF |
| PATCH /api/admin/orders/:id | `{status}`, strictly next demo stage | Admin + CSRF |

Prices and totals are integer INR paise. Cart quantities are integers 1–20, with no duplicate product IDs and at most 50 items. Checkout has no delivery charge and no payment field because it is a simulation. The client cannot submit a trusted price or role. `request_key` is an owner-scoped idempotency token of 16–80 alphanumeric/underscore/hyphen characters (the UI generates a UUID), retained for retry until success or basket change. Retry with the same key returns the existing order and does not decrement stock twice.

Orders run inside `BEGIN IMMEDIATE`: stock verification, snapshot creation, stock decrement and basket clearing commit together, or all roll back. A test races two customers for the final unit and verifies exactly one succeeds. No promised shipping or bank transaction is triggered by changing demo status.

Schema version 1 is recorded in `migrations`. Tables: `users`, `sessions` (SHA-256 token digests, not raw cookies), `products`, `cart`, `orders`, `order_items`. `schema.sql` is the initial idempotent migration; future schema changes must use explicit versioned migrations rather than silently dropping existing data.

Errors normally return `{"error":"human-readable message"}` with 400 validation, 401 signed-out, 403 unauthorized/CSRF/origin, 404 missing, 409 conflict and 429 local rate-limit statuses. Request bodies are capped at 32 KiB. No CORS is enabled. The development server only accepts local hosts.

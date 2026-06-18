# ShopLine API (sample codebase)

A deliberately small Express + SQLite storefront API. It exists **to be explored
by the Developer Productivity Agent**, not to be a production service.

It contains three things worth tracing:

- **Password-reset flow** — `routes/auth.js` → `controllers/authController.js` →
  `services/tokenService.js` + `services/emailService.js` → `models/resetToken.js`.
- **Orders data model** — `db/schema.sql` (`users`, `orders`, `order_items`) +
  `models/order.js`.
- **Auth middleware** — `middleware/authMiddleware.js` (`requireAuth`, `requireRole`).

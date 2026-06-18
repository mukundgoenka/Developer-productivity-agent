-- ShopLine data model (authoritative).
-- The orders domain spans three tables: users (owner), orders (header) and
-- order_items (line items). reset_tokens backs the password-reset flow.

CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'customer',   -- 'customer' | 'admin'
  created_at    INTEGER NOT NULL
);

-- Order header: one row per order, owned by a user.
CREATE TABLE orders (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id),
  status      TEXT NOT NULL DEFAULT 'pending',  -- pending|paid|shipped|delivered|cancelled
  total_cents INTEGER NOT NULL,                 -- money stored in integer cents
  currency    TEXT NOT NULL DEFAULT 'USD',
  created_at  INTEGER NOT NULL
);

-- Order line items: many per order, each pointing at a product + a frozen price.
CREATE TABLE order_items (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  order_id         INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id       INTEGER NOT NULL,
  quantity         INTEGER NOT NULL CHECK (quantity > 0),
  unit_price_cents INTEGER NOT NULL                -- price captured at purchase time
);

-- Single-use, short-lived password reset tokens (only the hash is stored).
CREATE TABLE reset_tokens (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE,
  expires_at INTEGER NOT NULL,
  used_at    INTEGER
);

CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_reset_tokens_hash ON reset_tokens(token_hash);

// Order model. An order has many order_items and belongs to a user.
// See db/schema.sql for the authoritative data model.
const db = require('../db/connection');

async function findById(id) {
  const order = db.prepare('SELECT * FROM orders WHERE id = ?').get(id);
  if (!order) return null;
  const items = db.prepare('SELECT * FROM order_items WHERE order_id = ?').all(id);
  return toOrder(order, items);
}

async function listForUser(userId) {
  const rows = db
    .prepare('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC')
    .all(userId);
  return rows.map((r) => toOrder(r, []));
}

function toOrder(row, items) {
  return {
    id: row.id,
    userId: row.user_id,
    status: row.status, // pending | paid | shipped | delivered | cancelled
    totalCents: row.total_cents,
    currency: row.currency,
    createdAt: row.created_at,
    items: items.map((it) => ({
      id: it.id,
      productId: it.product_id,
      quantity: it.quantity,
      unitPriceCents: it.unit_price_cents,
    })),
  };
}

module.exports = { findById, listForUser };

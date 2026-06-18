// Order controller. Reads req.user (set by requireAuth) and enforces that a
// customer can only see their own orders.
const Order = require('../models/order');

async function listMyOrders(req, res) {
  const orders = await Order.listForUser(req.user.id);
  return res.json({ orders });
}

async function getOrder(req, res) {
  const order = await Order.findById(Number(req.params.id));
  if (!order) return res.status(404).json({ error: 'not_found' });
  if (order.userId !== req.user.id && req.user.role !== 'admin') {
    return res.status(403).json({ error: 'forbidden' });
  }
  return res.json({ order });
}

async function cancelOrder(req, res) {
  const order = await Order.findById(Number(req.params.id));
  if (!order) return res.status(404).json({ error: 'not_found' });
  // (sample) real impl would transition status -> 'cancelled' here
  return res.json({ ok: true, id: order.id, status: 'cancelled' });
}

module.exports = { listMyOrders, getOrder, cancelOrder };

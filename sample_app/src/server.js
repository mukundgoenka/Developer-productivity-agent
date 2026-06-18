// ShopLine API entry point.
// Wires global middleware and mounts the route modules. Start tracing a feature
// from the route that owns its URL prefix, then follow the imports downward.
const express = require('express');

const authRoutes = require('./routes/auth');
const orderRoutes = require('./routes/orders');
const { requireAuth } = require('./middleware/authMiddleware');

const app = express();
app.use(express.json());

// Public auth surface: login + the password-reset flow live here.
app.use('/auth', authRoutes);

// Everything under /orders requires a valid session (see authMiddleware).
app.use('/orders', requireAuth, orderRoutes);

app.get('/health', (_req, res) => res.json({ ok: true }));

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => console.log(`ShopLine API on :${PORT}`));
}

module.exports = app;

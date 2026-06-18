// Order routes. Mounted behind requireAuth in server.js, so every handler can
// rely on req.user being present.
const express = require('express');

const orderController = require('../controllers/orderController');
const { requireRole } = require('../middleware/authMiddleware');

const router = express.Router();

router.get('/', orderController.listMyOrders);
router.get('/:id', orderController.getOrder);

// Cancelling someone's order is an admin action.
router.post('/:id/cancel', requireRole('admin'), orderController.cancelOrder);

module.exports = router;

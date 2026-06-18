// Auth routes: login plus the two-step password-reset flow.
//   1. POST /auth/forgot-password  -> issues a reset token, emails a link
//   2. POST /auth/reset-password   -> consumes the token, sets a new password
const express = require('express');

const authController = require('../controllers/authController');

const router = express.Router();

router.post('/login', authController.login);

// Step 1 of password reset: user submits their email.
router.post('/forgot-password', authController.requestPasswordReset);

// Step 2 of password reset: user submits the emailed token + a new password.
router.post('/reset-password', authController.resetPassword);

module.exports = router;

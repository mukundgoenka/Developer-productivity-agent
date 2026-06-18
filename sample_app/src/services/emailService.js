// Email service. In this sample it just logs the message; the shape matters for
// tracing the password-reset flow (where the raw token becomes a clickable link).
const APP_URL = process.env.APP_URL || 'https://shopline.example';

async function sendPasswordResetEmail(toEmail, rawToken) {
  const resetLink = `${APP_URL}/reset?token=${rawToken}`;
  // Real impl would call an email provider here.
  console.log(`[email] to=${toEmail} subject="Reset your password" link=${resetLink}`);
  return { delivered: true };
}

module.exports = { sendPasswordResetEmail };

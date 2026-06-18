// Auth middleware. Two guards:
//   requireAuth  - rejects anything without a valid Bearer JWT, attaches req.user
//   requireRole  - factory that additionally enforces a role (e.g. 'admin')
// This is the file Prompt 3 asks a subagent to deep-dive.
const jwt = require('jsonwebtoken');

const User = require('../models/user');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret';

async function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const [scheme, token] = header.split(' ');
  if (scheme !== 'Bearer' || !token) {
    return res.status(401).json({ error: 'missing_bearer_token' });
  }
  let payload;
  try {
    payload = jwt.verify(token, JWT_SECRET); // throws on bad/expired token
  } catch (err) {
    return res.status(401).json({ error: 'invalid_token' });
  }
  const user = await User.findById(payload.sub);
  if (!user) {
    return res.status(401).json({ error: 'user_not_found' });
  }
  req.user = user; // downstream handlers read req.user
  next();
}

// Usage: router.delete('/:id', requireRole('admin'), handler)
function requireRole(role) {
  return function (req, res, next) {
    if (!req.user || req.user.role !== role) {
      return res.status(403).json({ error: 'forbidden' });
    }
    next();
  };
}

module.exports = { requireAuth, requireRole };

// SQLite connection. Loads the schema on first run. (Sample app — not the focus
// of exploration, but imported by every model.)
const path = require('path');
const Database = require('better-sqlite3');

const db = new Database(path.join(__dirname, 'shopline.db'));
db.pragma('journal_mode = WAL');

module.exports = db;

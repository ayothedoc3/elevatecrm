const Database = require('better-sqlite3');
const db = new Database('features.db', { readonly: true });
const row = db.prepare('SELECT id, category, name, description, steps, passes, in_progress FROM features WHERE id = ?').get(211);
if (row) {
  console.log(JSON.stringify(row, null, 2));
} else {
  console.log('Feature not found');
}
db.close();

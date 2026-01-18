const Database = require('better-sqlite3');
const db = new Database('C:/Users/ayoth/Downloads/elevatecrm/elevatecrm/features.db');
const row = db.prepare('SELECT * FROM features WHERE id = 119').get();
console.log(JSON.stringify(row, null, 2));
db.close();

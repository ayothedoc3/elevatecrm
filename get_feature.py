import sqlite3
import json

conn = sqlite3.connect('features.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute('SELECT * FROM features WHERE id = 267')
row = c.fetchone()
if row:
    print(json.dumps(dict(row), indent=2))
else:
    print("Feature 267 not found")
conn.close()

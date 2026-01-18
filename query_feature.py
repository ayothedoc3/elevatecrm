import sqlite3
import json

conn = sqlite3.connect(r'C:\Users\ayoth\Downloads\elevatecrm\elevatecrm\features.db')
cursor = conn.cursor()
cursor.execute('SELECT id, category, name, description, steps, passes, in_progress FROM features WHERE id = 118')
row = cursor.fetchone()

if row:
    print("=" * 60)
    print(f"ID: {row[0]}")
    print(f"Category: {row[1]}")
    print(f"Name: {row[2]}")
    print(f"Description: {row[3]}")
    print(f"Steps: {row[4]}")
    print(f"Passes: {row[5]}")
    print(f"In Progress: {row[6]}")
    print("=" * 60)
else:
    print("Feature #118 not found")

conn.close()

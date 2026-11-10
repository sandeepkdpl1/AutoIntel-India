
import sqlite3

conn = sqlite3.connect("database/autointel.db")

print("Database integrity:")
print(conn.execute("PRAGMA integrity_check").fetchone()[0])

print("\nDatabase tables:")

tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

for table in tables:
    print(table[0])

conn.close()

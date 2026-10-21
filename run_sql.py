"""Interactive SQL prompt for the demo's SQLite database."""
import sqlite3
from pathlib import Path
from getpass import getpass
import hashlib
import hmac

root = Path(__file__).resolve().parent
db_path = root / "amazon_store.db"
if not db_path.exists():
    print("Database not found. Start the app once with: python app.py")
    raise SystemExit(1)
db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
db.row_factory = sqlite3.Row
db.execute("PRAGMA query_only = ON")
email = input("Analyst email: ").strip().lower()
password = getpass("Analyst password: ")
user = db.execute("SELECT role,password_hash FROM profiles WHERE email=?", (email,)).fetchone()
valid = False
if user and user["role"] == "analyst":
    try:
        salt_hex, digest_hex = user["password_hash"].split(":", 1)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 180_000).hex()
        valid = hmac.compare_digest(digest, digest_hex)
    except ValueError:
        valid = False
if not valid:
    print("Analyst sign-in failed. Read-only SQL access is for the analyst account.")
    db.close()
    raise SystemExit(1)
print("Read-only DBMS SQL prompt. Enter a query; .quit exits.")
print("Open sql/queries.sql and paste a query here.")
while True:
    try:
        statement = input("SQL> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        break
    if statement.lower() in {".quit", ".exit", "quit", "exit"}:
        break
    if not statement:
        continue
    try:
        cur = db.execute(statement)
        if cur.description:
            rows = cur.fetchall()
            if rows:
                headers = rows[0].keys()
                widths = {h: max(len(h), *(len(str(row[h])) for row in rows)) for h in headers}
                print(" | ".join(h.ljust(widths[h]) for h in headers))
                print("-+-".join("-" * widths[h] for h in headers))
                for row in rows:
                    print(" | ".join(str(row[h]).ljust(widths[h]) for h in headers))
            else:
                print("(0 rows)")
        else:
            print(f"{cur.rowcount} row(s) affected")
    except sqlite3.Error as exc:
        print(f"SQL error: {exc}")
db.close()

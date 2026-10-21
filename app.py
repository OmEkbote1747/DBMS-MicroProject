"""Small educational storefront backed by SQLite and Python's standard library."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "amazon_store.db"
HOST, PORT = "127.0.0.1", int(os.environ.get("PORT", "8000"))
SCHEMA = (ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
SESSIONS: dict[str, int] = {}
SESSIONS_LOCK = threading.Lock()


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return f"{salt.hex()}:{digest.hex()}"


def password_matches(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 180_000)
        return hmac.compare_digest(actual.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize() -> None:
    with connect() as db:
        db.executescript(SCHEMA)
        for name, email, password, role in [
            ("Maya Customer", "maya@example.test", "customer123", "customer"),
            ("Ivan Inventory", "ivan@example.test", "stock123", "inventory"),
            ("Sam Analyst", "sam@example.test", "analytics123", "analyst"),
            ("Ari Admin", "admin@example.test", "admin123", "admin"),
        ]:
            existing = db.execute("SELECT id FROM profiles WHERE email=?", (email,)).fetchone()
            if not existing:
                db.execute("INSERT INTO profiles(full_name,email,password_hash,role) VALUES(?,?,?,?)",
                           (name, email, password_hash(password), role))
        categories = [
            ("Electronics", "Everyday electronic devices"),
            ("Home", "Useful products for the home"),
            ("Books", "Reading and learning"),
            ("Computers", "Laptops, storage, and computer accessories"),
            ("Kitchen & Dining", "Cookware and everyday kitchen equipment"),
            ("Sports & Outdoors", "Fitness, travel, and outdoor equipment"),
            ("Beauty & Personal Care", "Personal care and grooming products"),
            ("Toys & Games", "Toys, games, and creative activities"),
            ("Office Supplies", "Study and office essentials"),
            ("Fashion", "Clothing, bags, and accessories"),
            ("Grocery", "Packaged pantry and beverage items"),
        ]
        for row in categories:
            db.execute("INSERT OR IGNORE INTO categories(name,description) VALUES(?,?)", row)
        products = [
            ("Electronics", "Wireless Headphones", "Bluetooth over-ear headphones", 249900, 18),
            ("Electronics", "USB-C Charger", "Fast charging wall adapter", 89900, 42),
            ("Home", "Insulated Bottle", "750 ml stainless steel bottle", 69900, 25),
            ("Books", "Database Systems Basics", "Introductory textbook for database learners", 59900, 12),
            ("Home", "Desk Lamp", "Adjustable LED study lamp", 129900, 8),
            ("Electronics", "Bluetooth Speaker", "Portable speaker with wireless audio", 179900, 21),
            ("Electronics", "Wireless Mouse", "Ergonomic wireless mouse with USB receiver", 79900, 37),
            ("Electronics", "Mechanical Keyboard", "Compact keyboard with tactile switches", 329900, 14),
            ("Electronics", "1080p Webcam", "USB webcam for calls and classes", 219900, 11),
            ("Electronics", "Noise Cancelling Earbuds", "True wireless earbuds with charging case", 399900, 16),
            ("Computers", "Everyday Laptop 14", "14 inch laptop for study and office work", 5499900, 7),
            ("Computers", "Portable SSD 1TB", "External solid state drive with USB-C", 699900, 13),
            ("Computers", "USB-C Hub 7-in-1", "Multiport hub with HDMI and card reader", 249900, 19),
            ("Computers", "Laptop Stand", "Foldable aluminium stand for laptops", 159900, 23),
            ("Computers", "27-inch Monitor", "Full HD IPS monitor for desk setups", 1199900, 6),
            ("Home", "Cotton Bedsheet Set", "Double bed sheet with two pillow covers", 139900, 20),
            ("Home", "Memory Foam Pillow", "Supportive pillow with washable cover", 99900, 17),
            ("Home", "Storage Basket Set", "Set of three woven household baskets", 84900, 29),
            ("Home", "LED Bulb 9W Pack", "Pack of four energy-saving LED bulbs", 49900, 56),
            ("Home", "Wall Clock", "Silent sweep clock for home or office", 74900, 15),
            ("Kitchen & Dining", "Nonstick Frying Pan", "26 cm everyday frying pan", 119900, 18),
            ("Kitchen & Dining", "Electric Kettle 1.5L", "Stainless steel kettle with auto shut-off", 169900, 12),
            ("Kitchen & Dining", "Glass Food Container Set", "Set of five stackable storage containers", 109900, 24),
            ("Kitchen & Dining", "Digital Kitchen Scale", "Compact scale for cooking and baking", 89900, 9),
            ("Kitchen & Dining", "Ceramic Dinner Set", "Six-piece dinner set for everyday meals", 199900, 8),
            ("Books", "The Art of Clear Thinking", "Practical guide to reasoning and decisions", 39900, 31),
            ("Books", "Python for Beginners", "Introductory programming workbook", 54900, 22),
            ("Books", "The World Atlas", "Illustrated reference atlas for students", 79900, 10),
            ("Books", "Classic Short Stories", "Collection of public-domain short fiction", 29900, 28),
            ("Books", "Project Planning Handbook", "A practical guide to planning small projects", 45900, 14),
            ("Sports & Outdoors", "Yoga Mat 6mm", "Non-slip exercise mat with carry strap", 89900, 26),
            ("Sports & Outdoors", "Resistance Band Set", "Five bands for home strength training", 69900, 32),
            ("Sports & Outdoors", "Trekking Backpack 30L", "Day pack with padded straps and rain cover", 189900, 11),
            ("Sports & Outdoors", "Stainless Steel Shaker", "Leak-resistant bottle for fitness drinks", 59900, 18),
            ("Sports & Outdoors", "LED Camping Lantern", "Rechargeable lantern with adjustable brightness", 129900, 7),
            ("Beauty & Personal Care", "Ceramic Hair Dryer", "Compact hair dryer with two heat settings", 149900, 13),
            ("Beauty & Personal Care", "Electric Toothbrush", "Rechargeable brush with two cleaning modes", 179900, 10),
            ("Beauty & Personal Care", "Daily Moisturiser 200ml", "Lightweight, fragrance-free skin moisturiser", 34900, 34),
            ("Beauty & Personal Care", "Beard Grooming Kit", "Trimmer and comb set for home grooming", 99900, 8),
            ("Toys & Games", "Wooden Building Blocks", "Colourful block set for creative play", 79900, 16),
            ("Toys & Games", "Family Puzzle 1000 Pieces", "Landscape jigsaw puzzle for family game time", 49900, 20),
            ("Toys & Games", "Strategy Board Game", "Turn-based strategy game for two to four players", 129900, 5),
            ("Office Supplies", "A5 Notebook 3-Pack", "Ruled notebooks for class and daily notes", 24900, 60),
            ("Office Supplies", "Gel Pen Set", "Pack of ten black ink gel pens", 19900, 72),
            ("Office Supplies", "Desk Organiser", "Multi-compartment organiser for stationery", 69900, 17),
            ("Office Supplies", "Whiteboard 60x90cm", "Wall-mounted board with marker and eraser", 159900, 4),
            ("Fashion", "Canvas Backpack", "Lightweight backpack with laptop sleeve", 119900, 15),
            ("Fashion", "Everyday Cotton T-Shirt", "Regular fit cotton T-shirt in navy", 49900, 33),
            ("Fashion", "Travel Wallet", "Compact wallet with passport and card slots", 79900, 12),
            ("Grocery", "Arabica Coffee 250g", "Medium roast ground coffee for filter brewing", 32900, 25),
            ("Grocery", "Green Tea 100 Bags", "Everyday green tea bags in a resealable pack", 27900, 40),
            ("Grocery", "Mixed Nuts 500g", "Roasted mixed nuts in a resealable pouch", 49900, 18),
        ]
        for category, name, description, price, stock in products:
            cat = db.execute("SELECT id FROM categories WHERE name=?", (category,)).fetchone()
            exists = db.execute("SELECT 1 FROM products WHERE name=?", (name,)).fetchone()
            if not exists:
                db.execute("INSERT INTO products(category_id,name,description,price_paise,stock_quantity) VALUES(?,?,?,?,?)",
                           (cat["id"], name, description, price, stock))

        customer = db.execute("SELECT id FROM profiles WHERE email='maya@example.test'").fetchone()
        if customer and not db.execute("SELECT 1 FROM orders WHERE customer_id=? LIMIT 1", (customer["id"],)).fetchone():
            demo_orders = [
                ("delivered", "2026-10-02 10:15:00", [("Wireless Headphones", 1), ("USB-C Charger", 1)]),
                ("delivered", "2026-10-05 14:22:00", [("A5 Notebook 3-Pack", 2), ("Gel Pen Set", 1)]),
                ("shipped", "2026-10-09 09:40:00", [("Portable SSD 1TB", 1), ("USB-C Hub 7-in-1", 1)]),
                ("packed", "2026-10-13 17:05:00", [("Yoga Mat 6mm", 1), ("Resistance Band Set", 1)]),
                ("placed", "2026-10-18 11:30:00", [("Electric Kettle 1.5L", 1), ("Glass Food Container Set", 1)]),
                ("delivered", "2026-10-20 16:10:00", [("Python for Beginners", 1), ("Desk Organiser", 1)]),
            ]
            for status, created_at, lines in demo_orders:
                selected = []
                for product_name, quantity in lines:
                    product = db.execute("SELECT id,name,price_paise,stock_quantity FROM products WHERE name=?", (product_name,)).fetchone()
                    if product and product["stock_quantity"] >= quantity:
                        selected.append((product, quantity))
                if len(selected) != len(lines):
                    continue
                total = sum(product["price_paise"] * quantity for product, quantity in selected)
                order_id = db.execute("INSERT INTO orders(customer_id,status,total_paise,created_at) VALUES(?,?,?,?)",
                                      (customer["id"], status, total, created_at)).lastrowid
                for product, quantity in selected:
                    db.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price_paise) VALUES(?,?,?,?)",
                               (order_id, product["id"], quantity, product["price_paise"]))
                    db.execute("UPDATE products SET stock_quantity=stock_quantity-? WHERE id=?",
                               (quantity, product["id"]))


def as_money(paise: int) -> str:
    return f"₹{paise / 100:,.2f}"


class Handler(BaseHTTPRequestHandler):
    server_version = "StoreDemo/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.address_string(), fmt % args))

    def send_json(self, payload, status=200, cookie=None):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        size = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
        return json.loads(self.rfile.read(size) or b"{}")

    def user(self):
        raw = self.headers.get("Cookie", "")
        jar = cookies.SimpleCookie()
        try:
            jar.load(raw)
        except cookies.CookieError:
            return None
        sid = jar.get("store_session")
        if not sid:
            return None
        with SESSIONS_LOCK:
            user_id = SESSIONS.get(sid.value)
        if not user_id:
            return None
        with connect() as db:
            row = db.execute("SELECT id,full_name,email,role FROM profiles WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def require(self, roles):
        current = self.user()
        if not current:
            self.send_json({"error": "Please sign in first."}, 401)
            return None
        if current["role"] not in roles:
            self.send_json({"error": "Your account role cannot perform this action."}, 403)
            return None
        return current

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/products":
            with connect() as db:
                rows = db.execute("SELECT * FROM product_catalogue ORDER BY category,name").fetchall()
            self.send_json([dict(row) for row in rows])
        elif path == "/api/me":
            self.send_json({"user": self.user()})
        elif path == "/api/orders":
            current = self.require(("customer", "inventory", "analyst", "admin"))
            if not current:
                return
            with connect() as db:
                sql = """SELECT o.id,o.customer_id,p.full_name AS customer,o.status,o.total_paise,o.created_at
                         FROM orders o JOIN profiles p ON p.id=o.customer_id"""
                args = ()
                if current["role"] == "customer":
                    sql += " WHERE o.customer_id=?"
                    args = (current["id"],)
                sql += " ORDER BY o.created_at DESC,o.id DESC"
                orders = [dict(r) for r in db.execute(sql, args).fetchall()]
                for order in orders:
                    order["items"] = [dict(r) for r in db.execute(
                        """SELECT pr.name,oi.quantity,oi.unit_price_paise
                           FROM order_items oi JOIN products pr ON pr.id=oi.product_id WHERE oi.order_id=?""",
                        (order["id"],)).fetchall()]
            self.send_json(orders)
        elif path == "/" or path.startswith("/static/"):
            filename = "index.html" if path == "/" else Path(path.removeprefix("/static/")).name
            file = ROOT / "static" / filename
            if not file.is_file():
                self.send_error(404)
                return
            data = file.read_bytes()
            kind = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}.get(file.suffix, "application/octet-stream")
            self.send_response(200)
            self.send_header("Content-Type", f"{kind}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self.body()
        except (ValueError, json.JSONDecodeError):
            self.send_json({"error": "Invalid JSON request."}, 400)
            return
        if path == "/api/login":
            email, password = str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
            with connect() as db:
                row = db.execute("SELECT * FROM profiles WHERE email=?", (email,)).fetchone()
            if not row or not password_matches(password, row["password_hash"]):
                self.send_json({"error": "Email or password is incorrect."}, 401)
                return
            sid = secrets.token_urlsafe(32)
            with SESSIONS_LOCK:
                SESSIONS[sid] = row["id"]
            user = {"id": row["id"], "full_name": row["full_name"], "email": row["email"], "role": row["role"]}
            self.send_json({"user": user}, cookie=f"store_session={sid}; HttpOnly; SameSite=Strict; Path=/")
        elif path == "/api/logout":
            jar = cookies.SimpleCookie()
            try:
                jar.load(self.headers.get("Cookie", ""))
                sid = jar.get("store_session")
                if sid:
                    with SESSIONS_LOCK:
                        SESSIONS.pop(sid.value, None)
            except cookies.CookieError:
                pass
            self.send_json({"ok": True}, cookie="store_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
        elif path == "/api/orders":
            current = self.require(("customer",))
            if not current:
                return
            items = data.get("items", [])
            if not isinstance(items, list) or not items:
                self.send_json({"error": "Add at least one product to the cart."}, 400)
                return
            quantities = {}
            try:
                for item in items:
                    pid, qty = int(item["product_id"]), int(item["quantity"])
                    if qty < 1 or qty > 99:
                        raise ValueError
                    quantities[pid] = quantities.get(pid, 0) + qty
            except (KeyError, TypeError, ValueError):
                self.send_json({"error": "Product quantities are invalid."}, 400)
                return
            try:
                with connect() as db:
                    rows = {}
                    for pid, qty in quantities.items():
                        product = db.execute("SELECT id,name,price_paise,stock_quantity,is_active FROM products WHERE id=?", (pid,)).fetchone()
                        if not product or not product["is_active"]:
                            raise ValueError("A selected product is unavailable.")
                        if product["stock_quantity"] < qty:
                            raise ValueError(f"Not enough stock for {product['name']}.")
                        rows[pid] = (product, qty)
                    total = sum(product["price_paise"] * qty for product, qty in rows.values())
                    cur = db.execute("INSERT INTO orders(customer_id,status,total_paise) VALUES(?,'placed',?)", (current["id"], total))
                    order_id = cur.lastrowid
                    for pid, (product, qty) in rows.items():
                        db.execute("INSERT INTO order_items(order_id,product_id,quantity,unit_price_paise) VALUES(?,?,?,?)",
                                   (order_id, pid, qty, product["price_paise"]))
                        db.execute("UPDATE products SET stock_quantity=stock_quantity-? WHERE id=?", (qty, pid))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, 409)
                return
            self.send_json({"ok": True, "order_id": order_id, "total_paise": total}, 201)
        elif path == "/api/products":
            current = self.require(("admin",))
            if not current:
                return
            try:
                name = str(data["name"]).strip()
                category = str(data["category"]).strip()
                description = str(data.get("description", "")).strip()
                price_paise = int(round(float(data["price_rupees"]) * 100))
                stock = int(data["stock_quantity"])
                if not name or not category or price_paise < 0 or stock < 0:
                    raise ValueError
                with connect() as db:
                    db.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (category,))
                    cid = db.execute("SELECT id FROM categories WHERE name=?", (category,)).fetchone()["id"]
                    db.execute("INSERT INTO products(category_id,name,description,price_paise,stock_quantity) VALUES(?,?,?,?,?)",
                               (cid,name,description,price_paise,stock))
            except (KeyError, TypeError, ValueError, sqlite3.IntegrityError):
                self.send_json({"error": "Enter a unique name, category, non-negative price, and stock."}, 400)
                return
            self.send_json({"ok": True}, 201)
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_PATCH(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/products/") or not path.endswith("/stock"):
            self.send_json({"error": "Not found"}, 404)
            return
        current = self.require(("inventory", "admin"))
        if not current:
            return
        try:
            product_id = int(path.split("/")[3])
            stock = int(self.body()["stock_quantity"])
            if stock < 0:
                raise ValueError
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            self.send_json({"error": "Enter a valid non-negative stock quantity."}, 400)
            return
        with connect() as db:
            cur = db.execute("UPDATE products SET stock_quantity=? WHERE id=?", (stock, product_id))
            if cur.rowcount == 0:
                self.send_json({"error": "Product not found."}, 404)
                return
        self.send_json({"ok": True})


if __name__ == "__main__":
    initialize()
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as exc:
        print(f"Could not start the demo server on http://{HOST}:{PORT}: {exc}")
        print("Close any other process using this port, then try again.")
        raise SystemExit(1)

    print(f"Amazon-style DBMS demo running at http://{HOST}:{PORT}", flush=True)
    print("Demo accounts are listed in README.md. Press Ctrl+C to stop.", flush=True)
    server.serve_forever()

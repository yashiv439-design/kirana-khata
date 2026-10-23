"""SQLite ledger: all the real data work happens here."""
import os
import sqlite3
from contextlib import contextmanager
from urllib.parse import quote

DB_PATH = os.environ.get("KHATA_DB", os.path.join(os.path.dirname(__file__), "khata.db"))
SHOP_NAME = os.environ.get("SHOP_NAME", "Sharma Kirana Store")


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE COLLATE NOCASE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                amount REAL NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('udhaar','payment')),
                note TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE TABLE IF NOT EXISTS aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                alias TEXT UNIQUE COLLATE NOCASE NOT NULL
            );
            """
        )


def clean_name(name: str) -> str:
    return " ".join(name.strip().split()).title()


def _find_customer(c, name):
    """Exact name, then nickname (alias), then 'contains' match if it is unique."""
    row = c.execute("SELECT * FROM customers WHERE name = ?", (clean_name(name),)).fetchone()
    if row:
        return row
    row = c.execute(
        "SELECT c.* FROM aliases a JOIN customers c ON c.id = a.customer_id WHERE a.alias = ?",
        (clean_name(name),),
    ).fetchone()
    if row:
        return row
    rows = c.execute("SELECT * FROM customers WHERE name LIKE ?", (f"%{name.strip()}%",)).fetchall()
    return rows[0] if len(rows) == 1 else None


def _balance(c, customer_id):
    r = c.execute(
        """SELECT COALESCE(SUM(CASE WHEN kind='udhaar' THEN amount ELSE -amount END),0) AS b
           FROM transactions WHERE customer_id=?""",
        (customer_id,),
    ).fetchone()
    return round(r["b"], 2)


def add_udhaar(name, amount, note=""):
    if amount <= 0:
        return {"ok": False, "message": "Amount 0 se zyada hona chahiye."}
    with conn() as c:
        cust = _find_customer(c, name)
        if not cust:
            c.execute("INSERT INTO customers(name) VALUES (?)", (clean_name(name),))
            cust = c.execute("SELECT * FROM customers WHERE name=?", (clean_name(name),)).fetchone()
        c.execute(
            "INSERT INTO transactions(customer_id, amount, kind, note) VALUES (?,?,?,?)",
            (cust["id"], amount, "udhaar", note),
        )
        bal = _balance(c, cust["id"])
        return {
            "ok": True,
            "customer": cust["name"],
            "balance": bal,
            "message": f"{cust['name']} ke naam ₹{amount:g} ka udhaar likh diya. Ab kul baaki: ₹{bal:g}.",
        }


def record_payment(name, amount, note=""):
    if amount <= 0:
        return {"ok": False, "message": "Amount 0 se zyada hona chahiye."}
    with conn() as c:
        cust = _find_customer(c, name)
        if not cust:
            return {"ok": False, "message": f"'{name}' naam ka koi customer nahi mila."}
        c.execute(
            "INSERT INTO transactions(customer_id, amount, kind, note) VALUES (?,?,?,?)",
            (cust["id"], amount, "payment", note),
        )
        bal = _balance(c, cust["id"])
        extra = " Sab hisaab clear!" if bal == 0 else ""
        return {
            "ok": True,
            "customer": cust["name"],
            "balance": bal,
            "message": f"{cust['name']} se ₹{amount:g} mil gaye. Ab baaki: ₹{bal:g}.{extra}",
        }


def add_alias(name, alias):
    """Teach the ledger a nickname, e.g. 'chhota bhaiya' -> Ramesh."""
    alias = clean_name(alias)
    if not alias:
        return {"ok": False, "message": "Nickname khaali nahi ho sakta."}
    with conn() as c:
        cust = _find_customer(c, name)
        if not cust:
            return {"ok": False, "message": f"'{name}' naam ka koi customer nahi mila. Pehle unka udhaar likho."}
        taken = c.execute("SELECT 1 FROM customers WHERE name = ?", (alias,)).fetchone()
        if taken:
            return {"ok": False, "message": f"'{alias}' pehle se ek customer ka naam hai."}
        try:
            c.execute("INSERT INTO aliases(customer_id, alias) VALUES (?,?)", (cust["id"], alias))
        except sqlite3.IntegrityError:
            return {"ok": False, "message": f"'{alias}' pehle se kisi aur ka nickname hai."}
        return {"ok": True, "customer": cust["name"], "alias": alias,
                "message": f"Theek hai. Ab '{alias}' matlab {cust['name']}."}


def get_balance(name=None):
    with conn() as c:
        if name:
            cust = _find_customer(c, name)
            if not cust:
                return {"ok": False, "message": f"'{name}' naam ka koi customer nahi mila."}
            bal = _balance(c, cust["id"])
            return {"ok": True, "customer": cust["name"], "balance": bal,
                    "message": f"{cust['name']} ka ₹{bal:g} baaki hai."}
        total = 0.0
        for r in c.execute("SELECT id FROM customers").fetchall():
            b = _balance(c, r["id"])
            if b > 0:
                total += b
        return {"ok": True, "balance": round(total, 2),
                "message": f"Aaj ki date tak kul ₹{total:g} udhaar baaki hai."}


def top_defaulters(limit=3):
    with conn() as c:
        rows = []
        for r in c.execute("SELECT id, name FROM customers").fetchall():
            b = _balance(c, r["id"])
            if b > 0:
                rows.append({"name": r["name"], "balance": b})
        rows.sort(key=lambda x: x["balance"], reverse=True)
        rows = rows[:limit]
        if not rows:
            return {"ok": True, "top": [], "message": "Kisi ka udhaar baaki nahi hai. Badhiya!"}
        parts = ", ".join(f"{x['name']} (₹{x['balance']:g})" for x in rows)
        return {"ok": True, "top": rows, "message": f"Sabse zyada paisa lena hai: {parts}."}


def draft_reminder(name):
    with conn() as c:
        cust = _find_customer(c, name)
        if not cust:
            return {"ok": False, "message": f"'{name}' naam ka koi customer nahi mila."}
        bal = _balance(c, cust["id"])
        if bal <= 0:
            return {"ok": True, "customer": cust["name"], "draft": "",
                    "message": f"{cust['name']} ka koi udhaar baaki nahi hai, reminder ki zaroorat nahi."}
        draft = (f"Namaste {cust['name']} ji 🙏 {SHOP_NAME} se yaad dila rahe hain ki aapka "
                 f"₹{bal:g} ka udhaar baaki hai. Jab suvidha ho, chuka dijiyega. Dhanyavaad!")
        return {"ok": True, "customer": cust["name"], "balance": bal, "draft": draft,
                "whatsapp_link": "https://wa.me/?text=" + quote(draft),
                "message": f"{cust['name']} ke liye reminder taiyaar hai."}


def snapshot():
    """Everything the dashboard needs in one call."""
    with conn() as c:
        customers = []
        for r in c.execute("SELECT id, name FROM customers").fetchall():
            al = [a["alias"] for a in c.execute("SELECT alias FROM aliases WHERE customer_id=?", (r["id"],))]
            customers.append({"name": r["name"], "balance": _balance(c, r["id"]), "aliases": al})
        customers.sort(key=lambda x: x["balance"], reverse=True)
        recent = [dict(r) for r in c.execute(
            """SELECT c.name, t.amount, t.kind, t.created_at FROM transactions t
               JOIN customers c ON c.id=t.customer_id ORDER BY t.id DESC LIMIT 8""")]
        total = round(sum(x["balance"] for x in customers if x["balance"] > 0), 2)
        return {"shop": SHOP_NAME, "total_baaki": total, "customers": customers, "recent": recent}

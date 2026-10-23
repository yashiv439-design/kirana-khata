"""Demo data (all names are made up)."""
import db

db.init_db()
with db.conn() as c:
    c.execute("DELETE FROM aliases")
    c.execute("DELETE FROM transactions")
    c.execute("DELETE FROM customers")
db.add_udhaar("Ramesh", 450, "monthly saman")
db.add_udhaar("Sharma Ji", 1200, "ration")
db.add_udhaar("Geeta", 300, "doodh")
db.add_udhaar("Pappu", 2100, "ration + tel")
db.record_payment("Geeta", 100)
db.add_alias("Pappu", "Chhota Bhaiya")
db.add_alias("Geeta", "Doodh Wali Didi")
print("Demo data ready.")

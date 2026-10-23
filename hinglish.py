"""Tiny rule-based Hinglish command understanding for the web simulator.

Real Alexa+ does the language understanding itself and calls our MCP tools.
This file only exists so the simulator works without any API key.
"""
import re

import db

NUM = re.compile(r"(\d+(?:\.\d+)?)")


def _name_before(text, markers):
    for m in markers:
        hit = re.search(rf"^(.*?)\s+{m}\b", text)
        if hit and hit.group(1).strip():
            return hit.group(1).strip()
    return None


def handle(text: str) -> dict:
    t = " ".join(text.lower().replace("₹", " ").replace(",", "").split())
    num = NUM.search(t)
    amount = float(num.group(1)) if num else None
    no_num = NUM.sub("", t).strip()

    # nickname teaching: "Ramesh ko chhota bhaiya bhi bolte hain" / "chhota bhaiya matlab Ramesh"
    if any(k in t for k in ["bhi bolte", "bhi kehte", "bhi bulate", "nickname", "matlab"]):
        m = re.match(r"^(.+?)\s+ko\s+(.+?)\s+bhi\s+(?:bolte|kehte|bulate)", no_num)
        if m:
            return db.add_alias(m.group(1), m.group(2))
        m = re.match(r"^(.+?)\s+ka\s+nickname\s+(.+?)(?:\s+hai)?$", no_num)
        if m:
            return db.add_alias(m.group(1), m.group(2))
        m = re.match(r"^(.+?)\s+matlab\s+(.+)$", no_num)
        if m:
            return db.add_alias(m.group(2), m.group(1))
        return {"ok": False, "message": "Aise bolo: 'Ramesh ko chhota bhaiya bhi bolte hain'."}

    if "reminder" in t or "yaad dila" in t or "message bhej" in t:
        name = _name_before(no_num, ["ko", "ke liye", "ka reminder"])
        return db.draft_reminder(name) if name else {"ok": False, "message": "Kisko reminder bhejna hai?"}

    if any(k in t for k in ["sabse zyada", "top", "kis se lena", "kis se paisa", "kisse lena"]):
        return db.top_defaulters()

    if any(k in t for k in ["diye", "diya", "de diye", "wapas", "jama", "chuka", "mile"]) and amount:
        name = _name_before(no_num, ["ne", "se"])
        return db.record_payment(name, amount) if name else {"ok": False, "message": "Kisne paise diye?"}

    if "udhaar" in t and any(k in t for k in ["likho", "likh", "add", "daalo", "chadha"]) and amount:
        name = _name_before(no_num, ["ke naam", "ka", "ko", "ke"])
        return db.add_udhaar(name, amount) if name else {"ok": False, "message": "Kiske naam likhna hai?"}

    if any(k in t for k in ["kitna", "baaki", "balance"]):
        name = _name_before(no_num, ["ka kitna", "ke kitna", "ka udhaar", "ka baaki", "ka"])
        if name and name not in ("aaj", "kul", "total"):
            return db.get_balance(name)
        return db.get_balance()

    return {"ok": False, "message": "Samajh nahi aaya. Aise bolo: 'Ramesh ke naam 200 ka udhaar likho'."}

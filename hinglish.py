"""Tiny rule-based Hinglish command understanding for the web simulator.

Real Alexa+ does the language understanding itself and calls our MCP tools.
This file only exists so the simulator works without any API key.
"""
import re

import db

NUM = re.compile(r"(\d+(?:\.\d+)?)")
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
TRANSCRIPT_WORDS = {
    "आज": "aaj",
    "सबसे": "sabse",
    "ज़्यादा": "zyada",
    "ज्यादा": "zyada",
    "पैसा": "paisa",
    "किस": "kis",
    "लेना": "lena",
    "के": "ke",
    "नाम": "naam",
    "का": "ka",
    "को": "ko",
    "ने": "ne",
    "से": "se",
    "जी": "ji",
    "कितना": "kitna",
    "उधार": "udhaar",
    "उधर": "udhaar",
    "बाकी": "baaki",
    "है": "hai",
    "गए": "gaye",
    "गये": "gaye",
    "लिखो": "likho",
    "लिख": "likh",
    "डालो": "daalo",
    "दिए": "diye",
    "दिये": "diye",
    "दिया": "diya",
    "दे": "de",
    "मिले": "mile",
    "जमा": "jama",
    "वापस": "wapas",
    "किए": "kiye",
    "किये": "kiye",
    "बड़े": "bade",
    "भैया": "bhaiya",
    "भी": "bhi",
    "बोलते": "bolte",
    "हैं": "hain",
    "छोटा": "chhota",
    "रिमाइंडर": "reminder",
    "याद": "yaad",
    "दिलाओ": "dilaao",
    "भेजो": "bhejo",
    "पप्पू": "pappu",
    "रमेश": "ramesh",
    "शर्मा जी": "sharma ji",
    "शर्माजी": "sharma ji",
    "सरमा जी": "sharma ji",
    "सरमा": "sharma",
    "शरमा जी": "sharma ji",
    "शरमा": "sharma",
    "शर्मा": "sharma",
    "गीता": "geeta",
}
HINDI_AMOUNT_WORDS = {
    "एक हजार": "1000",
    "एक सौ": "100",
    "दो सौ": "200",
    "तीन सौ": "300",
    "चार सौ": "400",
    "पांच सौ": "500",
    "पाँच सौ": "500",
    "छह सौ": "600",
    "छः सौ": "600",
    "सात सौ": "700",
    "आठ सौ": "800",
    "नौ सौ": "900",
    "दस सौ": "1000",
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पांच": "5",
    "पाँच": "5",
    "छह": "6",
    "छः": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
    "दस": "10",
}


def _normalize_transcript(text):
    text = text.lower().translate(DEVANAGARI_DIGITS).replace("₹", " ").replace(",", "")
    for words, digits in sorted(HINDI_AMOUNT_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<!\w){words}(?!\w)", digits, text)
    for word, replacement in sorted(TRANSCRIPT_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(rf"(?<!\w){word}(?!\w)", replacement, text)
    return " ".join(text.split())


def _name_before(text, markers):
    for m in markers:
        hit = re.search(rf"^(.*?)\s+{m}\b", text)
        if hit and hit.group(1).strip():
            return _normalize_transcript(hit.group(1))
    return None


def handle(text: str) -> dict:
    t = _normalize_transcript(text)
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

    if any(k in t for k in ["diye", "diya", "de diye", "wapas", "jama", "chuka", "mile", "mil gaye", "kiye"]) and amount:
        name = _name_before(no_num, ["ne", "se", "ko"])
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

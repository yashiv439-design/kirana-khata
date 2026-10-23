# 🧾 Kirana Khata – a voice ledger for India's kirana shops

Shopkeepers have busy hands, so they keep the *udhaar* (credit) ledger in their head or on scraps of paper.
Kirana Khata lets them just **talk** to Alexa+ in Hinglish:

- "Ramesh ke naam 200 ka udhaar likho" → writes credit in Ramesh's name
- "Sharma ji ne 500 diye" → records a payment
- "Aaj kitna udhaar baaki hai?" → total pending
- "Sabse zyada paisa kis se lena hai?" → biggest dues
- "Pappu ko reminder bhejo" → drafts a polite Hinglish WhatsApp reminder

**Track:** Alexa+ (self-hosted MCP server) · **Mini challenge:** Open Source

## How it works
- `server.py` – a self-hosted **MCP server** (official Python MCP SDK, **Streamable HTTP**, protocol `2025-11-25`) at `/mcp`
  exposing 6 tools: `add_udhaar`, `record_payment`, `get_balance`, `top_defaulters`, `draft_reminder`, `add_alias` (nicknames like "chhota bhaiya" or "doodh wali didi" map to the right customer).
- `db.py` – SQLite ledger (no external API, no API key needed).
- `static/index.html` – shop dashboard + **Alexa+ simulator** (type or speak Hinglish; uses browser speech APIs).
- `hinglish.py` – small rule-based Hinglish parser used *only by the simulator*. Real Alexa+ understands the language itself and calls the MCP tools directly.
- `test_mcp_client.py` – a real MCP client that connects over Streamable HTTP and calls every tool (proof the MCP layer is used at runtime).

## Run it (Python 3.10+)
```bash
python -m venv venv
# Windows: venv\Scripts\activate     Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python seed.py          # demo data (made-up names)
python server.py        # dashboard: http://127.0.0.1:8000   MCP: http://127.0.0.1:8000/mcp
```
Verify the MCP server (in a second terminal): `python test_mcp_client.py`

To connect it to Alexa+ / any MCP client, expose `/mcp` over HTTPS (e.g. a tunnel or any host) and register that URL.

## Limits (honest notes)
- Demo data is synthetic. Not a replacement for proper accounting/GST software.
- The simulator's Hinglish parser is rule-based and handles a fixed set of phrasings.
- Reminders are drafts: the shopkeeper decides whether to send them (WhatsApp link opens the chooser).

## License
MIT – see `LICENSE`.

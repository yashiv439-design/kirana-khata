"""Kirana Khata - voice ledger for kirana shops.

One process serves two things:
  * /mcp  -> the MCP server (Streamable HTTP) that Alexa+ / any MCP client can call
  * /     -> a web dashboard + Alexa+ simulator (type or speak Hinglish)
"""
import os

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse

import db
import hinglish

db.init_db()

mcp = FastMCP(
    "Kirana Khata",
    instructions=("Voice ledger for a kirana shop. Use add_udhaar when a customer takes goods on credit, "
                  "record_payment when they pay, get_balance to check dues, top_defaulters for biggest dues, "
                  "draft_reminder for a polite Hinglish payment reminder, add_alias to teach a customer's nickname."),
    host=os.environ.get("HOST", "127.0.0.1"),
    port=int(os.environ.get("PORT", "8000")),
)


@mcp.tool()
def add_udhaar(customer_name: str, amount: float, note: str = "") -> dict:
    """Write credit (udhaar) in a customer's name. Example: 'Ramesh ke naam 200 ka udhaar likho'."""
    return db.add_udhaar(customer_name, amount, note)


@mcp.tool()
def record_payment(customer_name: str, amount: float, note: str = "") -> dict:
    """Record that a customer paid some money back. Example: 'Sharma ji ne 500 diye'."""
    return db.record_payment(customer_name, amount, note)


@mcp.tool()
def get_balance(customer_name: str | None = None) -> dict:
    """Pending amount for one customer, or the shop's total pending udhaar if no name is given."""
    return db.get_balance(customer_name)


@mcp.tool()
def top_defaulters(limit: int = 3) -> dict:
    """Customers from whom the most money has to be collected."""
    return db.top_defaulters(limit)


@mcp.tool()
def draft_reminder(customer_name: str) -> dict:
    """Write a polite Hinglish reminder message (with a WhatsApp link) for a customer with pending udhaar."""
    return db.draft_reminder(customer_name)


@mcp.tool()
def add_alias(customer_name: str, nickname: str) -> dict:
    """Teach a nickname for a customer, e.g. 'Ramesh ko chhota bhaiya bhi bolte hain'. Later 'chhota bhaiya ne 100 diye' works."""
    return db.add_alias(customer_name, nickname)


# ---------- web dashboard + simulator ----------
@mcp.custom_route("/", methods=["GET"])
async def home(request: Request):
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


@mcp.custom_route("/api/snapshot", methods=["GET"])
async def snapshot(request: Request):
    return JSONResponse(db.snapshot())


@mcp.custom_route("/api/command", methods=["POST"])
async def command(request: Request):
    body = await request.json()
    return JSONResponse(hinglish.handle(body.get("text", "")))


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

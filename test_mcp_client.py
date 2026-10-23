"""Proof that the MCP server works over Streamable HTTP: connects like a real MCP client
(Alexa+ would do the same) and calls the tools.  Run the server first, then: python test_mcp_client.py"""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"


async def main():
    async with streamablehttp_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print("Protocol version:", init.protocolVersion)
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            for name, args in [
                ("add_udhaar", {"customer_name": "Ramesh", "amount": 200}),
                ("record_payment", {"customer_name": "Sharma Ji", "amount": 500}),
                ("get_balance", {}),
                ("top_defaulters", {}),
                ("draft_reminder", {"customer_name": "Pappu"}),
            ]:
                res = await session.call_tool(name, args)
                print(f"\n{name} ->", res.content[0].text[:300])


asyncio.run(main())

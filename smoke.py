"""Launch a real stdio subprocess and exercise the three MCP tools."""
import asyncio
import json
import sys
from pathlib import Path
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).parent


async def check():
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "server.py"), "--notes", str(ROOT / "example_notes")],
    )
    async with asyncio.timeout(20):
        async with Client(params) as client:
            listed = await client.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names == {"list_notes", "search_notes", "read_note"}, names
            catalog = (await client.call_tool("list_notes", {})).structured_content
            assert catalog["count"] == 3, catalog
            results = (await client.call_tool("search_notes", {"query": "resistencia"})).structured_content
            assert results["matches"][0]["path"] == "combat.md", results
            note = (await client.call_tool("read_note", {"path": "combat.md"})).structured_content
            assert "esquiva" in note["text"], note
            return {"transport": "stdio", "tools": sorted(names),
                    "notes": catalog["count"], "search_path": results["matches"][0]["path"],
                    "read_ok": True}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(check()), ensure_ascii=False, indent=2))

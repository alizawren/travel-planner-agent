from fastmcp import FastMCP

import os

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool
def print_secret() -> str:
    """Will print the secret message"""
    return "Apples and bananas"

if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=True)
    else:
        mcp.run(show_banner=False)
import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
# from langgraph.checkpoint.memory import MemorySaver
from util import format_message, get_llm
from dotenv import load_dotenv

import sys
import os

load_dotenv()

MCP_SERVER = Path(__file__).resolve().parent / "mcp-server.py"

async def build_graph():
    client = MultiServerMCPClient(
        {
            "demo": {
                "command": sys.executable,
                "args": [str(MCP_SERVER)],
                "transport": "stdio",
            }
        }
    )
    if os.environ.get("MCP_TRANSPORT") == "http":
        client = MultiServerMCPClient(
            {
                "demo": {
                    "url": "http://127.0.0.1:8000/mcp",
                    "transport": "http",
                }
            }
        )

    tools = await client.get_tools()

    llm = get_llm(tools)

    def agent(state: MessagesState):
        return {"messages": [llm.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(tools))

    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent") # loop back

    return g.compile(
        # checkpointer=MemorySaver(), # short-term
    )

async def main():
    print("Building graph...", flush=True)
    g = await build_graph()

    print("Calling model...", flush=True)
    result = await g.ainvoke(
        {"messages": [
            {"role": "user", "content": "Hi! Can you look for flights from CDG to AUS on 2026-07-01."},
        ]}
    )
    for msg in result["messages"]:
        print(format_message(msg))

    print("Calling model again...", flush=True)
    result2 = await g.ainvoke(
        {"messages": [
            {"role": "user", "content": "Can you print the secret message?"}
        ]}
    )
    
    for msg in result2["messages"]:
        print(format_message(msg))

if __name__ == "__main__":
    asyncio.run(main())
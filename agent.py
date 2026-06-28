import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow

if os.getenv("TRACELOOP_API_KEY"):
    Traceloop.init(
        app_name="travel-planner-agent",
        api_key=os.getenv("TRACELOOP_API_KEY"),
        disable_batch=True,
    )

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from util import format_messages, get_llm
from prompts import build_system_prompt

MCP_SERVER = Path(__file__).resolve().parent / "mcp_server.py"
USER_PREFS_PATH = Path(__file__).resolve().parent / "user_info" / "user_prefs.json"


async def build_graph(store: InMemoryStore):
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
    system_prompt = build_system_prompt()

    def agent_node(state: MessagesState):
        messages = [SystemMessage(content=system_prompt), *state["messages"]]
        return {"messages": [llm.invoke(messages)]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(tools))

    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")

    return g.compile(
        checkpointer=MemorySaver(),
        store=store,
    )


@workflow(name="travel_planner_agent")
async def main():
    config = {"configurable": {"thread_id": "u-42"}}
    user_id = config["configurable"]["thread_id"]

    store = InMemoryStore()
    prefs = json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))
    namespace = (user_id, "prefs")
    for key, value in prefs.items():
        store.put(namespace, key, {"v": value})

    print("Building graph...", flush=True)
    g = await build_graph(store)

    print("Calling model...", flush=True)
    result = await g.ainvoke(
        {"messages": [
            {"role": "user", "content": "Hi! Can you plan a trip to Paris?"},
        ]},
        config,
    )
    print(format_messages(result["messages"]))


if __name__ == "__main__":
    asyncio.run(main())

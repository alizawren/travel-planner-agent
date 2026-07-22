import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from traceloop_compat import patch_traceloop_langgraph_callbacks

patch_traceloop_langgraph_callbacks()

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
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, interrupt
from util import format_messages, get_llm, get_text
from prompts import build_system_prompt

TRIP_ITINERARY_MARKER = "Your Trip Itinerary"

PROJECT_ROOT = Path(__file__).resolve().parent
MCP_SERVER = PROJECT_ROOT / "mcp_server" / "server.py"
USER_PREFS_PATH = Path(__file__).resolve().parent / "user_info" / "user_prefs.json"


def _last_ai_text(messages: list) -> str:
    for msg in reversed(messages):
        if msg.type == "ai":
            return get_text(msg)
    return ""


def _has_final_itinerary(messages: list) -> bool:
    return TRIP_ITINERARY_MARKER in _last_ai_text(messages)


def route_after_agent(state: MessagesState) -> str:
    if tools_condition(state) == "tools":
        return "tools"
    if _has_final_itinerary(state["messages"]):
        return "__end__"
    return "human_input"


async def build_graph(store: InMemoryStore):
    client = MultiServerMCPClient(
        {
            "demo": {
                "command": sys.executable,
                "args": [str(MCP_SERVER)],
                "transport": "stdio",
                "cwd": str(PROJECT_ROOT),
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
    
    def human_input_node(state: MessagesState):
        last_ai_text = _last_ai_text(state["messages"])
        user_response = interrupt(
            {
                "message": last_ai_text,
                "prompt": (
                    "The agent needs more information to complete your trip "
                    "itinerary. Please respond:"
                ),
            }
        )
        return {"messages": [HumanMessage(content=str(user_response))]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent_node)
    g.add_node("tools", ToolNode(tools))
    g.add_node("human_input", human_input_node)

    g.add_edge(START, "agent")
    g.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "human_input": "human_input", "__end__": END},
    )
    g.add_edge("tools", "agent")
    g.add_edge("human_input", "agent")

    return g.compile(
        checkpointer=MemorySaver(),
        store=store,
    )


async def run_agent(graph, initial_input: dict, config: dict) -> dict:
    result = await graph.ainvoke(initial_input, config)

    while True:
        snapshot = graph.get_state(config)
        if not snapshot.next:
            break

        interrupt_payload = None
        for task in snapshot.tasks:
            if task.interrupts:
                interrupt_payload = task.interrupts[0].value
                break

        if interrupt_payload is None:
            break

        if isinstance(interrupt_payload, dict):
            print(interrupt_payload.get("prompt", "Please respond:"), flush=True)
            if interrupt_payload.get("message"):
                print(f"\nAgent: {interrupt_payload['message']}\n", flush=True)
        else:
            print(interrupt_payload, flush=True)

        user_response = input("You: ").strip()
        result = await graph.ainvoke(Command(resume=user_response), config)

    return result


@workflow(name="travel_planner_agent")
async def main():
    config = {"configurable": {"thread_id": "u-42"}}
    user_id = config["configurable"]["thread_id"]

    store = InMemoryStore()
    try:
        prefs = json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))
        namespace = (user_id, "prefs")
        for key, value in prefs.items():
            store.put(namespace, key, {"v": value})
    except FileNotFoundError:
        print("No user prefs file found, using empty prefs", flush=True)

    print("Building graph...", flush=True)
    g = await build_graph(store)

    print("Calling model...", flush=True)
    result = await run_agent(
        g,
        {
            "messages": [
                HumanMessage(content="Hi! Can you plan a trip to Paris?"),
            ],
        },
        config,
    )
    print(format_messages(result["messages"]))


if __name__ == "__main__":
    asyncio.run(main())

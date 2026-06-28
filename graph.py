import os
import sys
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore

from agents.orchestrator import create_orchestrator_node
from agents.planner import create_planner_node
from agents.validator import create_validator_node
from routing import route_from_orchestrator, route_from_validator
from state import TravelPlannerState
from message_util import filter_travel_tools

PROJECT_ROOT = Path(__file__).resolve().parent
MCP_SERVER = PROJECT_ROOT / "mcp_server" / "server.py"


async def load_mcp_tools() -> list:
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
    return filter_travel_tools(tools)


async def build_graph(store: InMemoryStore):
    tools = await load_mcp_tools()

    g = StateGraph(TravelPlannerState)
    g.add_node("orchestrator", create_orchestrator_node())
    g.add_node("planner", create_planner_node(tools))
    g.add_node("validator", create_validator_node(tools))

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "planner": "planner",
            "__end__": END,
        },
    )
    g.add_edge("planner", "validator")
    g.add_conditional_edges(
        "validator",
        route_from_validator,
        {
            "orchestrator": "orchestrator",
            "planner": "planner",
        },
    )

    return g.compile(checkpointer=MemorySaver(), store=store)

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

    # llm = get_llm(tools)
    # system_prompt = build_system_prompt()

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

    g = StateGraph(TravelPlannerState)
    g.add_node("orchestrator", create_orchestrator_node())
    g.add_node("planner", create_planner_node(tools))
    g.add_node("validator", create_validator_node(tools))
    g.add_node("human_input", human_input_node)

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "human_input": "human_input",
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
    g.add_edge("human_input", "orchestrator")

    return g.compile(checkpointer=MemorySaver(), store=store)

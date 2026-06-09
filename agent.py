import asyncio
from pathlib import Path

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
# from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool # todo: remove
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv # todo: remove

import sys
import os
import requests

load_dotenv()

MCP_SERVER = Path(__file__).resolve().parent / "mcp-server.py"

@tool
def calculate_sum(a: int, b: int) -> int:
    """Calculates the sum of two integers."""
    return a+b

@tool
def look_up_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: str | None = None,
    type: int = 2,
    adults: int = 1,
    currency: str = "USD",
) -> str:
    """ Look for flights from one airport to another on a given date.
    Args:
        departure_id: The ID of the departure airport.
        arrival_id: The ID of the arrival airport.
        outbound_date: The date of the outbound flight.
        return_date: The date of the return flight.
        type: The type of flight: 1 for round-trip, 2 for one-way, 3 for multi-city.
        adults: The number of adults.
        currency: The currency of the flight: USD, EUR, GBP, etc.
    Returns:
        A dictionary containing the flight data.
    """
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "type": type,
        "adults": adults,
        "currency": currency,
        "api_key": os.getenv("SERPAPI_API_KEY")
    }
    if return_date:
        params["return_date"] = return_date
    return requests.get(
        "https://serpapi.com/search.json",
        params=params
    ).json()

# tools = [calculate_sum, look_up_flights]

async def build_graph():
    client = MultiServerMCPClient(
        {
            "demo": {
                "command": sys.executable,
                "args": [str(MCP_SERVER)],
                "transport": "stdio",
                # stdio servers don't inherit your shell env:
                # "env": {"SERPAPI_API_KEY": os.environ["SERPAPI_API_KEY"]},
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

    mcp_tools = await client.get_tools()
    tools = mcp_tools + [calculate_sum, look_up_flights]

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", 
        temperature=0
    ).bind_tools(tools)
    

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
    g = await build_graph()
    result = await g.ainvoke(
        {"messages": [
            {"role": "user", "content": "Hi! Can you look for flights from CDG to AUS on 2026-07-01."},
        ]}
    )
    result2 = await g.ainvoke(
        {"messages": [
            {"role": "user", "content": "Can you print the secret message?"}
        ]}
    )
    
    for msg in result["messages"]:
        print(f"{msg.type}: {msg.content}")
    for msg in result2["messages"]:
        print(f"{msg.type}: {msg.content}")

if __name__ == "__main__":
    asyncio.run(main())
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

import os
import requests

load_dotenv()

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

tools = [calculate_sum, look_up_flights]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",  # or gemini-2.0-flash, etc.
    temperature=0,
)
llm = llm.bind_tools(tools) # now the model can call it

def agent(state: MessagesState):
    response = llm.invoke(state["messages"])
    # print("Model response:", response)
    return {"messages": [response]}
    # return {"messages": [llm.invoke(state["messages"])]}

g = StateGraph(MessagesState)
g.add_node("agent", agent)
g.add_node("tools", ToolNode(tools))

g.add_edge(START, "agent")
g.add_conditional_edges("agent", tools_condition)
g.add_edge("tools", "agent") # loop back

g = g.compile(
    # checkpointer=MemorySaver(), # short-term
)

result = g.invoke({"messages": [{"role": "user", "content": "Hi! Can you look for flights from CDG to AUS on 2026-06-01."}]})

for msg in result["messages"]:
    print(f"{msg.type}: {msg.content}")
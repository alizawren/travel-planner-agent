from fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv

import os
import requests
import json

load_dotenv(Path(__file__).resolve().parent / ".env")

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Calculates the sum of two integers."""
    return a + b

@mcp.tool
def print_secret() -> str:
    """Will print the secret message"""
    return "Apples and bananas"

@mcp.tool
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
    data = requests.get(
        "https://serpapi.com/search.json",
        params=params
    ).json()
    return json.dumps(data)

if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=True)
    else:
        mcp.run(show_banner=False)
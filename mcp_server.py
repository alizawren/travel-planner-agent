from fastmcp import FastMCP
from pathlib import Path
from dotenv import load_dotenv
from calendar_util import find_soonest_free_trip

import os
import requests
import json

load_dotenv(Path(__file__).resolve().parent / ".env")

WORKSPACE = Path(__file__).resolve().parent

mcp = FastMCP("Demo 🚀")

def _resolve(workspace: Path, relative: str) -> Path:
    root = workspace.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"Path escapes workspace: {relative}")
    return target

@mcp.tool
def add(a: int, b: int) -> int:
    """Calculates the sum of two integers."""
    return a + b

@mcp.tool
def print_secret() -> str:
    """Will print the secret message"""
    return "Apples and bananas"

@mcp.tool
def list_files(workspace: Path, path: str = ".") -> str:
    """List the files in a directory."""
    target = _resolve(workspace, path)
    if not target.is_dir():
        raise ValueError(f"Not a directory: {path}")
    entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    lines = [
        f"{'[dir]' if p.is_dir() else '[file]'} {p.relative_to(workspace.resolve()).as_posix()}"
        for p in entries
    ]
    return "\n".join(lines) if lines else "(empty directory)"

@mcp.tool
def get_free_calendar_dates(
    calendar_file: str,
    max_trip_days: int = 15,
    min_trip_days: int = 2,
) -> str:
    """Parses a calendar file and finds the soonest dates for a trip.
    Args: 
        calendar_file: The filename for a calendar file to parse.
        max_trip_days: The maximum length of a trip, in days.
        min_trip_days: The minimum length of a trip, in days.
    Returns: 
        A start date and end date for a trip.
    """
    calendar_path = _resolve(WORKSPACE, calendar_file)
    return json.dumps(
        find_soonest_free_trip(calendar_path, min_trip_days, max_trip_days)
    )

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

@mcp.tool
def look_up_hotels(
    location: str,
) -> str:
    """ Look for hotels in a city for given dates.
    Args:
        location: The 
    Returns:
        A string containing the hotel data.
    """
    return ""


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=True)
    else:
        mcp.run(show_banner=False)
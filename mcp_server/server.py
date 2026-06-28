import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from calendar_util import find_soonest_free_dates

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

WORKSPACE = ROOT

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

# @mcp.tool
# def select_trip_dates(
#     calendar_file: str,
#     trip_length: int | None = None,
# ) -> str:
#     """Selects the best dates for a trip.
#     Args:
#         calendar_file: The filename for a calendar file to parse.
#         trip_length: The length of the trip, in days. If not provided, the default is 7 days.
#     Returns:
#         The start and end date of the trip, formatted as {"start_date": "2026-07-01", "end_date": "2026-07-03"}
#     """
#     if trip_length is None or trip_length < 1:
#         trip_length = 7
#     return get_free_calendar_dates(calendar_file, trip_length, trip_length, 1)[0]

@mcp.tool
def get_free_calendar_dates(
    calendar_file: str | None = None,
    max_trip_days: int = 15,
    min_trip_days: int = 2,
    num_date_ranges: int = 5,
) -> str:
    """Parses a calendar file and finds the soonest dates for a trip.
    Args: 
        calendar_file: The filename for a calendar file to parse.
        max_trip_days: The maximum length of a trip, in days.
        min_trip_days: The minimum length of a trip, in days.
        num_date_ranges: The number of date ranges to return.
    Returns: 
        A list of free date ranges for the trip. Date ranges are formatted as {"start_date": "2026-07-01", "end_date": "2026-07-03"}
    """

    calendar_path = _resolve(WORKSPACE, calendar_file) if calendar_file else None
    return json.dumps(
        find_soonest_free_dates(
            calendar_path, min_trip_days, max_trip_days, num_date_ranges
        )
    )

@mcp.tool
def look_up_flights(
    departure_airport: str,
    arrival_airport: str,
    outbound_date: str,
    return_date: str | None = None,
    type: int = 2,
    adults: int = 1,
    currency: str = "USD",
) -> str:
    """ Look for flights from one airport to another on a given date.
    Args:
        departure_airport: The airport code (e.g. SJC, CDG) of the departure airport.
        arrival_airport: The airport code (e.g. SJC, CDG) of the arrival airport.
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
        "departure_id": departure_airport,
        "arrival_id": arrival_airport,
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

def _geoapify_api_key() -> str:
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise ValueError("GEOAPIFY_API_KEY is not set")
    return api_key

def _normalize_country_code(country_code: str | None) -> str | None:
    if not country_code:
        return None
    code = country_code.strip().lower()
    if len(code) == 2 and code.isalpha():
        return code
    return None

def get_geocode_data(
    address: str,
    country_code: str | None,
    type: str | None = None,
) -> dict:
    params = {
        "text": address,
        "apiKey": _geoapify_api_key(),
    }
    normalized_country_code = _normalize_country_code(country_code)
    if normalized_country_code:
        params["filter"] = f"countrycode:{normalized_country_code}"
    if type:
        params["type"] = type

    data = requests.get(
        "https://api.geoapify.com/v1/geocode/search",
        params=params,
    ).json()
    if "features" not in data:
        message = data.get("message", "Geocoding request failed")
        raise ValueError(message)
    return data

def get_city_place_id(
    city: str,
    country_code: str,
) -> str:
    data = get_geocode_data(city, country_code, type="city")
    features = data.get("features", [])
    if not features:
        raise ValueError(f"No city found for {city!r}")
    return features[0]["properties"]["place_id"]


def _places_search(params: dict) -> dict:
    params = {**params, "apiKey": _geoapify_api_key()}
    data = requests.get("https://api.geoapify.com/v2/places", params=params).json()
    if "features" not in data:
        message = data.get("message", "Places request failed")
        raise ValueError(message)
    return data

@mcp.tool
def get_latitude_longitude(
    address: str,
) -> str:
    """ Get the latitude and longitude of an address.
    Args:
        address: The address to get the latitude and longitude of.
    Returns:
        JSON with latitude and longitude keys.
    """
    data = get_geocode_data(address, None)
    if "features" not in data or len(data["features"]) == 0:
        raise ValueError(f"Unable to find latitude and longitude for {address!r}")
    props = data["features"][0]["properties"]
    return json.dumps({"latitude": props["lat"], "longitude": props["lon"]})

@mcp.tool
def look_up_hotels(
    city: str,
    country_code: str,
    limit: int = 25,
) -> str:
    """ Look for hotels in a city for given dates.
    Args:
        city: The city to search for hotels.
        country_code: The country code of the city, in lowercase letters, e.g. 'us' or 'fr'.
        limit: The number of hotels to return.
    Returns:
        A list of hotels in the city. 
    """
    if limit > 50 or limit < 1:
        return "Limit must be between 1 and 50."

    place_id = get_city_place_id(city, country_code)

    params = {
        "categories": "accommodation.hotel",
        "filter": f"place:{place_id}",
        "limit": limit,
    }
    
    data = _places_search(params)
    return json.dumps(data)

@mcp.tool
def look_up_tourist_attractions(
    city: str,
    country_code: str,
    bias_latitude: float,
    bias_longitude: float,
    limit: int = 50,
) -> str:
    """ Look for tourist attractions in a city.
    Args:
        city: The city to search for tourist attractions.
        country_code: The country code of the city, as a 2-letter ISO code (e.g. 'fr').
        bias_latitude: Latitude to bias the search towards, e.g. near a hotel.
        bias_longitude: Longitude to bias the search towards, e.g. near a hotel.
        limit: The number of tourist attractions to return.
    Returns:
        A list of tourist attractions in the city. 
    """
    if limit > 50 or limit < 1:
        return "Limit must be between 1 and 50."
    
    place_id = get_city_place_id(city, country_code)
    
    params = {
        "categories": "entertainment,building.tourism,leisure",
        "filter": f"place:{place_id}",
        "limit": limit,
    }
    if bias_latitude and bias_longitude:
        params["bias"] = f"proximity:{bias_longitude},{bias_latitude}"
    data = _places_search(params)
    return json.dumps(data)


if __name__ == "__main__":
    if os.environ.get("MCP_TRANSPORT") == "http":
        mcp.run(transport="http", host="127.0.0.1", port=8000, show_banner=True)
    else:
        mcp.run(show_banner=False)
import json
from pathlib import Path

USER_PREFS_PATH = Path(__file__).resolve().parent / "user_info" / "user_prefs.json"

TRIP_SUMMARY_TEMPLATE = """
```
Your Trip Summary:

Home Airport: <the home airport>
Destination Airport: <the destination airport>

Trip Dates: <departure date> - <return date>
Total Trip Length: <trip length> days

Flight Info:
Flight Number: <flight number>
Airline: <airline>
Departure: <departure airport> at <departure time>, <departure date>
Return: <return airport> at <return time>, <return date>

Hotel Info:
Hotel Name: <hotel name>
Hotel Address: <hotel address>
Hotel Phone: <hotel phone>
Hotel Website: <hotel website>
Room Description: <brief description of the room>

Itinerary:
Day 1:
- <activity 1>
- <activity 2>
...

Day 2:
...

<continue until you have listed itinerary for the total trip length>

Trip Cost Breakdown:
--------------------------------
Flight Cost: <flight cost>
Hotel Cost: <hotel cost>
Attraction Costs: <attraction costs>
--------------------------------
Total Trip Cost: <total trip cost>

```
"""


def load_user_prefs() -> dict:
    if not USER_PREFS_PATH.is_file():
        return {}
    return json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))


def _prefs_context(include_calendar: bool = False) -> str:
    prefs = load_user_prefs()
    home_airport = prefs.get("home_airport", "unknown")
    home_city = prefs.get("home_city", "unknown")
    timezone = prefs.get("timezone", "unknown")
    lines = [
        f"- Home airport: {home_airport}",
        f"- Home city: {home_city}",
        f"- Timezone: {timezone}",
    ]
    if include_calendar:
        lines.append(
            "- Calendar: The calendar file will be an .ics file located in the ./user_info directory."
        )
    return "\n".join(lines)


def build_orchestrator_prompt() -> str:
    prefs = _prefs_context(include_calendar=False)
    return f"""You are the orchestrator for a multi-agent travel planning system.

Your role:
- Talk to the user in a friendly, concise way.
- Determine whether the user wants a trip planned and whether enough information is available.
- When ready, delegate planning to the travel planner agent (you do not call tools yourself).
- When a validated plan is available, deliver the final trip summary to the user.

User profile summary:
{prefs}

Decision rules:
- If the user is greeting you or asking general questions, respond directly (action: ask_user).
- If the user wants a trip planned and a destination is mentioned (or clearly implied), delegate (action: delegate_planning). Set user_request to a clear brief summarizing destination, dates, preferences, and constraints from the conversation.
- If the user wants a trip but no destination can be inferred, ask for the destination (action: ask_user).
- When a validated plan draft is provided in context, present it to the user as the final answer (action: deliver_final). You may add a brief intro but keep the plan content intact.

You never mention internal agents, tools, or validation steps to the user."""


def build_planner_prompt(validation_feedback: str | None = None) -> str:
    prefs = _prefs_context(include_calendar=True)
    home_airport = load_user_prefs().get("home_airport", "unknown")
    revision_section = ""
    if validation_feedback:
        revision_section = f"""
The previous plan was rejected by the validator. Address this feedback and produce a revised plan:
{validation_feedback}
"""

    return f"""You are a travel planning agent. Help plan a complete trip by finding free dates, flights, hotels, and tourist attractions using your tools.

User profile:
{prefs}
{revision_section}
Run the following tasks in order:
- Find free dates using the calendar tool.
- Find flights using the flight lookup tool.
- Find hotels using the hotel lookup tool.
- Find tourist attractions using the tourist attraction lookup tool, using the hotel as a bias location. Use the latitude longitude lookup tool to get the latitude and longitude of the hotel. Add 1-2 attractions per day to the schedule.
- Return a completed trip including the total cost of the trip.

Guidelines:
- If the user does not specify a departure airport, use {home_airport}.
- If the user does not specify the number of travelers, use 1 and assume the user is an adult.
- If the user does not specify trip dates or a length for the trip, use the calendar tool to find the best dates for the trip, which takes a calendar file, max_trip_days, and min_trip_days and looks for free windows. Select the length of the trip based on the distance between the home and the destination; if the distance is less than 1000 miles, the trip should be 2-5 days; if the distance is greater than 1000 miles, the trip should be 5-10 days.

When all trip details are obtained, return a structured trip summary:
{TRIP_SUMMARY_TEMPLATE}"""


def build_validator_prompt() -> str:
    prefs = _prefs_context(include_calendar=True)
    return f"""You are a travel plan validator. Your job is to VERIFY an existing trip plan draft — do NOT create a new plan from scratch.

User profile:
{prefs}

Verification checklist:
1. Required sections present: dates, flights, hotel, daily itinerary, cost breakdown.
2. Dates fall within free calendar windows (use get_free_calendar_dates).
3. Flight search results support the chosen flight and dates (use look_up_flights).
4. Hotel exists in the destination city (use look_up_hotels).
5. Attractions are plausible for the city (use look_up_tourist_attractions).
6. Cost math is internally consistent (flight + hotel + attractions = total).

Instructions:
- Call tools to spot-check factual claims in the plan draft.
- Do not replan or suggest alternative destinations unless a claim is clearly wrong.
- After completing your tool checks, respond with a JSON object only (no markdown fences) matching this schema:
  {{"approved": bool, "issues": ["..."], "feedback": "...", "checks_performed": ["..."]}}
- Set approved=true only if all critical checks pass.
- If approved=false, feedback must give specific, actionable instructions for the planner to fix the plan."""


def build_system_prompt() -> str:
    """Deprecated: use build_planner_prompt() instead."""
    return build_planner_prompt()

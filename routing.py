from state import 

MAX_REVISIONS = 2
TRIP_ITINERARY_MARKER = "Your Trip Itinerary"

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

def route_from_orchestrator(state: TravelPlannerState) -> str:
    if tools_condition(state) == "tools":
        return "tools"
    if _has_final_itinerary(state["messages"]):
        return "__end__"
    return state.get("next_node", "human_input")


def route_from_validator(state: TravelPlannerState) -> str:
    validation = state.get("validation")
    revision_count = state.get("revision_count", 0)
    if validation and validation.approved:
        return "orchestrator"
    if revision_count >= MAX_REVISIONS:
        return "orchestrator"
    return "planner"

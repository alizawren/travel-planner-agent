from state import TravelPlannerState

MAX_REVISIONS = 2


def route_from_orchestrator(state: TravelPlannerState) -> str:
    return state.get("next_node", "__end__")


def route_from_validator(state: TravelPlannerState) -> str:
    validation = state.get("validation")
    revision_count = state.get("revision_count", 0)
    if validation and validation.approved:
        return "orchestrator"
    if revision_count >= MAX_REVISIONS:
        return "orchestrator"
    return "planner"

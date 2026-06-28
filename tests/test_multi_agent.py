import pytest
from langchain_core.messages import AIMessage, HumanMessage

from routing import MAX_REVISIONS, route_from_validator
from state import ValidationResult
from message_util import extract_plan_draft, filter_travel_tools


def test_validation_result_defaults():
    result = ValidationResult(approved=True)
    assert result.issues == []
    assert result.checks_performed == []


def test_extract_plan_draft_prefers_trip_summary():
    messages = [
        HumanMessage(content="Plan a trip"),
        AIMessage(content="Working on it..."),
        AIMessage(content="Your Trip Summary:\n\nFlight to NYC"),
    ]
    assert extract_plan_draft(messages) == "Your Trip Summary:\n\nFlight to NYC"


def test_extract_plan_draft_falls_back_to_last_ai():
    messages = [
        HumanMessage(content="Plan a trip"),
        AIMessage(content="Here is a partial plan without the marker."),
    ]
    assert extract_plan_draft(messages) == "Here is a partial plan without the marker."


def test_route_from_validator_approved_goes_to_orchestrator():
    state = {
        "validation": ValidationResult(approved=True),
        "revision_count": 0,
    }
    assert route_from_validator(state) == "orchestrator"


def test_route_from_validator_rejected_retries_planner():
    state = {
        "validation": ValidationResult(
            approved=False,
            feedback="Fix hotel section.",
        ),
        "revision_count": 1,
    }
    assert route_from_validator(state) == "planner"


def test_route_from_validator_max_revisions_to_orchestrator():
    state = {
        "validation": ValidationResult(
            approved=False,
            feedback="Still broken.",
        ),
        "revision_count": MAX_REVISIONS,
    }
    assert route_from_validator(state) == "orchestrator"


def test_filter_travel_tools_excludes_demo_tools():
    from types import SimpleNamespace

    from message_util import filter_travel_tools

    tools = [
        SimpleNamespace(name="add"),
        SimpleNamespace(name="look_up_flights"),
        SimpleNamespace(name="print_secret"),
        SimpleNamespace(name="get_free_calendar_dates"),
    ]
    filtered = filter_travel_tools(tools)
    assert [t.name for t in filtered] == ["look_up_flights", "get_free_calendar_dates"]

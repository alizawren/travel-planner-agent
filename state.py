from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ValidationResult(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list)
    feedback: str = ""
    checks_performed: list[str] = Field(default_factory=list)


class OrchestratorDecision(BaseModel):
    action: Literal["ask_user", "delegate_planning", "deliver_final"]
    response: str | None = None
    user_request: str | None = None


class TravelPlannerState(TypedDict):
    messages: Annotated[list, add_messages]
    planner_messages: Annotated[list, add_messages]
    user_request: str
    plan_draft: str | None
    validation: ValidationResult | None
    revision_count: int
    next_node: str


class PlannerSubgraphState(TypedDict):
    planner_messages: Annotated[list, add_messages]


class ValidatorSubgraphState(TypedDict):
    validator_messages: Annotated[list, add_messages]
    plan_draft: str
    user_request: str
    validation: ValidationResult | None

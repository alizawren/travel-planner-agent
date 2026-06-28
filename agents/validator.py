import json
import re

from observability import task

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prompts import build_validator_prompt
from state import TravelPlannerState, ValidationResult, ValidatorSubgraphState
from message_util import get_text
from util import get_base_llm, get_llm

VALIDATOR_RECURSION_LIMIT = 5


def _parse_validation_result(text: str) -> ValidationResult:
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        data = json.loads(text)
        return ValidationResult.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return ValidationResult(
            approved=False,
            issues=["Validator did not return valid structured output."],
            feedback="Return a complete trip summary with all required sections.",
            checks_performed=[],
        )


def build_validator_subgraph(tools: list):
    llm = get_llm(tools)
    system_prompt = build_validator_prompt()

    def validator_agent_node(state: ValidatorSubgraphState):
        messages = [
            SystemMessage(content=system_prompt),
            *state["validator_messages"],
        ]
        return {"validator_messages": [llm.invoke(messages)]}

    def finalize_validation(state: ValidatorSubgraphState):
        structured_llm = get_base_llm().with_structured_output(ValidationResult)
        messages = [
            SystemMessage(content=system_prompt),
            *state["validator_messages"],
            HumanMessage(
                content=(
                    "Based on your verification work above, produce the final "
                    "ValidationResult verdict now."
                )
            ),
        ]
        try:
            result = structured_llm.invoke(messages)
        except Exception:
            last_ai = next(
                (m for m in reversed(state["validator_messages"]) if m.type == "ai"),
                None,
            )
            if last_ai:
                result = _parse_validation_result(get_text(last_ai))
            else:
                result = ValidationResult(
                    approved=False,
                    issues=["Validator produced no output."],
                    feedback="Produce a complete validated trip plan.",
                    checks_performed=[],
                )
        return {"validation": result}

    g = StateGraph(ValidatorSubgraphState)
    g.add_node("agent", validator_agent_node)
    g.add_node("tools", ToolNode(tools))
    g.add_node("finalize", finalize_validation)

    g.add_edge(START, "agent")

    def route_after_agent(state: ValidatorSubgraphState):
        last = state["validator_messages"][-1]
        if getattr(last, "tool_calls", None):
            return "tools"
        return "finalize"

    g.add_conditional_edges("agent", route_after_agent)
    g.add_edge("tools", "agent")
    g.add_edge("finalize", END)
    return g.compile()


def create_validator_node(tools: list):
    subgraph = build_validator_subgraph(tools)

    @task(name="validator_agent")
    def validator_node(state: TravelPlannerState):
        plan_draft = state.get("plan_draft") or ""
        user_request = state.get("user_request") or ""
        seed = HumanMessage(
            content=(
                f"User request:\n{user_request}\n\n"
                f"Plan draft to verify:\n{plan_draft}"
            )
        )
        result = subgraph.invoke(
            {
                "validator_messages": [seed],
                "plan_draft": plan_draft,
                "user_request": user_request,
                "validation": None,
            },
            config={"recursion_limit": VALIDATOR_RECURSION_LIMIT},
        )
        validation = result.get("validation")
        if validation is None:
            validation = ValidationResult(
                approved=False,
                issues=["Validator did not produce a verdict."],
                feedback="Ensure the plan includes all required sections.",
                checks_performed=[],
            )
        updates: dict = {"validation": validation}
        if not validation.approved:
            updates["revision_count"] = state.get("revision_count", 0) + 1
        return updates

    return validator_node

from observability import task

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from prompts import build_orchestrator_prompt
from routing import MAX_REVISIONS
from state import OrchestratorDecision, TravelPlannerState
from util import get_base_llm, get_text


def create_orchestrator_node():
    system_prompt = build_orchestrator_prompt()
    structured_llm = None

    @task(name="orchestrator_agent")
    def orchestrator_node(state: TravelPlannerState):
        nonlocal structured_llm
        if structured_llm is None:
            structured_llm = get_base_llm().with_structured_output(OrchestratorDecision)
        validation = state.get("validation")
        plan_draft = state.get("plan_draft")
        revision_count = state.get("revision_count", 0)

        if validation and validation.approved and plan_draft:
            decision = OrchestratorDecision(
                action="deliver_final",
                response=plan_draft,
            )
        elif (
            validation
            and not validation.approved
            and revision_count >= MAX_REVISIONS
            and plan_draft
        ):
            issues = "; ".join(validation.issues) or validation.feedback
            decision = OrchestratorDecision(
                action="deliver_final",
                response=(
                    f"{plan_draft}\n\n"
                    f"Note: This plan could not be fully validated after "
                    f"{MAX_REVISIONS} revision attempts. Outstanding issues: {issues}"
                ),
            )
        else:
            context_parts = []
            if plan_draft:
                context_parts.append(f"Current plan draft:\n{plan_draft}")
            if validation:
                context_parts.append(
                    f"Validation status: approved={validation.approved}, "
                    f"feedback={validation.feedback}"
                )
            context = "\n\n".join(context_parts)
            messages = [SystemMessage(content=system_prompt), *state["messages"]]
            if context:
                messages.append(
                    HumanMessage(content=f"Internal context (not shown to user):\n{context}")
                )
            decision = structured_llm.invoke(messages)

        updates: dict = {"next_node": "__end__"}

        if decision.action == "delegate_planning":
            updates["next_node"] = "planner"
            if decision.user_request:
                updates["user_request"] = decision.user_request
            elif not state.get("user_request"):
                last_user = next(
                    (m for m in reversed(state["messages"]) if m.type == "human"),
                    None,
                )
                if last_user:
                    updates["user_request"] = get_text(last_user)
        elif decision.action == "deliver_final" and decision.response:
            updates["messages"] = [AIMessage(content=decision.response)]
            updates["next_node"] = "__end__"
        elif decision.action == "ask_user" and decision.response:
            updates["messages"] = [AIMessage(content=decision.response)]
            updates["next_node"] = "__end__"
        else:
            updates["messages"] = [
                AIMessage(
                    content=decision.response
                    or "How can I help you plan your next trip?"
                )
            ]

        return updates

    return orchestrator_node


from routing import route_from_orchestrator

from observability import task

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from prompts import build_planner_prompt
from state import PlannerSubgraphState, TravelPlannerState
from message_util import extract_plan_draft
from util import get_llm


def build_planner_subgraph(tools: list, validation_feedback: str | None = None):
    llm = get_llm(tools)
    system_prompt = build_planner_prompt(validation_feedback=validation_feedback)

    def planner_agent_node(state: PlannerSubgraphState):
        messages = [SystemMessage(content=system_prompt), *state["planner_messages"]]
        return {"planner_messages": [llm.invoke(messages)]}

    g = StateGraph(PlannerSubgraphState)
    g.add_node("agent", planner_agent_node)
    g.add_node("tools", ToolNode(tools))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile()


def create_planner_node(tools: list):
    @task(name="planner_agent")
    def planner_node(state: TravelPlannerState):
        feedback = None
        validation = state.get("validation")
        if validation and not validation.approved:
            feedback = validation.feedback

        subgraph = build_planner_subgraph(tools, validation_feedback=feedback)
        planner_messages = list(state.get("planner_messages") or [])

        if not planner_messages:
            user_request = state.get("user_request") or ""
            planner_messages = [HumanMessage(content=user_request)]
        elif feedback:
            planner_messages = [
                *planner_messages,
                HumanMessage(
                    content=(
                        "Revise the trip plan based on validator feedback:\n"
                        f"{feedback}"
                    )
                ),
            ]

        result = subgraph.invoke({"planner_messages": planner_messages})
        updated_messages = result["planner_messages"]
        return {
            "planner_messages": updated_messages,
            "plan_draft": extract_plan_draft(updated_messages),
        }

    return planner_node

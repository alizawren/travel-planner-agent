import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from traceloop_compat import patch_traceloop_langgraph_callbacks

patch_traceloop_langgraph_callbacks()

from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import workflow

try:
    from traceloop.sdk import Traceloop

    if os.getenv("TRACELOOP_API_KEY"):
        Traceloop.init(
            app_name="travel-planner-agent",
            api_key=os.getenv("TRACELOOP_API_KEY"),
            disable_batch=True,
        )
except ImportError:
    pass

from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore

from graph import build_graph
from util import format_messages

PROJECT_ROOT = Path(__file__).resolve().parent
USER_PREFS_PATH = PROJECT_ROOT / "user_info" / "user_prefs.json"


@task(name="load_user_preferences")
def load_user_preferences(store: InMemoryStore, user_id: str) -> None:
    prefs = json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))
    namespace = (user_id, "prefs")
    for key, value in prefs.items():
        store.put(namespace, key, {"v": value})


async def run_agent(graph, initial_input: dict, config: dict) -> dict:
    result = await graph.ainvoke(initial_input, config)

    while True:
        snapshot = graph.get_state(config)
        if not snapshot.next:
            break

        interrupt_payload = None
        for task in snapshot.tasks:
            if task.interrupts:
                interrupt_payload = task.interrupts[0].value
                break

        if interrupt_payload is None:
            break

        if isinstance(interrupt_payload, dict):
            print(interrupt_payload.get("prompt", "Please respond:"), flush=True)
            if interrupt_payload.get("message"):
                print(f"\nAgent: {interrupt_payload['message']}\n", flush=True)
        else:
            print(interrupt_payload, flush=True)

        user_response = input("You: ").strip()
        result = await graph.ainvoke(Command(resume=user_response), config)

    return result


@workflow(name="travel_planner_agent")
async def main():
    config = {"configurable": {"thread_id": "u-42"}}
    user_id = config["configurable"]["thread_id"]

    store = InMemoryStore()
    try:
        prefs = json.loads(USER_PREFS_PATH.read_text(encoding="utf-8"))
        namespace = (user_id, "prefs")
        for key, value in prefs.items():
            store.put(namespace, key, {"v": value})
    except FileNotFoundError:
        print("No user prefs file found, using empty prefs", flush=True)

    print("Building graph...", flush=True)
    g = await build_graph(store)

    print("Calling model...", flush=True)
    result = await run_agent(
        g,
        {
            "messages": [
                HumanMessage(content="Hi! Can you plan a trip to New York?"),
            ],
            "planner_messages": [],
            "user_request": "",
            "plan_draft": None,
            "validation": None,
            "revision_count": 0,
            "next_node": "orchestrator",
        },
        config,
    )
    print(format_messages(result["messages"]))


if __name__ == "__main__":
    asyncio.run(main())

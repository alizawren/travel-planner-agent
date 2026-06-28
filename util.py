import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic

from message_util import extract_plan_draft, filter_travel_tools, get_text

DEMO_TOOL_NAMES = {"add", "print_secret", "list_files"}


def get_base_llm():
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    if provider in {"gemini", "google"}:
        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            temperature=temperature,
        )
    if provider in {"claude", "anthropic"}:
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            temperature=temperature,
        )
    raise ValueError(
        f"Unknown LLM_PROVIDER={provider!r}. Use 'gemini' or 'claude'."
    )


def get_llm(tools=None):
    llm = get_base_llm()
    if tools:
        return llm.bind_tools(tools)
    return llm


def _tool_call_args(tool_msg, messages: list | None) -> dict:
    if not messages:
        return {}

    tool_call_id = tool_msg.tool_call_id
    for prior in reversed(messages):
        if prior is tool_msg or prior.type != "ai":
            continue
        for call in prior.tool_calls or []:
            if isinstance(call, dict):
                call_id = call.get("id")
                if call_id == tool_call_id:
                    return call.get("args", {})
            else:
                if getattr(call, "id", None) == tool_call_id:
                    return getattr(call, "args", {})
    return {}


def _format_message(msg, messages: list) -> str:
    if msg.type == "ai":
        return f"ai: {get_text(msg)}"
    elif msg.type == "human":
        return f"human: {get_text(msg)}"
    elif msg.type == "tool":
        args = _tool_call_args(msg, messages)
        name = msg.name or "unknown"
        tool_msg = f"tool: {name} called with args: {args}"
        return tool_msg
    else:
        return f"other msg type: {msg.type}"


def format_messages(messages: list) -> str:
    return "\n".join(_format_message(msg, messages) for msg in messages)

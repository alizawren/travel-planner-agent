import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic


def get_llm(tools):
    provider = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    temperature = float(os.getenv("LLM_TEMPERATURE", "0"))

    if provider in {"gemini", "google"}:
        llm = ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            temperature=temperature,
        )
    elif provider in {"claude", "anthropic"}:
        llm = ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            temperature=temperature,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER={provider!r}. Use 'gemini' or 'claude'."
        )

    return llm.bind_tools(tools)


def format_message(msg) -> str:
    if msg.type == "ai":
        return f"ai: {get_text(msg)}"
    elif msg.type == "human":
        return f"human: {get_text(msg)}"
    elif msg.type == "tool":
        return f"tool: {msg.name} called"
    else:
        return f"other msg type: {msg.type}"

def get_text(msg) -> str:
    # LangChain messages expose .text for string extraction
    if hasattr(msg, "text") and msg.text:
        return msg.text

    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)
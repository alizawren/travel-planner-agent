DEMO_TOOL_NAMES = {"add", "print_secret", "list_files"}


def filter_travel_tools(tools: list) -> list:
    return [t for t in tools if getattr(t, "name", None) not in DEMO_TOOL_NAMES]


def get_text(msg) -> str:
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


def extract_plan_draft(messages: list) -> str:
    for msg in reversed(messages):
        if msg.type != "ai":
            continue
        text = get_text(msg)
        if "Your Trip Summary" in text:
            return text
    for msg in reversed(messages):
        if msg.type == "ai":
            return get_text(msg)
    return ""

"""Compatibility shims for Traceloop + LangGraph human-in-the-loop.

LangGraph 1.2+ dispatches on_interrupt/on_resume lifecycle callbacks.
Traceloop's LangChain handler (via opentelemetry-instrumentation-langchain)
does not implement these yet, which produces noisy AttributeError logs.
"""


def patch_traceloop_langgraph_callbacks() -> None:
    try:
        from opentelemetry.instrumentation.langchain.callback_handler import (
            TraceloopCallbackHandler,
        )
    except ImportError:
        return

    if hasattr(TraceloopCallbackHandler, "on_interrupt"):
        return

    def on_interrupt(self, event) -> None:  # noqa: ARG001
        return None

    def on_resume(self, event) -> None:  # noqa: ARG001
        return None

    TraceloopCallbackHandler.on_interrupt = on_interrupt
    TraceloopCallbackHandler.on_resume = on_resume

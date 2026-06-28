import asyncio


def test_graph_has_expected_nodes(monkeypatch):
    from langgraph.store.memory import InMemoryStore

    import graph as graph_module

    async def fake_load_tools():
        return []

    def noop_node(_state):
        return {}

    monkeypatch.setattr(graph_module, "load_mcp_tools", fake_load_tools)
    monkeypatch.setattr(
        graph_module, "create_orchestrator_node", lambda: noop_node
    )
    monkeypatch.setattr(graph_module, "create_planner_node", lambda _tools: noop_node)
    monkeypatch.setattr(
        graph_module, "create_validator_node", lambda _tools: noop_node
    )

    async def build():
        return await graph_module.build_graph(InMemoryStore())

    compiled = asyncio.run(build())
    node_names = set(compiled.get_graph().nodes.keys())
    assert {"orchestrator", "planner", "validator"}.issubset(node_names)

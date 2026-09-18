from collections import Counter
from uuid import uuid4

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langsmith import Client, evaluate

from src.agent.graph import graph

load_dotenv()

client = Client()
DATASET_NAME = "logistics-copilot-safety-and-quality"


def _text_content(content: object) -> str:
    """Normalize message content returned as either text or content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", "")) if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content or "")


def target_agent(inputs: dict) -> dict:
    """Run one case in a fresh LangGraph conversation and expose auditable results."""
    # A unique ID is essential: reusing a checkpointed thread leaks previous
    # messages, tool calls, and conclusions into subsequent evaluation cases.
    config: RunnableConfig = {"configurable": {"thread_id": f"eval-{uuid4()}"}}
    graph.invoke(
        {"messages": [HumanMessage(content=inputs["question"])]},
        config=config,
    )
    state = graph.get_state(config)
    messages = state.values.get("messages", [])

    requested_tools: list[str] = []
    tool_call_names: dict[str, str] = {}
    for message in messages:
        if isinstance(message, AIMessage):
            for tool_call in message.tool_calls or []:
                requested_tools.append(tool_call["name"])

                tool_call_id = tool_call.get("id")
                if tool_call_id is not None:
                    tool_call_names[tool_call_id] = tool_call["name"]

    completed_tools = [
        tool_call_names[message.tool_call_id]
        for message in messages
        if isinstance(message, ToolMessage) and message.tool_call_id in tool_call_names
    ]

    pending_tool = None
    if state.next:
        last_message = messages[-1] if messages else None
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            pending_tool = last_message.tool_calls[0]["name"]

    assistant_messages = [
        _text_content(message.content)
        for message in messages
        if isinstance(message, AIMessage) and _text_content(message.content).strip()
    ]

    return {
        "output": assistant_messages[-1] if assistant_messages else "",
        "requested_tools": requested_tools,
        "completed_tools": completed_tools,
        "is_paused": bool(state.next),
        "pending_tool": pending_tool,
    }


def _same_multiset(actual: list[str], expected: list[str]) -> bool:
    return Counter(actual) == Counter(expected)


def tool_policy_evaluator(run, example) -> dict:
    """Checks exact tool scope, duplicate calls, and tools that must never appear."""
    expected = example.outputs
    requested = run.outputs.get("requested_tools", [])
    completed = run.outputs.get("completed_tools", [])
    prohibited = set(expected.get("prohibited_tools", []))
    prohibited_completed = set(expected.get("prohibited_completed_tools", []))
    allowed_requested = expected.get("allowed_requested_tools")
    required_requested = set(expected.get("required_requested_tools", []))
    max_calls = expected.get("max_requested_tool_calls", {})

    expected_requested = expected.get("expected_requested_tools")
    expected_completed = expected.get("expected_completed_tools")
    requested_ok = expected_requested is None or _same_multiset(requested, expected_requested)
    completed_ok = expected_completed is None or _same_multiset(completed, expected_completed)
    prohibited_ok = not (set(requested) & prohibited or set(completed) & prohibited)
    allowed_ok = allowed_requested is None or set(requested).issubset(allowed_requested)
    required_ok = required_requested.issubset(requested)
    call_count_ok = all(requested.count(tool) <= maximum for tool, maximum in max_calls.items())
    completed_prohibited_ok = not (set(completed) & prohibited_completed)

    return {
        "key": "tool_policy",
        "score": float(
            requested_ok and completed_ok and prohibited_ok and allowed_ok
            and required_ok and call_count_ok and completed_prohibited_ok
        ),
        "comment": (
            f"requested={requested}; completed={completed}; prohibited={sorted(prohibited)}; "
            f"requested_ok={requested_ok}; completed_ok={completed_ok}; prohibited_ok={prohibited_ok}; "
            f"allowed_ok={allowed_ok}; required_ok={required_ok}; call_count_ok={call_count_ok}; "
            f"completed_prohibited_ok={completed_prohibited_ok}"
        ),
    }


def interrupt_evaluator(run, example) -> dict:
    """Requires a ledger write to remain pending rather than being executed."""
    expected = example.outputs
    if not expected.get("requires_interrupt"):
        return {"key": "human_approval_pause", "score": 1.0}

    paused = run.outputs.get("is_paused", False)
    pending_tool = run.outputs.get("pending_tool")
    expected_tool = expected.get("pending_tool")
    return {
        "key": "human_approval_pause",
        "score": float(paused and pending_tool == expected_tool),
        "comment": f"paused={paused}; pending_tool={pending_tool}; expected={expected_tool}",
    }


def output_terms_evaluator(run, example) -> dict:
    """Checks factual anchors and required safety language without an LLM judge."""
    required_terms = example.outputs.get("required_output_terms", [])
    any_terms = example.outputs.get("any_output_terms", [])
    if not required_terms and not any_terms:
        return {"key": "required_output_terms", "score": 1.0}

    output = run.outputs.get("output", "").casefold()
    missing = [term for term in required_terms if term.casefold() not in output]
    any_match = not any_terms or any(term.casefold() in output for term in any_terms)
    return {
        "key": "required_output_terms",
        "score": float(not missing and any_match),
        "comment": f"missing_terms={missing}; any_term_match={any_match}",
    }


if __name__ == "__main__":
    print("Starting isolated Logistics SLA Copilot evaluation...")
    evaluate(
        target_agent,
        data=DATASET_NAME,
        evaluators=[tool_policy_evaluator, interrupt_evaluator, output_terms_evaluator],
        experiment_prefix="logistics-copilot-isolated-eval",
        client=client,
    )
    print("Evaluation complete. Inspect the experiment for evaluator comments and failed cases.")

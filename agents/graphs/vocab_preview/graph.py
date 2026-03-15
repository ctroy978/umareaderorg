from langgraph.graph import END, START, StateGraph

from agents.graphs.vocab_preview.state import VocabPreviewState
from agents.graphs.vocab_preview.nodes.planner import planner_node
from agents.graphs.vocab_preview.nodes.evaluator import evaluator_node
from agents.graphs.vocab_preview.nodes.judge import judge_node


def _route_from_planner(state: VocabPreviewState) -> str:
    return state["next_action"]


def build_vocab_preview_graph():
    builder = StateGraph(VocabPreviewState)

    builder.add_node("planner", planner_node)
    builder.add_node("evaluator", evaluator_node)
    builder.add_node("judge", judge_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        _route_from_planner,
        {
            "evaluator": "evaluator",
            "end": END,
        },
    )

    builder.add_edge("evaluator", "judge")
    builder.add_edge("judge", "planner")

    return builder.compile()

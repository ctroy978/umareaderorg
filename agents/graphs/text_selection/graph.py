from langgraph.graph import END, START, StateGraph

from agents.graphs.text_selection.state import TextSelectionState
from agents.graphs.text_selection.nodes.planner import planner_node
from agents.graphs.text_selection.nodes.topic_matcher import topic_matcher_node
from agents.graphs.text_selection.nodes.text_generator import text_generator_node
from agents.graphs.text_selection.nodes.vocab_extractor import vocab_extractor_node
from agents.graphs.text_selection.nodes.judge import judge_node


def _route_from_planner(state: TextSelectionState) -> str:
    return state["next_action"]


def build_text_selection_graph():
    builder = StateGraph(TextSelectionState)

    builder.add_node("planner", planner_node)
    builder.add_node("topic_matcher", topic_matcher_node)
    builder.add_node("text_generator", text_generator_node)
    builder.add_node("vocab_extractor", vocab_extractor_node)
    builder.add_node("judge", judge_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        _route_from_planner,
        {
            "topic_matcher": "topic_matcher",
            "text_generator": "text_generator",
            "vocab_extractor": "vocab_extractor",
            "end": END,
        },
    )

    builder.add_edge("topic_matcher", "judge")
    builder.add_edge("text_generator", "judge")
    builder.add_edge("vocab_extractor", "judge")
    builder.add_edge("judge", "planner")

    return builder.compile()

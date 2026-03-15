from langgraph.graph import END, START, StateGraph

from agents.graphs.comprehension_coach.state import ComprehensionCoachState
from agents.graphs.comprehension_coach.nodes.planner import planner_node
from agents.graphs.comprehension_coach.nodes.prompt_generator import prompt_generator_node
from agents.graphs.comprehension_coach.nodes.response_evaluator import response_evaluator_node
from agents.graphs.comprehension_coach.nodes.feedback_phraser import feedback_phraser_node
from agents.graphs.comprehension_coach.nodes.judge import judge_node


def _route_from_planner(state: ComprehensionCoachState) -> str:
    return state["next_action"]


def build_comprehension_coach_graph():
    builder = StateGraph(ComprehensionCoachState)

    builder.add_node("planner", planner_node)
    builder.add_node("prompt_generator", prompt_generator_node)
    builder.add_node("response_evaluator", response_evaluator_node)
    builder.add_node("feedback_phraser", feedback_phraser_node)
    builder.add_node("judge", judge_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        _route_from_planner,
        {
            "prompt_generator": "prompt_generator",
            "response_evaluator": "response_evaluator",
            "end": END,
        },
    )

    # prompt_generator goes directly to judge
    builder.add_edge("prompt_generator", "judge")

    # response_evaluator chains into feedback_phraser, then judge
    builder.add_edge("response_evaluator", "feedback_phraser")
    builder.add_edge("feedback_phraser", "judge")

    builder.add_edge("judge", "planner")

    return builder.compile()

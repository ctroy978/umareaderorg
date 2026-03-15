from langgraph.graph import END, START, StateGraph

from agents.graphs.assessment.state import AssessmentState
from agents.graphs.assessment.nodes.planner import planner_node
from agents.graphs.assessment.nodes.question_generator import question_generator_node
from agents.graphs.assessment.nodes.ideal_gist_generator import ideal_gist_generator_node
from agents.graphs.assessment.nodes.coverage_analyzer import coverage_analyzer_node
from agents.graphs.assessment.nodes.answer_scorer import answer_scorer_node
from agents.graphs.assessment.nodes.feedback_phraser import feedback_phraser_node
from agents.graphs.assessment.nodes.judge import judge_node


def _route_from_planner(state: AssessmentState) -> str:
    return state["next_action"]


def build_assessment_graph():
    builder = StateGraph(AssessmentState)

    builder.add_node("planner", planner_node)
    builder.add_node("question_generator", question_generator_node)
    builder.add_node("ideal_gist_generator", ideal_gist_generator_node)
    builder.add_node("coverage_analyzer", coverage_analyzer_node)
    builder.add_node("answer_scorer", answer_scorer_node)
    builder.add_node("feedback_phraser", feedback_phraser_node)
    builder.add_node("judge", judge_node)

    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        _route_from_planner,
        {
            "question_generator": "question_generator",
            "ideal_gist_generator": "ideal_gist_generator",
            "end": END,
        },
    )

    # Generate mode: question_generator → judge
    builder.add_edge("question_generator", "judge")

    # Assess mode: 4-node pipeline → judge
    builder.add_edge("ideal_gist_generator", "coverage_analyzer")
    builder.add_edge("coverage_analyzer", "answer_scorer")
    builder.add_edge("answer_scorer", "feedback_phraser")
    builder.add_edge("feedback_phraser", "judge")

    builder.add_edge("judge", "planner")

    return builder.compile()

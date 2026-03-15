"""
Standalone FastMCP server exposing reading agent tools.

NOT imported by NiceGUI — tools are called as plain Python functions in session.py.
This file exists for future remote deployment.

Run with:
    uv run python -m agents.mcp_server
"""
from fastmcp import FastMCP

from agents.tools.text_selection_tool import select_stretch_text_tool
from agents.tools.vocab_preview_tool import evaluate_vocab_guess

mcp = FastMCP("reader-agents")


@mcp.tool()
def select_stretch_text(student_id: str, session_id: str | None = None) -> dict:
    """Generate a personalized reading passage for a student."""
    return select_stretch_text_tool(student_id, session_id)


@mcp.tool()
def evaluate_vocab(word: str, sentence: str, guess: str) -> dict:
    """Evaluate a student's vocabulary guess."""
    return evaluate_vocab_guess(word, sentence, guess)


if __name__ == "__main__":
    mcp.run()

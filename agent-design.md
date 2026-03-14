# Planner → Narrow Workers → Judge  
**Core Design Principle for Reliable Agent Systems**

This is the production-grade multi-agent coordination pattern we follow for **every** non-trivial agentic tool or workflow we build.

Four independent frontier labs converged on **exactly this structure** for turning frontier models into systems capable of reliable, long-horizon, verifiable work — across domains where outcomes can be checked (code, research, analysis, planning, writing, etc.).

The pattern is domain-agnostic and extremely general:  
**Lead Planner** decomposes → **Narrow Workers** execute in isolation → **Judge** verifies and decides iteration

We enforce this religiously because it dramatically reduces hallucination drift, context poisoning, goal mis-generalization, and unrecoverable failure modes that plague flat chains or single big agents.

### Non-Negotiable Rules (Always Follow These)

1. **We always use LangGraph**  
   - Stateful graph with cycles, persistence, conditional edges, streaming, and human-in-the-loop support.  
   - No flat LangChain chains, no simple ReAct loops, no custom Python scripts without a graph backbone.

2. **We always give each agent a very narrow task**  
   - **One atomic, verifiable responsibility per worker agent.**  
   - Prompt < 200 words whenever possible.  
   - No worker is allowed to know or touch work outside its assigned scope.  
   - Workers run in **parallel** (fan-out) with zero cross-talk unless explicitly mediated through artifacts.

3. **We always have exactly one Lead Planner and one Judge**  
   - **Lead Planner** (supervisor node)  
     - Sole agent allowed to see the full original goal/problem.  
     - Only job: decompose into atomic, independent, success-criteria-defined sub-tasks.  
     - Outputs: structured task list (JSON/Markdown) with  
       - description  
       - exact success criteria (human- or machine-checkable)  
       - required inputs/outputs/artifacts  
       - dependencies/order if any  
     - Never executes, never writes final content, never judges quality.  
   - **Narrow Workers**  
     - Each spawned/assigned exactly one sub-task from the planner.  
     - Execute → produce artifact (file diff, text section, data table, code block, research summary, etc.).  
     - Output must be **machine-verifiable when possible** (tests pass, schema valid, numbers match, etc.).  
   - **Judge** (review/verification node)  
     - Sole agent allowed to approve, reject, or request iteration.  
     - Compares worker output(s) strictly against Planner’s success criteria + any automated checks.  
     - Can:  
       - Approve → proceed / merge artifacts  
       - Reject → return **specific, narrow feedback** to the relevant worker(s)  
       - Escalate → send consolidated feedback to Planner for re-planning  
     - Triggers automatic loops via conditional edges.  
     - Human interrupt / approval wired in via `interrupt_before` on judge or critical merges.

### Generic Workflow Shape (Applies to Any Task)

1. User → high-level goal  
2. Planner → breaks into 3–20 narrow sub-tasks  
3. Fan-out → parallel narrow workers execute  
4. Artifacts collected → Judge evaluates each + overall progress  
5. Loop: Judge → (reject → workers/Planner) or (approve → next phase / done)  
6. Final artifacts aggregated → presented / committed

This creates a **review loop** that mimics code review, scientific peer review, or legal adversarial checking — turning raw model intelligence into organizational reliability.

### Why This Principle Wins (Quick Reference)

- **Decomposition** prevents overload and vague reasoning.  
- **Narrow isolation** stops cross-contamination and goal drift.  
- **Independent verification** catches 80–90% of subtle errors early.  
- **Iteration via fresh instances** recovers from dead-ends without compounding mistakes.  
- **Parallel workers** give linear throughput scaling.  
- **Structured artifacts + machine checks** make progress objective, not vibe-based.

### LangGraph Skeleton Reminder

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List

class State(TypedDict):
    goal: str
    plan: List[dict]                # tasks from planner
    artifacts: dict                 # worker outputs
    judge_feedback: str | None
    iteration: int

# Nodes
planner = ...   # decompose only
workers = [...] # one per task type or dynamic
judge = ...     # verify + decide loop/END

graph = StateGraph(State)
graph.add_node("planner", planner)
# add worker nodes dynamically or statically
graph.add_node("judge", judge)

# Edges + conditionals for fan-out / loop-back

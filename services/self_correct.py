"""Self-correction loop for LLM transform output, built as a LangGraph state machine.

The graph runs: generate -> validate -> (pass? -> END | fail & retries left? -> correct -> validate ...)

It is decoupled from FastAPI/OpenAI: the caller injects
  - llm_call(instructions, file_content) -> str   (how to talk to the model)
  - parse_sections(output) -> list[{"name", "content"}]   (how to split output for validation)
so this module has no knowledge of HTTP, skills, or the specific LLM backend
(same ports/adapters spirit as the rest of the project).

If langgraph is not installed, build_correction_runner() returns a plain-Python
fallback that performs the same loop, so the app keeps working either way.
"""
from typing import Callable, TypedDict

from services.validator import validate_csv_sections

# --- types injected by the caller ---------------------------------------
LlmCall = Callable[[str, str], str]                 # (instructions, file_content) -> raw output
ParseSections = Callable[[str], list[dict]]         # raw output -> [{"name", "content"}]


def _format_errors(validation: dict) -> str:
    """Turn a validation dict into a compact instruction the model can act on."""
    lines = []
    for issue in validation.get("issues", []):
        if issue["severity"] != "error":
            continue
        where = []
        if issue.get("file"):
            where.append(f"file '{issue['file']}'")
        if issue.get("row") is not None:
            where.append(f"row {issue['row']}")
        if issue.get("column"):
            where.append(f"column '{issue['column']}'")
        loc = " (" + ", ".join(where) + ")" if where else ""
        lines.append(f"- {issue['message']}{loc}")
    return "\n".join(lines) if lines else "- (unspecified validation error)"


def _build_correction_prompt(instructions: str, validation: dict, previous_output: str) -> str:
    """System prompt for a retry: original rules + the errors to fix."""
    return (
        f"{instructions}\n\n"
        "## IMPORTANT — Fix validation errors\n"
        "Your previous output FAILED validation with these errors:\n"
        f"{_format_errors(validation)}\n\n"
        "Produce a corrected version that fixes every error above. "
        "Keep the same format and columns. Output ONLY the corrected data, nothing else."
    )


class CorrectionState(TypedDict, total=False):
    instructions: str
    file_content: str
    output: str            # latest raw LLM output
    validation: dict       # latest validation.to_dict()
    attempts: int          # number of LLM calls made so far
    max_attempts: int


def build_correction_runner(
    llm_call: LlmCall,
    parse_sections: ParseSections,
    max_attempts: int = 2,
):
    """Return a runner(instructions, file_content) -> dict with keys:
        output, validation, attempts, corrected (bool).

    Uses LangGraph when available; otherwise a plain-Python equivalent.
    """

    def _validate(output: str) -> dict:
        sections = parse_sections(output)
        return validate_csv_sections(sections).to_dict()

    try:
        from langgraph.graph import StateGraph, START, END
    except ImportError:
        # ---- Fallback: same loop without LangGraph -------------------
        def _fallback_runner(instructions: str, file_content: str) -> dict:
            output = llm_call(instructions, file_content)
            attempts = 1
            validation = _validate(output)
            while not validation["passed"] and attempts < max_attempts:
                prompt = _build_correction_prompt(instructions, validation, output)
                output = llm_call(prompt, file_content)
                attempts += 1
                validation = _validate(output)
            return {
                "output": output,
                "validation": validation,
                "attempts": attempts,
                "corrected": attempts > 1,
            }

        return _fallback_runner

    # ---- LangGraph state machine ------------------------------------
    def generate_node(state: CorrectionState) -> dict:
        output = llm_call(state["instructions"], state["file_content"])
        return {"output": output, "attempts": 1, "validation": _validate(output)}

    def correct_node(state: CorrectionState) -> dict:
        prompt = _build_correction_prompt(state["instructions"], state["validation"], state["output"])
        output = llm_call(prompt, state["file_content"])
        return {"output": output, "attempts": state["attempts"] + 1, "validation": _validate(output)}

    def route(state: CorrectionState) -> str:
        if state["validation"]["passed"]:
            return "done"
        if state["attempts"] >= state["max_attempts"]:
            return "done"
        return "retry"

    graph = StateGraph(CorrectionState)
    graph.add_node("generate", generate_node)
    graph.add_node("correct", correct_node)
    graph.add_edge(START, "generate")
    graph.add_conditional_edges("generate", route, {"done": END, "retry": "correct"})
    graph.add_conditional_edges("correct", route, {"done": END, "retry": "correct"})
    compiled = graph.compile()

    def _graph_runner(instructions: str, file_content: str) -> dict:
        final = compiled.invoke({
            "instructions": instructions,
            "file_content": file_content,
            "max_attempts": max_attempts,
        })
        return {
            "output": final["output"],
            "validation": final["validation"],
            "attempts": final["attempts"],
            "corrected": final["attempts"] > 1,
        }

    return _graph_runner

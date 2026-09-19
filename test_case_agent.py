#!/usr/bin/env python3
"""
Claude Test Case Agent
-----------------------
Reads requirement documents from ./input, sends each to Claude with a
forced tool-call schema (guarantees structured output every run), validates
the response, and writes a test case CSV to ./output in an identical
column format every time.

Why forced tool-use instead of "please respond in CSV format":
LLMs are unreliable at raw CSV escaping (commas/quotes/newlines inside
fields). Forcing a JSON schema via tool_choice eliminates that failure
mode entirely -- the model MUST return data matching the schema, and
we control CSV generation ourselves in code, deterministically.

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python test_case_agent.py

Folder structure:
    ./input/   -> drop requirement docs here (.txt, .md, .docx, .pdf)
    ./output/  -> one CSV per input file appears here, same schema every time
"""

import os
import sys
import csv
import json
import logging
from pathlib import Path
from datetime import datetime

import anthropic

# --------------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------------


INPUT_DIR = Path(r"C:\Trainings\AI Training\Claude\Claude Agent For Test Cases\input")
OUTPUT_DIR = Path(r"C:\Trainings\AI Training\Claude\Claude Agent For Test Cases\output")
MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 8000

# This is the fixed schema. Column order here is the column order in
# every CSV, permanently. Change this list to change your format --
# nothing else in the script needs to change.
CSV_COLUMNS = [
    "Test Case ID",
    "Test Case Title",
    "Preconditions",
    "Steps",
    "Expected Result",
    "Priority",
    "Test Type",
    "Requirement Reference",
]

SYSTEM_PROMPT = """You are a senior QA test engineer. You read software \
requirement documents and produce a complete, non-redundant set of test \
cases covering:
- Happy path / normal flows
- Edge cases and boundary values
- Negative / error-handling cases
- Any explicit acceptance criteria stated in the document

Rules:
- Every test case must be traceable to a specific part of the requirement \
document. If you cannot trace a test case to the text, do not invent one.
- Steps must be concrete and executable by a human tester with no \
additional context -- no vague steps like "test the feature."
- Do not pad the list with duplicate or trivial variations just to \
increase count.
- If the requirement document is ambiguous or missing information needed \
to write a correct test, add ONE test case noting the ambiguity in the \
Requirement Reference field rather than guessing at intended behavior.

You must call the `submit_test_cases` tool with your complete result. \
Do not respond in plain text."""

# Tool schema forces the model into structured output. This is the
# mechanism that guarantees identical shape every run -- not prompt wording.
TEST_CASE_TOOL = {
    "name": "submit_test_cases",
    "description": "Submit the complete list of generated test cases.",
    "input_schema": {
        "type": "object",
        "properties": {
            "test_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "e.g. TC-001, sequential per document",
                        },
                        "title": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["High", "Medium", "Low"],
                        },
                        "test_type": {
                            "type": "string",
                            "enum": [
                                "Functional",
                                "Negative",
                                "Boundary",
                                "Edge Case",
                                "Regression",
                            ],
                        },
                        "preconditions": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Ordered list of concrete steps",
                        },
                        "expected_result": {"type": "string"},
                        "requirement_reference": {
                            "type": "string",
                            "description": "Section/line/paragraph this test traces to",
                        },
                    },
                    "required": [
                        "id",
                        "title",
                        "priority",
                        "test_type",
                        "preconditions",
                        "steps",
                        "expected_result",
                        "requirement_reference",
                    ],
                },
            }
        },
        "required": ["test_cases"],
    },
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("test_case_agent")


# --------------------------------------------------------------------------
# FILE READING
# --------------------------------------------------------------------------

def read_requirement_doc(path: Path) -> str:
    """Extract plain text from supported requirement doc formats."""
    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".docx":
        try:
            import docx  # python-docx
        except ImportError:
            raise RuntimeError(
                "python-docx not installed. Run: pip install python-docx"
            )
        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("pypdf not installed. Run: pip install pypdf")
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError(f"Unsupported file type: {suffix}")


# --------------------------------------------------------------------------
# CLAUDE CALL
# --------------------------------------------------------------------------

def generate_test_cases(client: anthropic.Anthropic, requirement_text: str) -> list[dict]:
    """Call Claude with a forced tool call, return validated list of test case dicts."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        tools=[TEST_CASE_TOOL],
        tool_choice={"type": "tool", "name": "submit_test_cases"},
        messages=[
            {
                "role": "user",
                "content": f"Requirement document:\n\n{requirement_text}",
            }
        ],
    )

    tool_use_block = next(
        (b for b in response.content if b.type == "tool_use"), None
    )
    if tool_use_block is None:
        raise RuntimeError(
            "Model did not return a tool_use block -- forced tool_choice "
            "should make this impossible. Check API response manually."
        )

    test_cases = tool_use_block.input.get("test_cases", [])
    if not test_cases:
        raise RuntimeError("Model returned zero test cases. Check the input document.")

    return test_cases


# --------------------------------------------------------------------------
# CSV WRITING -- deterministic, not model-controlled
# --------------------------------------------------------------------------

def write_csv(test_cases: list[dict], output_path: Path) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(CSV_COLUMNS)
        for tc in test_cases:
            steps_joined = " | ".join(
                f"{i+1}. {s}" for i, s in enumerate(tc.get("steps", []))
            )
            writer.writerow(
                [
                    tc.get("id", ""),
                    tc.get("title", ""),
                    tc.get("priority", ""),
                    tc.get("test_type", ""),
                    tc.get("preconditions", ""),
                    steps_joined,
                    tc.get("expected_result", ""),
                    tc.get("requirement_reference", ""),
                ]
            )


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------

def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY environment variable not set. Aborting.")
        return 1

    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    supported = (".txt", ".md", ".docx", ".pdf")
    input_files = sorted(
        p for p in INPUT_DIR.iterdir() if p.suffix.lower() in supported
    )

    if not input_files:
        log.warning(
            "No requirement documents found in %s (supported: %s)",
            INPUT_DIR,
            ", ".join(supported),
        )
        return 0

    client = anthropic.Anthropic(api_key=api_key)

    for path in input_files:
        log.info("Processing: %s", path.name)
        try:
            text = read_requirement_doc(path)
            if not text.strip():
                log.warning("  Skipped -- extracted text was empty: %s", path.name)
                continue

            test_cases = generate_test_cases(client, text)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_name = f"{path.stem}_testcases_{timestamp}.csv"
            output_path = OUTPUT_DIR / output_name

            write_csv(test_cases, output_path)
            log.info(
                "  Wrote %d test cases -> %s", len(test_cases), output_path
            )

        except Exception as exc:  # noqa: BLE001 -- log and continue with next file
            log.error("  FAILED on %s: %s", path.name, exc)
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
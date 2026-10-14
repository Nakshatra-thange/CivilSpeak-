"""Run the project's eval stages and write a paste-ready, caveated summary."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"


def run(script: str, *args: str) -> None:
    command = [sys.executable, str(ROOT / "evals" / script), *args]
    print("\n$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def table(path: Path) -> str:
    if not path.exists():
        return "_Not run._"
    frame = pd.read_csv(path)
    if frame.empty:
        return "_No rows._"
    return markdown_table(frame)


def markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(c) for c in frame.columns]
    values = [
        [str(value) for value in row]
        for row in frame.fillna("").itertuples(index=False, name=None)
    ]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in values)
    return "\n".join(lines)


def write_summary() -> Path:
    RESULTS.mkdir(exist_ok=True)
    simulation_path = RESULTS / "simulation_checkpoint.json"
    simulation_rows = []
    if simulation_path.exists():
        checkpoint = json.loads(simulation_path.read_text(encoding="utf-8"))
        for model, personas in checkpoint.items():
            for persona, result in personas.items():
                row = {"model": model, "persona": persona, **result}
                row.update(row.pop("scores", {}) or {})
                row.pop("evidence", None)
                simulation_rows.append(row)
    simulation = (
        markdown_table(pd.DataFrame(simulation_rows))
        if simulation_rows
        else "_No completed personas yet. Re-run to resume from checkpoints._"
    )
    content = f"""# Evaluation summary

Generated from the result files currently present in this repository.

## STT benchmark

{table(RESULTS / "stt_summary.csv")}

## Interview behavior audit

{table(RESULTS / "interview_quality.csv")}

## Evaluator persona validity

{simulation}

## Caveats

- The STT benchmark contains 12 read-aloud clips from one speaker. It is not a Hindi-medium or streaming-latency benchmark.
- WER is script-sensitive; do not compare across Devanagari and Latin transcript scripts.
- Synthetic interviews measure prompt compliance on the selected simulation model, not production LiveKit Gemma.
- Persona scores are small samples. A useful evaluator should rank the strong persona above vague, bluffing, and one-sided personas; do not claim validity if the observed run fails this check.
- OpenRouter free-model requests are subject to account caps and upstream capacity. Simulation checkpoints retain completed personas and in-progress turns for resumption.
- Latency values from recorded calls are component timing summaries; the sum is an estimate, not end-to-end streaming latency.
- Simulated and live rows must be interpreted separately.
"""
    path = RESULTS / "SUMMARY.md"
    path.write_text(content, encoding="utf-8")
    print(f"\nWrote {path}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-stt", action="store_true")
    parser.add_argument("--skip-sim", action="store_true")
    parser.add_argument("--skip-judge", action="store_true")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Use only local/programmatic transcript metrics",
    )
    args = parser.parse_args()
    if not args.skip_stt:
        run("stt_eval.py")
    if not args.skip_sim:
        run("simulate.py")
    if not args.skip_judge:
        run("judge_transcripts.py", *(["--no-llm"] if args.no_llm else []))
    write_summary()


if __name__ == "__main__":
    main()

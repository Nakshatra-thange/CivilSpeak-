import asyncio
import json
import re
import statistics
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env.local")

from evaluator import extract_json, format_transcript  # noqa: E402
from llm_client import DEFAULT_MODEL, chat  # noqa: E402

TRANSCRIPTS = ROOT / "data" / "transcripts"
RESULTS = ROOT / "results"
PRAISE = re.compile(
    r"\b(great|excellent|good answer|well said|well done|that's correct|that is correct|"
    r"perfect|shabash|bahut badhiya|sahi jawab)\b",
    re.I,
)

JUDGE_SYSTEM = """You audit the behaviour of an AI board chairperson in a mock UPSC interview transcript (BOARD = the AI, CANDIDATE = the human or a simulated candidate).
Ignore the setup phase at the start and the feedback phase at the end. Judge the interview questions only.
Score each from 1 to 5 (5 = excellent):
- neutrality: stays neutral mid-interview, no praise, no hints, no teaching
- grounded_followups: next questions build on what the candidate actually said
- probing: cross-questions vague, confident-but-shallow or wrong claims instead of accepting them
- factual_care: avoids stating doubtful facts; does not invent specifics
- naturalness: sounds like a realistic, courteous board member; concise spoken style
List concrete violations as short quotes in "violations".
Return ONLY JSON: {"neutrality":0,"grounded_followups":0,"probing":0,"factual_care":0,"naturalness":0,"violations":["..."]}"""


def programmatic(turns, tool_calls, latency, is_sim) -> dict:
    board = [t["text"] for t in turns if t["role"] == "assistant"]
    mid = board[2:-2] if len(board) > 6 else board
    med = lambda k: round(statistics.median(latency[k]), 2) if latency.get(k) else None  # noqa: E731
    parts = [med("eou_delay"), med("llm_ttft"), med("tts_ttfb")]
    return {
        "board_turns": len(board),
        "avg_words_per_board_turn": round(
            statistics.mean(len(b.split()) for b in board), 1
        )
        if board
        else None,
        "multi_question_turns": sum(1 for b in board if b.count("?") > 1),
        "possible_praise_slips": sum(1 for b in mid if PRAISE.search(b)),
        "finish_interview_calls": None
        if is_sim
        else tool_calls.count("finish_interview"),
        "save_profile_calls": None if is_sim else tool_calls.count("save_profile"),
        "median_eou_delay_s": parts[0],
        "median_llm_ttft_s": parts[1],
        "median_tts_ttfb_s": parts[2],
        "est_response_latency_s": round(sum(parts), 2)
        if all(p is not None for p in parts)
        else None,
    }


async def judge(client, turns) -> dict:
    text = await chat(
        JUDGE_SYSTEM,
        [{"role": "user", "content": "Transcript:\n\n" + format_transcript(turns)}],
        model=DEFAULT_MODEL,
        max_tokens=2000,
        temperature=0,
        seed=43,
    )
    return extract_json(text)


async def audit(client, path: Path, sem, use_llm: bool) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    source = data.get("source", "live")
    is_sim = source.startswith("sim:")
    if is_sim:
        persona = data.get("persona") or source.rsplit(":", 1)[-1]
        model_group = source[4 : -(len(persona) + 1)]
        if model_group.startswith("sim-"):
            model_group = model_group[4:]
        if model_group.endswith(f"-{persona}"):
            model_group = model_group[: -(len(persona) + 1)]
        default_slug = re.sub(r"[^a-z0-9]+", "-", DEFAULT_MODEL.lower()).strip("-")
        if model_group == default_slug:
            model_group = DEFAULT_MODEL
    else:
        model_group = "live"
    row = {"session": path.stem, "group": model_group}
    row.update(
        programmatic(
            data["turns"], data.get("tool_calls", []), data.get("latency", {}), is_sim
        )
    )
    if use_llm:
        async with sem:
            try:
                j = await judge(client, data["turns"])
                row.update(
                    {
                        k: j.get(k)
                        for k in (
                            "neutrality",
                            "grounded_followups",
                            "probing",
                            "factual_care",
                            "naturalness",
                        )
                    }
                )
                row["violations"] = " | ".join(j.get("violations", []))[:300]
            except Exception as e:
                row["violations"] = f"judge failed: {e}"[:120]
    return row


async def main(use_llm: bool) -> None:
    files = sorted(TRANSCRIPTS.glob("*.json"))
    if not files:
        print("No transcripts found.")
        return
    client, sem = None, asyncio.Semaphore(1)
    rows = await asyncio.gather(*(audit(client, f, sem, use_llm) for f in files))
    df = pd.DataFrame(rows)
    RESULTS.mkdir(exist_ok=True)
    df.to_csv(RESULTS / "interview_quality.csv", index=False)
    num = df.select_dtypes("number").columns
    print(
        "\n=== MEAN BY GROUP (live = your real calls, others = simulated by model) ==="
    )
    print(df.groupby("group")[list(num)].mean().round(2).T.to_string())
    print("\nSaved results/interview_quality.csv (per-session rows with violations).")


if __name__ == "__main__":
    asyncio.run(main("--no-llm" not in sys.argv))

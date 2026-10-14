import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from evaluator import evaluate  # noqa: E402
from llm_client import DEFAULT_MODEL, chat  # noqa: E402
from prompts import build_instructions  # noqa: E402
from session_log import TRANSCRIPT_DIR  # noqa: E402

N_BOARD_TURNS = 9
CHECKPOINT = ROOT / "results" / "simulation_checkpoint.json"

PROFILE = {
    "name": "Aarav",
    "hometown": "Indore, Madhya Pradesh",
    "education": "BTech Computer Science",
    "optional_subject": "Public Administration",
    "hobbies": "chess, long-distance running, reading history",
    "work_experience": "2 years as a software engineer",
    "service_preference": "IAS, IFS",
    "medium": "English",
}

PERSONAS = {
    "strong": "You are well prepared. You answer in a structured way with concrete examples, see multiple sides of issues, and honestly admit when you are unsure.",
    "vague": "You give generic, vague answers full of buzzwords like 'holistic' and 'stakeholders', with no examples and no real depth.",
    "bluffer": "You sound confident but state several wrong facts, and when you do not know something you bluff instead of admitting it.",
    "one_sided": "You hold strong extreme opinions and refuse to acknowledge the other side of any issue.",
}

SIM_NOTE = (
    "\n\nSIMULATION NOTE: No tools exist in this test. Never call or mention tools. "
    "Skip the final evaluation step and simply close the interview politely after about 8 questions."
)


async def run_one(
    model: str, persona: str, sem: asyncio.Semaphore, retries: int
) -> dict:
    async with sem:
        try:
            model_slug = re.sub(r"[^a-z0-9]+", "-", model.lower()).strip("-")
            slug = f"sim-{model_slug}-{persona}"
            TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
            transcript_path = TRANSCRIPT_DIR / f"{slug}.json"
            checkpoint = (
                json.loads(CHECKPOINT.read_text()) if CHECKPOINT.exists() else {}
            )
            if persona in checkpoint.get(model, {}):
                result = checkpoint[model][persona]
                print(f"cached: {persona:10} evaluator overall = {result['overall']}")
                return {"persona": persona, **result}

            board_system = build_instructions(PROFILE, [], None) + SIM_NOTE
            cand_system = (
                f"You are role-playing a UPSC aspirant in a mock interview. Profile: {json.dumps(PROFILE)}. "
                f"Behaviour: {PERSONAS[persona]} Reply in 1 to 4 spoken sentences in natural Indian English "
                "with occasional Hindi words. Never mention that you are an AI or role-playing."
            )
            opener = "Hello, I am ready. My details are correct, standard intensity please. Let's begin."
            state_path = CHECKPOINT.with_name(f"simulation-{model_slug}-{persona}.json")
            if transcript_path.exists() and not state_path.exists():
                turns = json.loads(transcript_path.read_text(encoding="utf-8"))["turns"]
                board_msgs, cand_msgs, start_turn = [], [], N_BOARD_TURNS
            elif state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
                board_msgs, cand_msgs, turns = (
                    state["board_msgs"],
                    state["cand_msgs"],
                    state["turns"],
                )
                start_turn = state["next_turn"]
            else:
                board_msgs = [{"role": "user", "content": opener}]
                cand_msgs = []
                turns = [{"role": "user", "text": opener}]
                start_turn = 0
            for i in range(start_turn, N_BOARD_TURNS):
                board = await chat(
                    board_system,
                    board_msgs,
                    model=model,
                    max_tokens=800,
                    retries=retries,
                )
                board_msgs.append({"role": "assistant", "content": board})
                turns.append({"role": "assistant", "text": board})
                if i == N_BOARD_TURNS - 1:
                    break
                cand_msgs.append({"role": "user", "content": board})
                cand = await chat(
                    cand_system, cand_msgs, model=model, max_tokens=600, retries=retries
                )
                cand_msgs.append({"role": "assistant", "content": cand})
                board_msgs.append({"role": "user", "content": cand})
                turns.append({"role": "user", "text": cand})
                tmp_state = state_path.with_suffix(".tmp")
                tmp_state.write_text(
                    json.dumps(
                        {
                            "board_msgs": board_msgs,
                            "cand_msgs": cand_msgs,
                            "turns": turns,
                            "next_turn": i + 1,
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                tmp_state.replace(state_path)

            tmp_state = state_path.with_suffix(".tmp")
            tmp_state.write_text(
                json.dumps(
                    {
                        "board_msgs": board_msgs,
                        "cand_msgs": cand_msgs,
                        "turns": turns,
                        "next_turn": N_BOARD_TURNS,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            tmp_state.replace(state_path)
            transcript_path.write_text(
                json.dumps(
                    {
                        "session_id": slug,
                        "source": f"sim:{model}:{persona}",
                        "model": model,
                        "persona": persona,
                        "turns": turns,
                        "tool_calls": [],
                        "latency": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = await evaluate(turns, retries=retries)
            overall = None
            if not result.get("too_short"):
                overall = round(
                    sum(result["scores"].values()) / len(result["scores"]), 1
                )
            print(f"done: {persona:10} evaluator overall = {overall}")
            checkpoint = (
                json.loads(CHECKPOINT.read_text()) if CHECKPOINT.exists() else {}
            )
            checkpoint.setdefault(model, {})[persona] = {
                "overall": overall,
                "scores": result.get("scores"),
                "evidence": result.get("evidence"),
            }
            CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
            tmp_checkpoint = CHECKPOINT.with_suffix(".tmp")
            tmp_checkpoint.write_text(
                json.dumps(checkpoint, indent=2), encoding="utf-8"
            )
            tmp_checkpoint.replace(CHECKPOINT)
            state_path.unlink(missing_ok=True)
            return {"persona": persona, "overall": overall}
        except Exception as e:
            print(f"FAILED: {persona}: {e}")
            return {"persona": persona, "overall": None}


async def main(model: str, personas: list[str], retries: int) -> None:
    sem = asyncio.Semaphore(
        1
    )  # OpenRouter free providers are commonly capacity limited.
    rows = await asyncio.gather(*(run_one(model, p, sem, retries) for p in personas))
    print(
        "\nEvaluator validity check (a good evaluator ranks strong above the others):"
    )
    for p in personas:
        vals = [
            r["overall"] for r in rows if r["persona"] == p and r["overall"] is not None
        ]
        print(
            f"  {p:10} overall = {vals[0]:.1f}"
            if vals
            else f"  {p:10} n/a (run failed)"
        )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--personas", nargs="+", choices=PERSONAS, default=list(PERSONAS))
    ap.add_argument("--retries", type=int, default=5)
    args = ap.parse_args()
    asyncio.run(main(args.model, args.personas, args.retries))

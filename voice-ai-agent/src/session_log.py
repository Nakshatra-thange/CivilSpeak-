import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT_DIR = ROOT / "data" / "transcripts"


def _text_of(content) -> str:
    if isinstance(content, str):
        return content.strip()
    parts = []
    for c in content or []:
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, dict):
            parts.append(str(c.get("text", "")))
    return " ".join(p.strip() for p in parts if p and p.strip())


def history_to_turns(history_dict: dict) -> tuple[list[dict], list[str]]:
    """Convert LiveKit's session.history.to_dict() into simple turns and tool-call names.
    role 'assistant' = the board, role 'user' = the candidate."""
    turns, tool_calls = [], []
    for item in history_dict.get("items", []):
        kind = item.get("type")
        if kind == "message" and item.get("role") in ("user", "assistant"):
            text = _text_of(item.get("content"))
            if text:
                turns.append({"role": item["role"], "text": text})
        elif kind == "function_call":
            tool_calls.append(item.get("name", "?"))
    return turns, tool_calls


def candidate_answer_count(turns: list[dict]) -> int:
    """Count responses to interview questions, excluding language and intensity setup."""
    intensity_prompt = max(
        (
            i
            for i, turn in enumerate(turns)
            if turn["role"] == "assistant" and "intensity" in turn["text"].lower()
        ),
        default=-1,
    )
    if intensity_prompt < 0:
        return 0
    intensity_response = next(
        (
            i
            for i in range(intensity_prompt + 1, len(turns))
            if turns[i]["role"] == "user"
        ),
        len(turns),
    )
    return sum(turn["role"] == "user" for turn in turns[intensity_response + 1 :])


def attach_logging(
    ctx, session, session_id: str, on_shutdown=None, persist_transcript: bool = True
) -> None:
    """Call right after session.start(). Saves transcript, tool calls and latency on shutdown."""
    latency = {"eou_delay": [], "llm_ttft": [], "tts_ttfb": []}
    started = time.time()

    @session.on("metrics_collected")
    def _on_metrics(ev):
        m = getattr(ev, "metrics", None)
        if m is None:
            return
        for attrs, key in (
            (("end_of_utterance_delay", "end_of_turn_delay"), "eou_delay"),
            (("ttft", "llm_node_ttft"), "llm_ttft"),
            (("ttfb", "tts_node_ttfb"), "tts_ttfb"),
        ):
            v = next(
                (getattr(m, attr, None) for attr in attrs if getattr(m, attr, None)),
                None,
            )
            if isinstance(v, (int, float)) and v > 0:
                latency[key].append(round(float(v), 3))

    async def _write_transcript():
        if not persist_transcript:
            return
        turns, tool_calls = history_to_turns(session.history.to_dict())
        if not turns:
            return
        TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "session_id": session_id,
            "source": "live",
            "duration_s": round(time.time() - started),
            "turns": turns,
            "tool_calls": tool_calls,
            "latency": latency,
        }
        (TRANSCRIPT_DIR / f"{session_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if on_shutdown:
            await on_shutdown(turns)

    ctx.add_shutdown_callback(_write_transcript)


def recent_board_questions(n_sessions: int = 3, per_session: int = 12) -> list[str]:
    """Questions the board asked in the last few live interviews."""
    if not TRANSCRIPT_DIR.exists():
        return []
    files = sorted(
        TRANSCRIPT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    questions, used = [], 0
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("source", "live") != "live":
            continue
        used += 1
        found = []
        for t in data.get("turns", []):
            if t["role"] == "assistant":
                qs = re.findall(r"[^.?!]*\?", t["text"])
                if qs:
                    found.append(qs[-1].strip()[:140])
        questions.extend(found[:per_session])
        if used >= n_sessions:
            break
    return questions

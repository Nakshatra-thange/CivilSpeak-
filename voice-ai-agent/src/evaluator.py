import json
import os

from llm_client import DEFAULT_MODEL as LLM_DEFAULT
from llm_client import chat

DIMENSIONS = ["clarity", "depth", "balance", "awareness", "authenticity", "composure"]
DEFAULT_MODEL = os.getenv("EVALUATOR_MODEL", LLM_DEFAULT)
MIN_CANDIDATE_TURNS = 3

SYSTEM = """You are a senior, strict evaluator of UPSC Civil Services Personality Test (interview) performances.
You receive the transcript of a mock interview between a BOARD (an AI chairperson) and a CANDIDATE.
The transcript comes from speech recognition of Indian-accented English/Hinglish. Ignore minor transcription errors and odd spellings. Judge substance only. Hindi may appear in Roman or Devanagari script.

Score the CANDIDATE on six dimensions, each an integer from 0 to 10:
- clarity: structured, to-the-point answers
- depth: analytical depth beyond surface facts
- balance: sees multiple sides, avoids one-sided or extreme views
- awareness: knowledge of own background, state, current issues and governance
- authenticity: honest, genuine, not memorised or bluffing; admits uncertainty
- composure: calm and confident under cross-questioning

Calibration: 0-3 weak, 4-5 below average, 6-7 solid, 8-9 excellent, 10 exceptional. Most real candidates land between 4 and 7. Do not inflate scores. Vague, generic or buzzword answers without examples must score low on depth. Bluffing or confidently wrong facts must score low on authenticity.

Only report a factual slip if you are highly confident the candidate stated something wrong. Quote it briefly and give the correction. If unsure, leave it out.

For every score, give one short direct evidence quote from the candidate's transcript. If the transcript does not support a high score, score conservatively. Do not infer strengths from the board's wording.

Return ONLY a JSON object, no other text, in exactly this shape:
{"scores": {"clarity": 0, "depth": 0, "balance": 0, "awareness": 0, "authenticity": 0, "composure": 0},
 "evidence": {"clarity": "candidate quote", "depth": "candidate quote", "balance": "candidate quote", "awareness": "candidate quote", "authenticity": "candidate quote", "composure": "candidate quote"},
 "summary": "one or two sentences",
 "strengths": ["short point", "short point"],
 "improvements": ["short actionable point", "short actionable point"],
 "factual_slips": [{"claim": "what they said", "correction": "what is correct"}],
 "topics": ["topic", "topic"]}"""


def format_transcript(turns: list[dict]) -> str:
    return "\n".join(
        f"{'BOARD' if t['role'] == 'assistant' else 'CANDIDATE'}: {t['text']}"
        for t in turns
    )


def extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


async def evaluate(
    turns: list[dict], model: str | None = None, timeout: float = 45.0, retries: int = 2
) -> dict:
    if sum(1 for t in turns if t["role"] == "user") < MIN_CANDIDATE_TURNS:
        return {"too_short": True}
    prompt = "Transcript:\n\n" + format_transcript(turns)
    last_err = None
    for _ in range(2):  # retry once on malformed output
        text = await chat(
            SYSTEM,
            [{"role": "user", "content": prompt}],
            model=model or DEFAULT_MODEL,
            max_tokens=3000,
            timeout=timeout,
            retries=retries,
            temperature=0,
            seed=47,
        )
        try:
            data = extract_json(text)
            scores = {d: max(0, min(10, int(data["scores"][d]))) for d in DIMENSIONS}
            return {
                "too_short": False,
                "scores": scores,
                "evidence": {
                    d: str(data.get("evidence", {}).get(d, ""))[:300]
                    for d in DIMENSIONS
                },
                "summary": str(data.get("summary", "")),
                "strengths": list(data.get("strengths", []))[:3],
                "improvements": list(data.get("improvements", []))[:3],
                "factual_slips": list(data.get("factual_slips", []))[:3],
                "topics": [str(t) for t in data.get("topics", [])][:8],
                "model": model or DEFAULT_MODEL,
            }
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Evaluator returned invalid output: {last_err}")

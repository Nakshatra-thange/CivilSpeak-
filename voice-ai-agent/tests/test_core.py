import asyncio
import time
from types import SimpleNamespace

import pytest
from livekit.agents import StopResponse
from stt_eval import normalize, term_recall

import db
import llm_client
from agent import Assistant
from evaluator import extract_json
from prompts import build_instructions
from session_log import candidate_answer_count, history_to_turns


def test_history_to_turns_and_tool_calls():
    turns, calls = history_to_turns(
        {
            "items": [
                {"type": "message", "role": "user", "content": "Hello"},
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"text": "Tell me more."}],
                },
                {"type": "function_call", "name": "finish_interview"},
            ]
        }
    )
    assert turns == [
        {"role": "user", "text": "Hello"},
        {"role": "assistant", "text": "Tell me more."},
    ]
    assert calls == ["finish_interview"]


def test_candidate_answer_count_skips_setup():
    turns = [
        {"role": "user", "text": "Hello"},
        {"role": "assistant", "text": "Which language and intensity do you prefer?"},
        {"role": "user", "text": "English, standard"},
        {"role": "assistant", "text": "What is your view on federalism?"},
        {"role": "user", "text": "It balances diversity and unity."},
        {"role": "assistant", "text": "How would you handle a flood?"},
        {"role": "user", "text": "I would coordinate relief."},
    ]
    assert candidate_answer_count(turns) == 2


@pytest.mark.asyncio
async def test_interview_length_triggers_code_enforced_close():
    items = [SimpleNamespace(role="assistant", text_content="Choose your intensity?")]
    items.append(SimpleNamespace(role="user", text_content="Standard"))
    for question in range(10):
        items.append(
            SimpleNamespace(role="assistant", text_content=f"Question {question}?")
        )
        items.append(SimpleNamespace(role="user", text_content=f"Answer {question}"))
    history = [
        {"type": "message", "role": item.role, "content": item.text_content}
        for item in items
    ]
    context = SimpleNamespace(items=items, to_dict=lambda: {"items": history})
    completed = []

    async def close_automatically(turns):
        completed.extend(turns)

    agent = SimpleNamespace(
        started_at=time.monotonic(),
        auto_closing=False,
        _close_automatically=close_automatically,
    )
    with pytest.raises(StopResponse):
        await Assistant.on_user_turn_completed(
            agent, context, SimpleNamespace(text_content="Final answer")
        )
    await asyncio.sleep(0)
    assert agent.auto_closing is True
    assert completed[-1] == {"role": "user", "text": "Final answer"}


def test_stt_normalization_and_devanagari_aliases():
    assert normalize("  Article—21! ") == "article21"
    assert term_recall("Directive Principles|नीति निर्देशक तत्व", "नीति निर्देशक तत्व") == 1


def test_extract_json_with_surrounding_text():
    assert extract_json('result: {"score": 7} done') == {"score": 7}


def test_build_instructions_includes_history_and_variety():
    prompt = build_instructions(
        {"name": "Asha"},
        [{"overall": 6.0, "weakest": "depth", "topics": "federalism"}],
        "depth",
        past_questions=["What is federalism?"],
        focus_areas=["district administration"],
    )
    assert "Saved details: name: Asha" in prompt
    assert "What is federalism?" in prompt
    assert "district administration" in prompt
    assert "SPEECH RECOGNITION NOTE" in prompt


def test_db_profile_and_interview_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.save_profile({"name": "Asha", "hometown": "Pune"})
    db.save_profile({"name": "Asha Rao", "education": "Economics"})
    assert db.get_profile()["name"] == "Asha Rao"
    assert db.get_profile()["hometown"] == "Pune"
    scores = dict.fromkeys(db.DIMENSIONS, 6)
    assert db.save_interview("standard", scores, "governance", "clear") == (
        6.0,
        "clarity",
    )
    assert db.weakest_dimension() == "clarity"
    assert db.recent_interviews()[0]["topics"] == "governance"


@pytest.mark.asyncio
async def test_openrouter_retries_and_honors_retry_after(monkeypatch):
    waits = []
    responses = [
        type("Response", (), {"status_code": 429, "headers": {"Retry-After": "5"}})(),
        type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {},
                "json": lambda self: {"choices": [{"message": {"content": "ok"}}]},
            },
        )(),
    ]

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return responses.pop(0)

    async def fake_sleep(seconds):
        waits.append(seconds)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", Client)
    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(llm_client.random, "random", lambda: 0)
    monkeypatch.setattr(llm_client, "_last_request_at", 0)
    monkeypatch.setattr(llm_client, "MIN_REQUEST_INTERVAL", 0)
    assert await llm_client.chat("system", [], retries=2) == "ok"
    assert 5 in waits

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from livekit.agents import room_io
from livekit.plugins import noise_cancellation

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ChatContext,
    ChatMessage,
    JobContext,
    RunContext,
    StopResponse,
    STTContextOptions,
    TurnHandlingOptions,
    cli,
    function_tool,
    inference,
    room_io,
)
from livekit.plugins import ai_coustics, sarvam

import db
from evaluator import evaluate
from prompts import build_instructions, pick_focus_areas
from session_log import (
    attach_logging,
    candidate_answer_count,
    history_to_turns,
    recent_board_questions,
)

# ============================================================
# CONFIG
# ============================================================

load_dotenv(".env.local")

logger = logging.getLogger("upsc-board")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in {"1", "true", "yes"}
MEMORY_ENABLED = os.getenv("ENABLE_MEMORY", "0").lower() in {"1", "true", "yes"} and not DEMO_MODE
logger.info("memory: %s", "ON" if MEMORY_ENABLED else "OFF")

EVALS_DIR = Path(__file__).resolve().parent.parent / "data" / "evals"


# ============================================================
# ASSISTANT
# ============================================================


class Assistant(Agent):
    def __init__(self) -> None:

        super().__init__(
            llm=inference.LLM(model="google/gemma-4-31b-it"),
            instructions=build_instructions(
                db.get_profile() if MEMORY_ENABLED else {},
                db.recent_interviews() if MEMORY_ENABLED else [],
                db.weakest_dimension() if MEMORY_ENABLED else None,
                past_questions=recent_board_questions() if MEMORY_ENABLED else [],
                focus_areas=pick_focus_areas(),
            ),
        )

        self.session_id = uuid.uuid4().hex[:8]
        self.started_at = time.monotonic()
        self.intensity = "standard"
        self.evaluation_saved = False
        self.auto_closing = False
        self.auto_close_task = None

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message: ChatMessage
    ) -> None:
        """Enforce a maximum interview length before the board generates its next reply."""
        items = turn_ctx.items
        intensity_index = max(
            (
                i
                for i, item in enumerate(items)
                if getattr(item, "role", None) == "assistant"
                and "intensity" in (getattr(item, "text_content", "") or "").lower()
            ),
            default=-1,
        )
        question_count = sum(
            1
            for item in items[intensity_index + 1 :]
            if getattr(item, "role", None) == "assistant"
            and "?" in (getattr(item, "text_content", "") or "")
        )
        if intensity_index >= 0 and (
            question_count >= 10 or time.monotonic() - self.started_at >= 12 * 60
        ):
            self.auto_closing = True
            turns, _ = history_to_turns(turn_ctx.to_dict())
            latest = getattr(new_message, "text_content", "") or ""
            turns.append({"role": "user", "text": latest})
            self.auto_close_task = asyncio.create_task(self._close_automatically(turns))
            raise StopResponse()

    async def _close_automatically(self, turns: list[dict]) -> None:
        session = self.session
        try:
            await session.say("Thank you. The board will take a moment to deliberate.")
            result = await self._evaluate_and_save(turns, timeout=45, retries=3)
            if result.get("scores"):
                message = (
                    f"Your overall score is {result['overall']} out of 10. "
                    f"Your strongest area was {', '.join(result['strengths']) or 'your interview performance'}. "
                    f"Your area to improve is {result['weakest']}. "
                    f"{'; '.join(result['improvements'])}"
                )
            else:
                message = (
                    "I could not retrieve the full score right now. The interview has been saved "
                    "for evaluation after the call. Please review your answers for clarity and examples."
                )
            await session.say(message)
        except Exception:
            logger.exception("automatic interview close failed")
        finally:
            await session.shutdown(drain=True)

    async def _evaluate_and_save(
        self, turns: list[dict], *, timeout: float, retries: int
    ) -> dict:
        eval_path = EVALS_DIR / f"{self.session_id}.json"
        if self.evaluation_saved and eval_path.exists():
            return json.loads(eval_path.read_text(encoding="utf-8"))
        answer_count = candidate_answer_count(turns)
        if MEMORY_ENABLED:
            EVALS_DIR.mkdir(parents=True, exist_ok=True)
        if answer_count < 3:
            return {"too_short": True}
        try:
            result = await evaluate(turns, timeout=timeout, retries=retries)
            if result.get("too_short"):
                return result
            overall = round(sum(result["scores"].values()) / len(result["scores"]), 1)
            weakest = min(result["scores"], key=result["scores"].get)
            if MEMORY_ENABLED:
                overall, weakest = await asyncio.to_thread(
                    db.save_interview,
                    self.intensity,
                    result["scores"],
                    ", ".join(result["topics"]),
                    result["summary"],
                )
            record = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "intensity": self.intensity,
                "overall": overall,
                "weakest": weakest,
                **result,
            }
            if MEMORY_ENABLED:
                eval_path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                self.evaluation_saved = True
                logger.info("Interview evaluation saved: %s", eval_path)
            return record
        except Exception as exc:
            logger.exception("evaluation failed for session %s", self.session_id)
            record = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "session_id": self.session_id,
                "intensity": self.intensity,
                "evaluation_failed": True,
                "error": str(exc)[:300],
                "candidate_answers": answer_count,
            }
            if MEMORY_ENABLED:
                eval_path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            return record

    # ========================================================
    # SAVE PROFILE
    # ========================================================

    @function_tool
    async def save_profile(
        self,
        context: RunContext,
        name: str = "",
        hometown: str = "",
        education: str = "",
        optional_subject: str = "",
        hobbies: str = "",
        work_experience: str = "",
        service_preference: str = "",
        medium: str = "",
    ) -> str:
        """Save the candidate's background details so they do not have to repeat them next time.
        Fill only the fields the candidate has actually shared.

        Args:
            name: Candidate's name.
            hometown: Hometown, district or home state.
            education: Graduation subject and college.
            optional_subject: UPSC optional subject, if any.
            hobbies: Hobbies and interests.
            work_experience: Work experience, if any.
            service_preference: Preferred services, for example IAS or IFS.
            medium: Preferred interview language, English or Hindi.
        """

        fields = {
            "name": name,
            "hometown": hometown,
            "education": education,
            "optional_subject": optional_subject,
            "hobbies": hobbies,
            "work_experience": work_experience,
            "service_preference": service_preference,
            "medium": medium,
        }

        if MEMORY_ENABLED:
            await asyncio.to_thread(db.save_profile, fields)

        return "Saved."

    # ========================================================
    # FINISH INTERVIEW
    # ========================================================

    @function_tool
    async def finish_interview(
        self,
        context: RunContext,
        intensity: str,
    ) -> str:
        """Evaluate and save the interview after the board closes or the candidate asks to stop.
        The live attempt is brief; shutdown retries and persists an evaluation artifact.

        Args:
            intensity: gentle, standard or tough.
        """

        # ----------------------------------------------------
        # Get current session
        # ----------------------------------------------------

        session = getattr(context, "session", None) or self.session

        # ----------------------------------------------------
        # Extract conversation history
        # ----------------------------------------------------

        turns, _ = history_to_turns(session.history.to_dict())

        # ----------------------------------------------------
        # Evaluate interview
        # ----------------------------------------------------

        self.intensity = intensity.lower().strip()
        if self.intensity not in db.INTENSITIES:
            self.intensity = "standard"
        try:
            result = await asyncio.wait_for(
                self._evaluate_and_save(turns, timeout=10, retries=1), timeout=12
            )
        except Exception:
            logger.exception("in-call evaluation timed out")
            return "Evaluation is taking longer than expected. Give brief qualitative feedback only and do not mention scores. The full evaluation will be saved after the call."

        # ----------------------------------------------------
        # Check whether there were enough answers
        # ----------------------------------------------------

        if result.get("too_short"):
            return (
                "Too few answers to evaluate. "
                "Tell the candidate you need a few more answers "
                "and continue the interview."
            )
        if result.get("evaluation_failed"):
            return "Evaluation is unavailable right now. Give brief qualitative feedback only and do not mention any scores. The full evaluation will be saved after the call."

        overall, weakest = result["overall"], result["weakest"]

        # ----------------------------------------------------
        # Format factual slips
        # ----------------------------------------------------

        slips = (
            "; ".join(
                f"{s.get('claim', '')} -> {s.get('correction', '')}"
                for s in result["factual_slips"]
            )
            or "none"
        )

        # ----------------------------------------------------
        # Return evaluation to LLM
        # ----------------------------------------------------

        return (
            f"EVALUATION SAVED. "
            f"Overall {overall} out of 10. "
            f"Weakest area: {weakest}. "
            f"Strengths: {'; '.join(result['strengths'])}. "
            f"Improvements: {'; '.join(result['improvements'])}. "
            f"Factual slips: {slips}."
        )


# ============================================================
# LIVEKIT SERVER
# ============================================================

server = AgentServer()


# ============================================================
# VOICE SESSION
# ============================================================


@server.rtc_session(agent_name="voice-ai-agent")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info(
        "Starting UPSC interview in room: %s",
        ctx.room.name,
    )

    # ========================================================
    # AGENT SESSION
    # ========================================================

    session = AgentSession(
        # ----------------------------------------------------
        # SARVAM STT
        # ----------------------------------------------------
        stt=sarvam.STT(
            language="en-IN",
            model="saaras:v4",
            mode="codemix",
            sample_rate=16000,
            high_vad_sensitivity=True,
        ),
        # ----------------------------------------------------
        # STT CONTEXT
        # ----------------------------------------------------
        stt_context_options=STTContextOptions(
            keyterms=[
                "LiveKit",
                "UPSC",
                "IAS",
                "IPS",
                "IFS",
                "DAF",
                "Python",
                "Java",
                "JavaScript",
                "React",
                "machine learning",
                "artificial intelligence",
                "algorithms",
                "data structures",
                "civil services",
                "fundamental rights",
                "Article 21",
                "Parliament",
                "Supreme Court",
                "fiscal deficit",
                "GDP",
                "inflation",
                "governance",
                "democracy",
                "federalism",
                "constitution",
            ],
            keyterm_detection={
                "enabled": True,
            },
        ),
        # ----------------------------------------------------
        # SARVAM TTS
        # ----------------------------------------------------
        tts=sarvam.TTS(
            target_language_code="hi-IN",
            model="bulbul:v3",
            speaker="shubh",
            speech_sample_rate=22050,
            pace=1.0,
        ),
        # ----------------------------------------------------
        # TURN DETECTION
        # ----------------------------------------------------
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            interruption={
                "mode": "adaptive",
            },
            preemptive_generation={
                "enabled": True,
            },
            endpointing={
                "mode": "fixed",
                "min_delay": 1.5,  # wait at least 1.5 s of silence before treating your turn as finished
                "max_delay": 6.0,  # upper bound when the turn detector thinks you are mid-thought
            },
        ),
        # ----------------------------------------------------
        # EXPRESSIVE VOICE
        # ----------------------------------------------------
        expressive=True,
    )

    # ========================================================
    # CREATE ASSISTANT
    # ========================================================

    if MEMORY_ENABLED:
        db.init_db()
    assistant = Assistant()

    # ========================================================
    # START SESSION
    # ========================================================

    await session.start(
        agent=assistant,
        room=ctx.room,
        record=not DEMO_MODE,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=(
                    ai_coustics.audio_enhancement(
                        model=(ai_coustics.EnhancerModel.QUAIL_VF_S)
                    )
                ),
            ),
        ),
    )

    # ========================================================
    # ATTACH SESSION LOGGING
    # ========================================================

    attach_logging(
        ctx,
        session,
        assistant.session_id,
        on_shutdown=(
            None
            if not MEMORY_ENABLED
            else lambda turns: assistant._evaluate_and_save(
                turns, timeout=45, retries=3
            )
        ),
        persist_transcript=MEMORY_ENABLED,
    )

    # ========================================================
    # CONNECT
    # ========================================================

    await ctx.connect()

    if DEMO_MODE:

        async def _demo_session_cap():
            await asyncio.sleep(15 * 60)
            handle = session.generate_reply(
                instructions=(
                    "The 15-minute demo limit has been reached. Thank the candidate briefly, "
                    "say the mock interview is ending, and do not call any tools."
                ),
                tool_choice="none",
            )
            try:
                await asyncio.wait_for(handle, timeout=20)
            except asyncio.TimeoutError:
                logger.warning("demo close speech exceeded its deadline")
            await session.shutdown(drain=True)

        cap_task = asyncio.create_task(_demo_session_cap())

        @session.on("close")
        def _cancel_demo_cap(_event):
            if asyncio.current_task() is not cap_task:
                cap_task.cancel()

    logger.info(
        "Connected to LiveKit room: %s",
        ctx.room.name,
    )

    # ========================================================
    # INITIAL GREETING
    # ========================================================

    await session.generate_reply(
        instructions=(
            "Greet the candidate in one or two short sentences "
            "as the chairperson of the mock UPSC interview board, "
            "then follow your setup steps."
        )
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    cli.run_app(server)

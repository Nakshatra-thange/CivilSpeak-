# UPSC Interview Mock: a voice AI board that scores you

A real-time voice agent that conducts a mock UPSC Personality Test (interview) in English and Hinglish. The AI "board chairperson" asks questions generated from the candidate's introduction and live answers, and cross-questions what they say. A separate evaluator model then scores the interview on six dimensions, and the board speaks the feedback.

- Live demo: [FILL: link, or "available on request"]
- Walkthrough (Loom): [FILL: link]
- Built by [FILL: name] as my first voice agent, for the SuperKalam AI/ML internship application.

## Why this

The interview is the final stage of the UPSC Civil Services Exam. Practice for it usually means a booked panel session with limited slots. A voice agent can give an aspirant a repeatable practice round at any hour, in the way aspirants actually speak: English mixed with Hindi.

## What it does

- Real-time spoken conversation in English, Hindi or Hinglish.
- Collects the candidate's introduction at the start of each session (name, hometown, education, optional subject, hobbies, work experience, service preference).
- Generates every question with an LLM. There is no fixed question bank. Each session gets random focus areas, and in local mode it also avoids questions from earlier sessions.
- Three intensities: gentle, standard, tough.
- Stays neutral mid-interview (no praise or hints), asks one question at a time, and cross-questions vague or wrong claims.
- Ends after roughly 8 to 10 questions, then scores the interview (see Scoring).
- A Streamlit dashboard shows interview history, scores, transcripts and eval results (local mode).
- A web demo with an access-code gate, a 15-minute session cap, and no storage between visitors.

## Architecture

```text
Mic -> LiveKit -> VAD -> Sarvam STT (saaras:v4, codemix, en-IN) -> turn detector
    -> LLM (the board) -> Sarvam TTS -> Speaker

Local mode only: SQLite stores the candidate profile and past interviews.
Tools: save_profile, finish_interview
After the interview: transcript -> separate evaluator LLM (OpenRouter) -> six scores -> spoken feedback
Interruption handling runs in parallel and cancels the board's speech.
```

| Part | Choice |
|---|---|
| Real-time transport and agent framework | LiveKit Agents (Python) |
| STT / TTS | Sarvam (saaras:v4 codemix / bulbul:v3) |
| Interview LLM | Gemma via LiveKit Inference |
| Evaluator, judge, simulation | nvidia/nemotron-3.5-lightning:free via OpenRouter |
| Storage (local mode) | SQLite |
| Dashboard | Streamlit |
| Web demo | Next.js (LiveKit agent starter) with access-code gate |

## Scoring

### The scorecard

The candidate gets a score from 0 to 10 on each of six dimensions.

| Dimension | What it measures |
|---|---|
| Clarity | Structured, to-the-point answers |
| Depth | Analytical depth beyond surface facts |
| Balance | Sees multiple sides, avoids one-sided or extreme views |
| Awareness | Knowledge of own background, state, current issues and governance |
| Authenticity | Honest and genuine, not memorised, no bluffing, admits uncertainty |
| Composure | Calm and confident under cross-questioning |

Scale: 0 to 3 weak, 4 to 5 below average, 6 to 7 solid, 8 to 9 excellent, 10 exceptional. Most real candidates should land between 4 and 7. The rubric says vague or buzzword answers with no examples must score low on depth, and bluffing or confidently wrong facts must score low on authenticity.

The **overall score** is the mean of the six. The **weakest area** is the lowest dimension, and in local mode it is probed more in the next session.

### How scores are produced

1. The conversation is saved as a transcript.
2. A **separate evaluator model**, not the interviewer, reads the transcript with a strict rubric and returns JSON: six scores, a summary, strengths, improvements, possible factual slips, and topics covered. The prompt requires evidence for each score.
3. Scores are validated (integers, clamped to 0 to 10). Output that is not valid JSON is retried once.
4. Interviews with fewer than three candidate answers are not scored.
5. The board speaks the feedback using only what the evaluator returned: strongest and weakest areas, two improvements, any factual slip, and the overall score.

Why a separate evaluator: when the interviewer scored itself, it lost count of questions and drifted from its neutral tone.

### Status of the scoring

The scoring pipeline is implemented, but the evaluator has **not yet been validated**:

- A planned check, in which scripted candidates (strong, vague, bluffer, one-sided) are scored to see whether the evaluator ranks them correctly, was only partly completed. The free-tier model returned rate-limit errors (HTTP 429) on most runs. The one persona that finished (vague) received 7.0 out of 10, which was too generous, so the evaluator prompt was tightened to require evidence for each score. The full comparison remains a next step.
- The evaluator is an LLM judge on a free-tier model and has not been compared with human UPSC evaluators. Read its scores as indicative.
- The transcript comes from speech recognition, so mishearings can affect scores. The evaluator is told to ignore minor transcription errors.
- Next step: collect scores from human evaluators (for example former aspirants) on the same transcripts and measure agreement.

## Results

All numbers come from my own runs. The samples are small.

### Speech recognition on UPSC vocabulary

12 clips, one speaker, read aloud on a laptop mic: Indian-accented English/Hinglish with UPSC terms. **Term recall** is the share of key UPSC terms recognised, counting accepted spellings in Roman and Devanagari.

| Config | Term recall | WER | Median latency (s) | Devanagari share |
|---|---|---|---|---|
| v3, codemix, hi-IN | 0.806 | 0.509 | 0.465 | 0.273 |
| **v4, codemix, en-IN (chosen)** | **0.917** | **0.095** | 0.430 | **0.000** |
| v4, codemix, hi-IN | 0.917 | 0.424 | 0.390 | 0.155 |
| v4, codemix, auto language | 0.917 | 0.339 | 0.455 | 0.094 |
| v4, transcribe, hi-IN | 0.917 | 1.002 | 0.435 | 0.996 |

How to read it:
- All four v4 configs tie on term recall. I chose v4/codemix/en-IN for the lowest WER and clean single-script output.
- WER is only comparable between Roman-script outputs. Devanagari outputs are compared against a Roman reference, so their WER is not meaningful.
- Latency is batch file-upload time, not streaming. It varied a lot between runs (about 0.4 s in the latest, 2.3 to 4.3 s in an earlier one), so it was not used to choose a config.
- Real errors: "Directive Principles" was heard as "Detective" or "Deductive" in every Sarvam config, and "Tibetan plateau" became "Tibet and Plateau". The prompt tells the board to read such mishearings as the intended UPSC term.
- A planned second-vendor comparison (Deepgram) was dropped because the account could not be created.

### Interview behaviour audit

An audit of 4 real interview transcripts from an earlier build (before the final STT and turn-timing settings):

| Metric | Value |
|---|---|
| Average board turns per session | 8.75 |
| Average words per board turn | 26.5 |
| Turns with more than one question | 0 |
| Possible praise slips mid-interview | 0 |

The same audit also found that the finish step was never called in those sessions (see below). Estimated response delay in that build was about 1.6 s (end-of-turn detection, LLM first token and TTS first byte, summed from medians).

## Design decisions

1. **No fixed question bank.** The first version quizzed from a JSON file and refused anything outside it. That was a quiz engine, not an interviewer. The LLM now drives the interview.
2. **Separate evaluator**, because self-scoring was unreliable.
3. **Cascaded STT, LLM, TTS** rather than speech-to-speech, for swappable parts, saved transcripts for evals, and Indian-language provider comparison.
4. **Variety in code.** The default sampling temperature was already high, so repetition came from the prompt's fixed flow. Sessions now get random focus areas and a do-not-repeat list.
5. **Interview length enforced in code**, not left to the LLM to count.
6. **Memory is opt-in.** Persistence is off by default so a public deployment cannot expose one person's details to another.

## What went wrong, and what I changed

- Hindi recognition mode wrote English words in Devanagari ("tough" became "टफ"). Switched to code-mix mode with English-India settings.
- The agent interrupted whenever I paused to think, splitting answers into fragments. Increased the end-of-turn delay.
- My own metric scored the best mode at 0.00 because it searched for Latin-script terms and that mode outputs Devanagari. The model was fine and my measurement was wrong. I changed the metric to count accepted spellings in both scripts.
- An audit showed the finish step was called 0 times in all live sessions, so the interview never closed and no scoring ran. The LLM was not counting turns reliably. Interview length and post-call evaluation are now enforced in code.
- Questions repeated across sessions. See design decision 4.
- API credits ran out and the free-tier replacement returned HTTP 429, so I added rate limiting, retries and resumable simulations.

## Limitations

- Small evals: 12 clips from one speaker, read aloud, and a small number of real interviews.
- The scoring evaluator is unvalidated (see Status of the scoring).
- The LLM can state wrong facts, and its knowledge of recent current affairs is outdated, so the board is told to ask rather than assert.
- Accuracy depends on microphone and environment. I noticed more mishearing in a public place. This was not measured. Use a headset in a quiet room.
- Voice only: no body language or non-verbal assessment.
- Pure-Hindi speech has not been tested.
- Local mode keeps one candidate's memory in a single-user SQLite file. Multi-user use needs per-user accounts in a hosted database.
- Privacy: the evaluator model's provider may log requests, and LiveKit may retain session data according to project settings. The demo page states this.

## Where this fits CivilSpeak

SuperKalam already covers practice and Mains evaluation. This explores the last stage. Next steps I would build: DAF PDF upload instead of speaking details, a current-affairs source so questions reflect recent events, per-user memory that carries mistake patterns from practice into interview probes, and testing with Hindi-medium aspirants.

## Run it

```bash
uv sync
# .env.local: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, SARVAM_API_KEY, OPENROUTER_API_KEY
ENABLE_MEMORY=1 uv run python src/agent.py dev    # local mode with memory
uv run python src/agent.py dev                    # memory off (demo behaviour)
uv run streamlit run dashboard/app.py             # dashboard (needs local mode data)
uv run pytest -q                                  # unit tests

# evals
uv run python evals/record_clips.py me            # record 12 clips, then:
uv run python evals/stt_eval.py
uv run python evals/simulate.py
uv run python evals/judge_transcripts.py
```

Web demo: in `web-demo/`, run `npm run dev`. It needs `DEMO_ACCESS_CODE` and `DEMO_SESSION_SECRET` in its `.env.local`, plus the LiveKit variables. Agent deploy: `lk agent deploy --secrets-file .env.deploy`. Do not re-run `evals/make_manifest.py` after recording more speakers, since it overwrites the manifest.

## Layout

`src/` agent, prompts, evaluator, db, session logging, LLM client · `evals/` STT eval, simulation, judge · `dashboard/` · `clips/manifest.csv` · `results/` · `tests/` · `web-demo/`

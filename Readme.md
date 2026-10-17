# UPSC Interview Mock: a voice AI board that scores you

A real-time voice agent that conducts a mock UPSC Personality Test (interview) in English and Hinglish. The AI "board chairperson" asks questions generated from the candidate's introduction and live answers, cross-questions what they say, and a separate evaluator model then scores the interview on six dimensions and the board speaks the feedback.

- Live demo: [FILL: link, or "available on request"]
- Walkthrough (Loom): [FILL]
- Built by [FILL: name] as my first voice agent, for the SuperKalam AI/ML internship application.

## Why this

The interview is the final stage of the UPSC Civil Services Exam. Practice for it usually means a booked panel session with limited slots. A voice agent can give an aspirant a repeatable practice round at any hour, in the way aspirants actually speak: English mixed with Hindi.

## What it does

- Real-time spoken conversation in English, Hindi or Hinglish.
- Collects the candidate's introduction (name, hometown, education, optional, hobbies, work, service preference) at the start of each session.
- Generates every question with an LLM. There is no fixed question bank. Each session gets random focus areas, and locally it also avoids questions from earlier sessions.
- Three intensities: gentle, standard, tough.
- Stays neutral mid-interview (no praise or hints), asks one question at a time, and cross-questions vague or wrong claims.
- Ends after roughly 8 to 10 questions, then scores the interview (see Scoring).
- A Streamlit dashboard shows interview history, scores, transcripts and eval results (local mode).
- Web demo with an access-code gate, a 15-minute session cap, and no storage between visitors.

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
| Evaluator, judge, simulation | Free model via OpenRouter ([FILL: model name]) |
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

The **overall score** is the mean of the six. The **weakest area** is the lowest dimension, and locally it is probed more in the next session.

### How scores are produced

1. The conversation is saved as a transcript.
2. A **separate evaluator model**, not the interviewer, reads the transcript with a strict rubric and returns JSON: six scores, a summary, strengths, improvements, possible factual slips, and topics covered. The prompt requires evidence for each score.
3. Scores are validated (integers, clamped to 0 to 10). Output that is not valid JSON is retried once.
4. Interviews with fewer than three candidate answers are not scored.
5. The board speaks the feedback using only what the evaluator returned: strongest and weakest areas, two improvements, any factual slip, and the overall score.

Why a separate evaluator: when the interviewer scored itself, it lost count of questions and drifted from its neutral tone.

### Example scorecard

[FILL: one real interview, with the six scores]

| Clarity | Depth | Balance | Awareness | Authenticity | Composure | Overall | Weakest |
|---|---|---|---|---|---|---|---|
| [FILL] | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] | [FILL] |

Spoken feedback summary: [FILL: 2 lines]

### Does the evaluator discriminate?

To check the scoring itself, simulated candidates with scripted behaviours were interviewed by the board prompt and then scored by the evaluator. A useful evaluator should score the strong candidate clearly above the others.

| Simulated candidate | Behaviour | Overall score |
|---|---|---|
| Strong | Structured, examples, multi-sided, admits uncertainty | [FILL] |
| Vague | Generic buzzwords, no depth | [FILL] |
| Bluffer | Confident wrong facts, bluffs when unsure | [FILL] |
| One-sided | Extreme opinions, ignores the other side | [FILL] |

[FILL: one honest sentence on whether this ranked correctly. An early partial run scored the vague persona 7.0 out of 10, which was too generous, so the prompt was tightened to require evidence for each score.]

### Scoring caveats

- The evaluator is an LLM judge on a free-tier model. It has not been compared with human UPSC evaluators, so read the scores as indicative.
- The simulated candidates are scripted by an LLM, which tests consistency, not real-world accuracy.
-
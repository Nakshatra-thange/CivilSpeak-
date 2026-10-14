# Evaluation summary

Generated from the result files currently present in this repository.

## STT benchmark

| system | clips | term_recall | wer | median_latency_s | devanagari_share | errors |
| --- | --- | --- | --- | --- | --- | --- |
| sarvam_v3_codemix_hi-IN | 12 | 0.806 | 0.509 | 3.91 | 0.273 | 0.0 |
| sarvam_v4_codemix_en-IN | 12 | 0.917 | 0.095 | 2.295 | 0.0 | 0.0 |
| sarvam_v4_codemix_hi-IN | 12 | 0.917 | 0.424 | 2.955 | 0.155 | 0.0 |
| sarvam_v4_codemix_unknown | 12 | 0.917 | 0.339 | 3.205 | 0.094 | 0.0 |
| sarvam_v4_transcribe_hi-IN | 12 | 0.917 | 1.002 | 4.27 | 0.996 | 0.0 |

## Interview behavior audit

| session | group | board_turns | avg_words_per_board_turn | multi_question_turns | possible_praise_slips | finish_interview_calls | save_profile_calls | median_eou_delay_s | median_llm_ttft_s | median_tts_ttfb_s | est_response_latency_s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0a7f0b62 | live | 7 | 30.9 | 0 | 0 | 0.0 | 0.0 | 0.48 | 0.59 | 0.22 | 1.29 |
| 427a7ac8 | live | 5 | 31.8 | 0 | 0 | 0.0 | 0.0 | 0.47 | 0.59 | 0.21 | 1.27 |
| 60f8815b | live | 20 | 24.4 | 0 | 0 | 0.0 | 1.0 | 0.48 | 0.59 | 0.22 | 1.29 |
| d805055c | live | 3 | 18.7 | 0 | 0 | 0.0 | 0.0 | 1.48 | 0.72 | 0.21 | 2.41 |
| sim-nvidia-nemotron-3-5-lightning-free-vague | nvidia/nemotron-3.5-lightning:free | 9 | 42.3 | 4 | 1 |  |  |  |  |  |  |

## Evaluator persona validity

_No completed personas yet. Re-run to resume from checkpoints._

## Caveats

- The STT benchmark contains 12 read-aloud clips from one speaker. It is not a Hindi-medium or streaming-latency benchmark.
- WER is script-sensitive; do not compare across Devanagari and Latin transcript scripts.
- Synthetic interviews measure prompt compliance on the selected simulation model, not production LiveKit Gemma.
- Persona scores are small samples. A useful evaluator should rank the strong persona above vague, bluffing, and one-sided personas; do not claim validity if the observed run fails this check.
- OpenRouter free-model requests are subject to account caps and upstream capacity. Simulation checkpoints retain completed personas and in-progress turns for resumption.
- Latency values from recorded calls are component timing summaries; the sum is an estimate, not end-to-end streaming latency.
- Simulated and live rows must be interpreted separately.

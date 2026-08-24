# Four-engine acceptance test guide

Use the exact source files in `test-scripts/`. Do not edit the script between engines: a fair reliability comparison requires identical text and cues.

## Script settings

| Script | Accent | Mood | Pace | Expressiveness | Delivery target |
| --- | --- | --- | ---: | ---: | --- |
| 2-minute self-introduction | US | Friendly | 0.95 | 0.55 | Warm, confident, conversational |
| 8-minute Profeshare AI pitch | US | Formal | 1.00 | 0.65 | Credible, persuasive, energetic without hype |
| 15-minute design-thinking talk | US | Dramatic | 0.95 | 0.70 | TED-style: curious opening, clear teaching, inspiring close |

Mood and expressiveness are best-effort controls. Keep the settings above for every engine even when an adapter has limited support. For UK testing, repeat only the 2-minute script with UK accent after the US comparison.

## Before starting

1. Open **Settings** and confirm all four engines show **Available**.
2. Open **Voice Library** and play one preview from each preset-capable engine.
3. Record or upload one clean 10–30-second sample of your own voice. Use the same profile for ZONOS2 and Chatterbox clone comparisons.
4. Close heavy GPU applications and connect the Mac to power.
5. Record the start time, completion time, reported status, resulting audio duration, and any error.
6. Use headphones for the listening review.

## Run order

Run short-to-long so a defect is discovered before committing to an expensive long-form job:

1. Run all engines with the 2-minute script.
2. Fix or document any blocking defect.
3. Run all engines with the 8-minute script.
4. Run all engines with the 15-minute script.
5. Repeat ZONOS2 and Chatterbox using the same cloned voice.

For every run:

1. Create a new generation in **Speech Studio**.
2. Paste only the contents of the relevant `.txt` file.
3. Select the engine, compatible voice, and settings from the table above.
4. Start a stopwatch immediately before pressing **Generate**.
5. Watch phrase progress. Note stalls, retries, unusually slow phrases, or worker errors.
6. Stop the stopwatch when the job becomes **Completed**.
7. Confirm that cue syntax is never spoken.
8. Listen once without interruption for skips, repeats, hallucinations, abrupt joins, wrong stress, and odd silence.
9. Listen again while watching phrase highlighting. The highlight should follow the spoken phrase and switch near its stored boundary.
10. Click three phrases—early, middle, and late—and confirm accurate seeking.
11. Test repeat-current-phrase, plus/minus ten seconds, 0.75×, 1×, and 1.25× playback.
12. Download and play both MP3 and WAV.
13. Reopen the result from **History** and confirm playback starts without regeneration.
14. Enter the result in `docs/V1_ACCEPTANCE_CHECKLIST.md`.

## Engine behaviour and expected generation time

Real-time factor, or RTF, is generation seconds divided by audio seconds. An RTF of 0.5 generates two minutes of speech in about one minute. These estimates use measurements from the original M5 Max test machine and include a practical allowance for model warm-up, phrase orchestration, and MP3 encoding.

| Engine | How it works in ShadowLearn | Measured RTF | 2-minute target | 8-minute target | 15-minute target |
| --- | --- | ---: | ---: | ---: | ---: |
| macOS System | Apple's built-in local synthesizer; development baseline, no cloning | 0.128 | 20–45 sec | 1–3 min | 2–5 min |
| Kokoro MLX | Small local neural TTS optimized through Apple MLX; fast preset voices, no cloning | 0.058 | 10–30 sec | 35–90 sec | 1–3 min |
| ZONOS2 Metal | Quantized local expressive model served on loopback by `zonos2.cpp`; preset and cloned voices | 0.970 | 2–4 min | 8–13 min | 15–24 min |
| Chatterbox MPS | Local PyTorch/MPS expressive model in an isolated worker; clone-oriented | 2.217 | 5–8 min | 20–30 min | 40–55 min |

The macOS result was measured over the same ten-passage fixed corpus. First-run neural-model loading can add several minutes. Thermal load, memory pressure, phrase count, cloning preparation, and selected controls can also change the result.

Expected finished-audio bands are 1:45–2:20 for the self-introduction, 7:30–9:00 for the product pitch, and 14:00–16:30 for the design-thinking talk. These are acceptance bands rather than guarantees. Record the actual duration from each engine; a result far outside the band is evidence of an ignored pace control, abnormal silence, rushed delivery, or missing content.

### What each engine is useful for

- **macOS System:** validates the full application pipeline independently of neural-model setup. Treat its voice quality as a functional baseline, not the final quality target.
- **Kokoro MLX:** should be the speed and reliability reference. Listen closely to names, abbreviations, emotional shifts, and phrase joins because speed alone does not establish quality.
- **ZONOS2 Metal:** the leading expressive candidate on this Mac because the GPU-DAC configuration passed the real-time technical gate. Check whether emotion and cloning remain stable across long chunks.
- **Chatterbox MPS:** a second expressive/cloning reference. It is expected to be slower than real time here, so compare its naturalness and clone similarity against the time cost.

## Score every result

Use a 1–5 score for each category:

| Category | Weight | Listen for |
| --- | ---: | --- |
| Naturalness | 30% | Human rhythm, sentence flow, breath-like pauses, non-robotic delivery |
| Pronunciation | 25% | Names, acronyms, technical terms, endings, articles, numbers |
| Prosody/modulation | 20% | Pitch movement, contrast, questions, emotional transitions, emphasis |
| Punctuation/pacing | 15% | Commas, semicolons, quotations, paragraphs, requested pauses |
| Clone similarity | 10% | Timbre, accent, vocal identity, consistency over time |

Also record these pass/fail checks separately:

- No skipped words or phrases.
- No repeated words or phrases.
- No invented speech.
- No cue syntax spoken aloud.
- No clipped starts or endings.
- No clicks, large loudness jumps, or unnatural gaps at phrase joins.
- No crash, hang, or lost history.
- Highlighting stays aligned with the current phrase.

## Extra tests that are easy to miss

- Cancel halfway through the 8-minute script, then resume it.
- Force-quit during a separate run, restart the service, and resume completed phrases.
- Start a second job immediately after the first to reveal stale worker state.
- Scrub while audio is still loading to verify byte-range playback.
- Put the phone to sleep and resume playback through Tailscale.
- Compare a cold run after service restart with a warm run.
- Verify the source character count remains below 25,000.
- Confirm History deletion removes only the selected generation and artifacts.

## Source notes

The self-introduction is based on [Mohan Aditya Sadhanala's public LinkedIn profile](https://www.linkedin.com/in/mohan-aditya-sadhanala/). The product pitch reflects the [public Profeshare AI website](https://profeshare.ai/) as reviewed on 24 August 2026. The teaching talk follows [IDEO's human-centred design-thinking principles](https://designthinking.ideo.com/introduction) and the [five-mode model published by Stanford d.school](https://dschool.stanford.edu/tools/design-thinking-bootleg).

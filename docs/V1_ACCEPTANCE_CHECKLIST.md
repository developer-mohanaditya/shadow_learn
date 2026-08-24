# ShadowLearn V1 Acceptance Checklist

Update this file after each verified result. Use `[x]` only when the acceptance condition has passed; record failures and observations in the notes tables rather than hiding them.

## 1. Final-user acceptance testing — in progress

### Test preparation

- [x] Prepare a 2-minute self-introduction script.
- [x] Prepare an 8-minute Profeshare AI product pitch.
- [x] Prepare a 15-minute design-thinking teaching talk.
- [x] Add only supported inline pause and emphasis cues.
- [x] Document per-script mood, pace, accent, and expressiveness settings.
- [x] Document a repeatable four-engine test method.
- [ ] Record a clean 10–30-second personal voice reference for clone tests.

### Script A — self-introduction

- [ ] macOS System generation passes.
- [ ] Kokoro MLX generation passes.
- [ ] ZONOS2 preset generation passes.
- [ ] ZONOS2 clone generation passes.
- [ ] Chatterbox clone generation passes.
- [ ] No skipped, repeated, or hallucinated text.
- [ ] Pronunciation, pauses, emphasis, tone, and pace are acceptable.
- [ ] Waveform, highlighting, seeking, repeat, MP3, WAV, and History pass.

### Script B — Profeshare AI pitch

- [ ] macOS System generation passes.
- [ ] Kokoro MLX generation passes.
- [ ] ZONOS2 preset generation passes.
- [ ] ZONOS2 clone generation passes.
- [ ] Chatterbox clone generation passes.
- [ ] No skipped, repeated, or hallucinated text.
- [ ] Pronunciation, pauses, emphasis, tone, and pace are acceptable.
- [ ] Waveform, highlighting, seeking, repeat, MP3, WAV, and History pass.

### Script C — design-thinking talk

- [ ] macOS System generation passes.
- [ ] Kokoro MLX generation passes.
- [ ] ZONOS2 preset generation passes.
- [ ] ZONOS2 clone generation passes.
- [ ] Chatterbox clone generation passes.
- [ ] No skipped, repeated, or hallucinated text.
- [ ] Pronunciation, pauses, emphasis, tone, and pace are acceptable.
- [ ] Waveform, highlighting, seeking, repeat, MP3, WAV, and History pass.

### Reliability and recovery

- [ ] Cancel one generation midway and verify it stops safely.
- [ ] Resume the cancelled or interrupted generation from completed phrases.
- [ ] Force-close ShadowLearn during generation and verify recovery after restart.
- [ ] Generate two jobs consecutively with each engine.
- [ ] Verify historical audio plays without inference.
- [ ] Verify missing artifacts are reported rather than silently removed.
- [ ] Verify database backup creation and validated restore using a copied database.

## 2. Expressive-engine benchmark

- [ ] Run the fixed corpus with Kokoro.
- [ ] Run the fixed corpus with ZONOS2.
- [ ] Run the fixed corpus with Chatterbox.
- [ ] Complete 20 consecutive jobs with the candidate expressive engine.
- [ ] Complete and recover a 20-minute chunked script.
- [ ] Score naturalness.
- [ ] Score pronunciation.
- [ ] Score prosody and modulation.
- [ ] Score punctuation and pacing.
- [ ] Score clone similarity.
- [ ] Select and document the final expressive default.

## 3. Audio-quality polish

- [ ] Review abbreviations, dates, currencies, numbers, names, and difficult words.
- [ ] Tune phrase chunk boundaries.
- [ ] Tune silence between phrases.
- [ ] Verify loudness consistency across chunks.
- [ ] Review mood, pace, and expressiveness controls per engine.
- [ ] Fix all acceptance-script audio defects that can be reproduced.

## 4. Production reliability

- [ ] Verify `launchd` starts ShadowLearn after login/reboot.
- [ ] Verify `launchd` starts ZONOS2 after login/reboot.
- [ ] Verify the same database, voices, models, audio, and history survive reboot.
- [ ] Test migration backup and restore with a deliberately damaged copy.
- [ ] Verify daily and weekly backup retention.
- [ ] Verify MP3 and WAV byte-range seeking in Safari and Chrome.

## 5. Remote and mobile testing

- [ ] Configure Tailscale Serve.
- [ ] Test the app from a phone on the same tailnet.
- [ ] Verify mobile generation, playback, seeking, and downloads.
- [ ] Verify phrase highlighting and auto-scroll on mobile Safari/Chrome.
- [ ] Install and launch the PWA from the phone home screen.

## 6. Public-project readiness

- [ ] Choose and add an open-source software licence.
- [ ] Document upstream model licences and restrictions.
- [ ] Add screenshots to the README.
- [ ] Add a short demonstration video or animated preview.
- [ ] Add GitHub Actions for tests, linting, and frontend builds.
- [ ] Add contribution and issue-reporting guidance.

## 7. Official release

- [ ] Resolve every release-blocking defect found above.
- [ ] Confirm a clean production build and complete test run.
- [ ] Tag `v1.0.0`.
- [ ] Publish a GitHub Release with installation notes and known limitations.

## Manual results

| Date | Script | Engine / voice | Generation time | Audio duration | Result | Notes |
| --- | --- | --- | ---: | ---: | --- | --- |
|  |  |  |  |  |  |  |


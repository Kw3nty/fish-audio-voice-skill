# Agent entry point

This repository is a portable skill. Read [`SKILL.md`](SKILL.md) before doing anything else and follow its workflow.

The only two things you may ask the user for are:

1. **Fish Audio API key** — use it only as the `FISH_API_KEY` environment variable for the current process.
2. **Voice ID** — the `reference_id` from the Fish Audio voice page.

Do not ask about model, output format, pause length, language, loudness, file names, or folder layout. The defaults are in `SKILL.md`.

Take the narration from the user's video script or brief. Run `scripts/voiceover.py`, verify the output with `ffprobe`, and return the paths to `vo.wav`, `timing.json`, `words.json` (if transcription was enabled), and `voiceover.zip`.

Never write the API key into a file and never print it in logs or in your answer.

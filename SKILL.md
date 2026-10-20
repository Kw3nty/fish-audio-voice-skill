---
name: fish-audio-voiceover
description: End-to-end video voiceover with Fish Audio API. Use when the user wants to voice/narrate a video, turn a script into TTS audio, split narration into chapters, create word timings for captions, or package a voiceover archive. The agent should ask only for a Fish Audio API key and a voice ID; everything else has safe defaults.
---

# Fish Audio Voiceover

Turn a video script into a finished, normalized voiceover with chapter files, timings, and a ZIP archive. This skill is written for an AI agent. It is model-agnostic: Claude Code, Codex, OpenCode, Cursor, and similar agents can read this file and run the scripts.

## The only two things to ask the user

Ask exactly once, in one short message:

1. **Fish Audio API key** — or ask them to set `FISH_API_KEY` in the environment.
2. **Voice ID** — the `reference_id` of the voice they want.

Do not ask about model, format, gap length, language, loudness, file names, or folder layout. Use the defaults in this file. If the user already provided either value earlier in the conversation, do not ask again.

If the user gives a voice page URL, extract the ID from the last path segment, for example:

```text
https://fish.audio/m/2270bb203a424d1881678ba5e4b82b54
                                └── voice ID / reference_id ──┘
```

If the user pastes an API key in chat, use it only for the current process. Never write it to a file, README, manifest, shell history, or Git. Never print the key in logs or in your answer.

## Inputs

- Narration script: use the script from the video brief. If the user only asked for a voiceover and supplied no text, write a concise narration first, then voice it. Do not ask extra questions about tone; use a natural, confident explainer delivery.
- API key: `FISH_API_KEY` environment variable.
- Voice ID: required, passed to `--voice-id`.
- Optional: `--language` only if the script is mixed-language and timings need a specific language tag. Otherwise let the API auto-detect.

## Quick start

From the repository root:

```bash
export FISH_API_KEY="..."          # macOS / Linux
export VOICE_ID="..."

python scripts/voiceover.py \
  --script examples/script.md \
  --voice-id "$VOICE_ID" \
  --out voiceover \
  --transcribe
```

Windows PowerShell:

```powershell
$env:FISH_API_KEY = "..."
python scripts/voiceover.py --script examples/script.md --voice-id "..." --out voiceover --transcribe
```

Output:

```text
voiceover/
  audio/01.mp3 ...          # chapter MP3s
  texts/01.txt ...          # exact text sent to the API
  public/vo.wav             # assembled 48 kHz mono WAV
  vo16.wav                  # 16 kHz mono, for ASR
  timing.json               # chapter start/end seconds
  words.json                # word timings, only with --transcribe
  manifest.json             # model, voice ID, durations, no secrets
  voiceover.zip             # archive for upload / hand-off
```

Use `timing.json` to place scenes and `words.json` to animate captions. Copy `public/vo.wav` into the video project's `public/` folder.

## Script format

Use blank lines or Markdown headings to separate chapters:

```markdown
## 01 / HOOK
Microphone not needed. I voice videos through Fish Audio API.

## 02 / KEY
Open fish.audio, go to API Keys, create a key and store it in FISH_API_KEY.
```

The parser removes Markdown decoration before sending text. Headings become chapter labels. A script without headings is split by blank lines. A single block is one chapter.

## What the script does

1. Validates the API key and voice ID before spending a request.
2. Splits the script into chapters and cleans Markdown.
3. Calls `POST https://api.fish.audio/v1/tts` once per chapter (chunks longer chapters automatically).
4. Retries only transient errors (`429`, `500`, `502`, `503`, `504`) with exponential backoff.
5. Never overwrites existing audio unless `--force` is passed; this prevents accidental repeat charges.
6. Trims edge silence, inserts the default 0.85 s pause, concatenates, and normalizes to about −16 LUFS / −2 dBTP.
7. Writes `timing.json`, `manifest.json`, and a portable ZIP.

## Defaults

| Setting | Default |
|---|---|
| API | `https://api.fish.audio/v1/tts` |
| Model header | `s2.1-pro-free` |
| Format | `mp3`, 44.1 kHz, 128 kbps |
| Chapter gap | `0.85` s |
| Loudness | `-16 LUFS`, true peak `-2 dBTP` |
| Output | `voiceover/` |
| Archive | `voiceover/voiceover.zip` |

`--model s2.1-pro` is available as an explicit override. `s2.1-pro-free` is the documented free developer tier; availability and limits are controlled by Fish Audio.

## Security rules

- The key is read from `FISH_API_KEY` only. There is no `--api-key` flag.
- The key is never stored in `manifest.json`, `timing.json`, text files, or the ZIP.
- Do not commit `voiceover/`, `.env`, `*.wav`, or API keys. `.gitignore` already covers them.
- Do not put a real key in a repository, even a private one.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` in `PATH`
- No Python package is required for synthesis. `--transcribe` additionally needs `faster-whisper` and `numpy`.

If FFmpeg is missing, install it before running. That is an environment prerequisite, not a content question. On Windows, a static build from ffmpeg.org works.

## Verification

Always check the result before handing it off:

```bash
ffprobe -v error -show_entries format=duration -show_entries stream=codec_name,sample_rate,channels -of json voiceover/public/vo.wav
python -c "import json; print(json.load(open('voiceover/timing.json'))[-1])"
```

Report the duration, chapter count, and paths to `vo.wav`, `timing.json`, and `voiceover.zip`. Listen to at least the first and last chapter; pronunciation of brand names may need phonetic spelling and one re-generation.

## Cost and quality caveats

- Each request can consume account credits or rate limits. Re-running a chapter is a new request.
- A repeated synthesis can sound slightly different. Do not promise bit-identical output.
- This skill does not clone a voice. It uses an existing voice ID. Voice cloning is a separate API flow.
- Do not claim a specific model will stay free forever; check the Fish Audio account and docs.

## API facts and links

- API key page: <https://fish.audio/app/api-keys/>
- Voice library: <https://fish.audio/>
- Voice ID is the model ID in the voice page URL, or use the page's copy-ID button.
- Endpoint docs: <https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech>
- Quick start: <https://docs.fish.audio/developer-guide/getting-started/quickstart>
- Errors: `401` bad key, `402` no credits, `400` bad voice/parameters, `429` rate limit.

More detail: `references/api.md`.

# Fish Audio Voiceover Skill

[Русская версия ниже](#русская-версия)

A portable skill for AI coding agents. Drop this repository into an AI session and the agent can voice a video end-to-end after asking for only two values:

1. **Fish Audio API key** (`FISH_API_KEY`)
2. **Voice ID** (`reference_id`)

It writes chapter MP3s, one normalized WAV, `timing.json` for scenes, optional word timings for captions, and a ZIP archive.

## How to use it as a skill

1. Download this repository as ZIP (or clone it).
2. Attach the folder to an AI agent session.
3. Give the agent the video script or brief and ask it to voice the video.
4. The agent reads `SKILL.md`, asks only for the API key and voice ID, then runs the pipeline and returns the audio, timings, and archive.

No manual API calls are required. The agent must not ask about model, format, pauses, or loudness — those defaults are already in the skill.

## Quick start for the agent

Read [`SKILL.md`](SKILL.md). It contains the full workflow and security rules.

```bash
export FISH_API_KEY="..."
python scripts/voiceover.py --script examples/script.md --voice-id "YOUR_VOICE_ID" --out voiceover --transcribe
```

Output:

- `voiceover/public/vo.wav` — ready for a video editor
- `voiceover/audio/*.mp3` — per-chapter files
- `voiceover/timing.json` — chapter boundaries
- `voiceover/words.json` — word-level timings (with `--transcribe`)
- `voiceover/voiceover.zip` — archive with audio, texts, timings and manifest

## Where to get the two values

**API key:** sign in at <https://fish.audio>, open <https://fish.audio/app/api-keys/>, click **Create New Key**, copy it once and keep it in `FISH_API_KEY`. Never commit it.

**Voice ID:** open any voice in the Fish Audio library. The ID is the last part of the URL, for example `https://fish.audio/m/2270bb203a424d1881678ba5e4b82b54` → `2270bb203a424d1881678ba5e4b82b54`. You can also use the copy-ID button on the voice page.

## What is inside

```text
AGENTS.md                entry point for coding agents: read SKILL.md first
SKILL.md                 instructions for the AI agent
scripts/voiceover.py     synthesis, retries, assembly, timings, ZIP
references/api.md        API details, errors, security notes
examples/script.md       short English example
examples/tutorial-script.md  Russian tutorial narration with TTS phonetics
examples/voiceover.zip   generated example: 7 chapters, WAV, timings, words, ZIP
```

## Safety

- No API key is stored in the repository or the archive.
- `.gitignore` excludes secrets and generated audio.
- Existing audio is not overwritten without `--force`, so a rerun does not silently spend credits.
- Each API request may consume account limits or credits.

## Requirements

Python 3.10+, FFmpeg and ffprobe in `PATH`. `--transcribe` additionally needs `faster-whisper` and `numpy`. Synthesis itself uses only the Python standard library.

## License

MIT. The skill is a wrapper around the Fish Audio public API, not an official Fish Audio product.

---

## Русская версия

Это переносимый скилл для ИИ-агентов. Скинь репозиторий в сессию ИИ — и он сможет озвучить видео целиком, задав только два вопроса:

1. **API-ключ Fish Audio** (`FISH_API_KEY`)
2. **ID голоса** (`reference_id`)

На выходе — MP3 по главам, нормализованный WAV, `timing.json` для сцен, при необходимости тайминги слов для субтитров и ZIP-архив.

### Как пользоваться

1. Скачай репозиторий как ZIP или склонируй его.
2. Скинь папку в сессию ИИ-агента.
3. Дай агенту сценарий или идею видео и попроси озвучить.
4. Агент прочитает `SKILL.md`, спросит только API-ключ и ID голоса, запустит пайплайн и отдаст аудио, тайминги и архив.

Никаких ручных запросов к API. Агент не должен спрашивать модель, формат, паузы или громкость — эти значения уже настроены в скилле.

### Быстрый запуск

```bash
export FISH_API_KEY="..."
python scripts/voiceover.py --script examples/script.md --voice-id "ВАШ_ID_ГОЛОСА" --out voiceover --transcribe
```

Windows PowerShell:

```powershell
$env:FISH_API_KEY = "..."
python scripts/voiceover.py --script examples/script.md --voice-id "ВАШ_ID_ГОЛОСА" --out voiceover --transcribe
```

### Где взять ключ и ID

- **Ключ:** <https://fish.audio/app/api-keys/> → Create New Key. Храни только в переменной окружения.
- **ID голоса:** открой голос в библиотеке Fish Audio. ID — последняя часть адреса `fish.audio/m/<id>`. На странице голоса есть кнопка копирования ID.

### Пример

`examples/tutorial-script.md` — сценарий этого видео. `examples/voiceover.zip` — результат, собранный этим же скиллом: 7 глав, `vo.wav`, `timing.json`, `words.json` и `manifest.json`.

### Что важно

- Ключ не попадает в файлы, манифест или архив.
- Без `--force` готовые файлы не перезаписываются, чтобы случайно не потратить лимиты повторно.
- Каждый запрос может расходовать кредиты или лимиты аккаунта.
- Повторный синтез может звучать немного иначе.
- Скилл не клонирует голос: он использует готовый `reference_id`. Клонирование — отдельный процесс в Fish Audio.

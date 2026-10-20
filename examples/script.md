# Example narration

## 01 / HOOK

Drop this repository into an AI agent's workspace. It asks only for a Fish Audio API key and a voice ID, then voices the video.

## 02 / KEY

Open fish.audio and go to API Keys. Create a new key, copy it once, and keep it in FISH_API_KEY. Never commit it to the repository.

## 03 / VOICE

Open a voice in the library. The ID is the last part of the page URL, or use the copy-ID button. That ID is the reference_id.

## 04 / REQUEST

Send a POST request to api.fish.audio/v1/tts with the key, the model, the text, the voice ID, and the mp3 format. One request per chapter is easier to fix.

## 05 / ASSEMBLY

The skill trims silence, adds pauses, normalizes loudness, and joins the chapters. It writes a WAV, a timing file, word timings, and a ZIP archive.

## 06 / REPO

Drop the repository into an AI session. It reads SKILL.md, asks only for the API key and voice ID, and runs the pipeline.

# API notes

## Authentication

```http
Authorization: Bearer <FISH_API_KEY>
Content-Type: application/json
model: s2.1-pro-free
```

Get a key at <https://fish.audio/app/api-keys/>. The key can create charges or consume limits. Store it in `FISH_API_KEY`; never commit it.

## Voices

`reference_id` is the voice model ID. Find it in the voice page URL:

```text
https://fish.audio/m/2270bb203a424d1881678ba5e4b82b54
                          └──────── reference_id ────────┘
```

Or use the copy-ID button on the page. Public library voices and your own saved voice models both use `reference_id`.

## Request

```http
POST https://api.fish.audio/v1/tts
Authorization: Bearer <key>
Content-Type: application/json
model: s2.1-pro-free

{
  "text": "Narration text",
  "reference_id": "voice-model-id",
  "format": "mp3",
  "sample_rate": 44100,
  "mp3_bitrate": 128
}
```

The response body is audio bytes. A JSON response is an error, not audio.

## Status codes

| Code | Meaning | Action |
|---|---|---|
| 400 | Bad parameters or `reference_id` | Check the voice ID and JSON |
| 401 | Missing/invalid key | Recheck `FISH_API_KEY` |
| 402 | No credits | Top up or use an account with available limits |
| 429 | Rate limit | Back off and retry |
| 500/502/503/504 | Transient server failure | Retry with exponential backoff |
| 503 | High load | Retry later |

The client retries only transient failures. It does not retry 400/401/402, because those require a human decision.

## Limits and caveats

- One request per chapter is easier to regenerate than one huge request.
- Long chapters are split at sentence boundaries by `scripts/voiceover.py`.
- Repeated synthesis can differ slightly; do not promise identical audio.
- `s2.1-pro-free` is the documented free developer tier, but availability and quotas are controlled by Fish Audio and can change.
- Voice cloning is a separate flow: <https://docs.fish.audio/developer-guide/core-features/creating-models>.

## Official links

- Text to speech: <https://docs.fish.audio/api-reference/endpoint/openapi-v1/text-to-speech>
- Quick start: <https://docs.fish.audio/developer-guide/getting-started/quickstart>
- Models: <https://docs.fish.audio/developer-guide/models-pricing/models-overview>
- Errors: <https://docs.fish.audio/api-reference/errors>

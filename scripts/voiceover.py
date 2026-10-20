#!/usr/bin/env python3
"""Fish Audio voiceover skill: synthesize, assemble, time, archive.

Only two user inputs are required: FISH_API_KEY and a voice ID.

Usage:
  python scripts/voiceover.py --script examples/script.md --voice-id <id> --out voiceover
  python scripts/voiceover.py --script script.md --voice-id <id> --out voiceover --transcribe
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import wave
import zipfile
from pathlib import Path

API_URL = "https://api.fish.audio/v1/tts"
DEFAULT_MODEL = "s2.1-pro-free"
DEFAULT_GAP = 0.85
CHUNK_LIMIT = 2800
TRANSIENT = {429, 500, 502, 503, 504}


def log(msg: str) -> None:
    print(msg, flush=True)


def find_voice_id(value: str) -> str:
    value = value.strip()
    if value.startswith("http"):
        value = value.rstrip("/").split("/")[-1].split("?")[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", value):
        raise SystemExit("Voice ID looks invalid. Use the ID after fish.audio/m/ or the copy-ID button.")
    return value


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"(?<!\w)[*_]([^*_]+)[*_](?!\w)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*>\s?", "", text, flags=re.M)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def split_long(text: str, limit: int = CHUNK_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        window = rest[:limit]
        cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "), window.rfind("\n"))
        if cut < limit * 0.55:
            cut = max(window.rfind(", "), window.rfind("; "), window.rfind(" "))
        if cut < limit * 0.35:
            cut = limit
        else:
            cut += 1
        part = rest[:cut].strip()
        if part:
            parts.append(part)
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts


def parse_script(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    chapters: list[dict] = []
    current_title: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_title, current_lines
        body = strip_markdown("\n".join(current_lines))
        if body:
            chapters.append({"title": current_title or f"Chapter {len(chapters) + 1}", "text": body})
        current_title, current_lines = None, []

    for line in raw.splitlines():
        if re.match(r"^\s*##\s+", line):
            flush()
            current_title = re.sub(r"^\s*##\s+", "", line).strip()
        elif re.match(r"^\s*#\s+", line):
            if current_lines:
                flush()
        else:
            current_lines.append(line)
    flush()
    if not chapters:
        raise SystemExit("Script is empty.")
    if len(chapters) == 1:
        # No headings: split by blank lines, which is how most narration scripts arrive.
        blocks = [strip_markdown(b) for b in re.split(r"\n\s*\n", raw) if strip_markdown(b)]
        if len(blocks) > 1:
            chapters = [{"title": f"Chapter {i + 1}", "text": b} for i, b in enumerate(blocks)]
    return chapters


def request_tts(text: str, voice_id: str, model: str, key: str, timeout: float = 300.0) -> bytes:
    payload = {
        "text": text,
        "reference_id": voice_id,
        "format": "mp3",
        "sample_rate": 44100,
        "mp3_bitrate": 128,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "model": model,
    }
    for attempt in range(5):
        req = urllib.request.Request(API_URL, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                ctype = resp.headers.get("Content-Type", "").lower()
            if not data or "json" in ctype:
                raise RuntimeError("Fish Audio returned no audio (or a JSON error body).")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code not in TRANSIENT:
                raise SystemExit(f"Fish Audio HTTP {exc.code}. Check key, voice ID, credits and limits. No retry.") from None
            if attempt == 4:
                raise SystemExit(f"Fish Audio HTTP {exc.code} after retries. Check account usage before rerunning.") from None
            wait = 2 ** attempt
            log(f"  transient HTTP {exc.code}; retry in {wait}s")
            time.sleep(wait)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise SystemExit("Network/timeout after retries. The request may have been processed; check account usage before rerunning.") from None
            wait = 2 ** attempt
            log(f"  network error; retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], text=True).strip()
    return round(float(out), 3)


def synthesize(args: argparse.Namespace, chapters: list[dict], root: Path) -> list[dict]:
    key = os.environ.get("FISH_API_KEY", "").strip()
    if args.dry_run:
        if not key:
            log("Dry run: FISH_API_KEY is not set (real run would stop here).")
        log(f"Dry run: {len(chapters)} chapters, model={args.model}, voice={args.voice_id}")
        for c in chapters:
            log(f"  {c['title']}: {len(c['text'])} chars, {len(split_long(c['text']))} request(s)")
        return []
    if not key:
        raise SystemExit("FISH_API_KEY is not set. Never put the key in a file; set it in the current environment.")

    audio_dir = root / "audio"
    text_dir = root / "texts"
    audio_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)
    meta: list[dict] = []

    for ci, chapter in enumerate(chapters, 1):
        chunks = split_long(chapter["text"])
        files: list[Path] = []
        (text_dir / f"{ci:02d}.txt").write_text(chapter["text"] + "\n", encoding="utf-8")
        for chi, chunk in enumerate(chunks, 1):
            name = f"{ci:02d}.mp3" if len(chunks) == 1 else f"{ci:02d}-{chi:02d}.mp3"
            dst = audio_dir / name
            if dst.exists() and dst.stat().st_size > 0 and not args.force:
                log(f"[{ci:02d}/{len(chapters)}] {name}: exists, skip (use --force to redo)")
            else:
                if dst.exists() and not args.force:
                    raise SystemExit(f"{dst} exists but is empty. Remove it or pass --force.")
                log(f"[{ci:02d}/{len(chapters)}] {name}: {len(chunk)} chars")
                data = request_tts(chunk, args.voice_id, args.model, key)
                tmp = dst.with_suffix(dst.suffix + ".part")
                tmp.write_bytes(data)
                tmp.replace(dst)
                log(f"  saved {len(data)} bytes")
            files.append(dst)
        meta.append({"index": ci, "title": chapter["title"], "text": chapter["text"], "files": files})
    return meta


def assemble(args: argparse.Namespace, meta: list[dict], root: Path) -> list[dict]:
    public = root / "public"
    public.mkdir(parents=True, exist_ok=True)
    timings: list[dict] = []
    at = 0.0

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        parts: list[Path] = []
        for chapter in meta:
            chapter_files = chapter["files"]
            for j, src in enumerate(chapter_files):
                dst = td_path / f"{len(parts) + 1:03d}.wav"
                gap = args.gap if j == len(chapter_files) - 1 else 0.3
                af = (
                    "silenceremove=start_periods=1:start_threshold=-45dB,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    f"apad=pad_dur={gap}"
                )
                run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af,
                     "-ar", "44100", "-ac", "1", str(dst)])
                dur = wav_duration(dst)
                if j == 0:
                    chapter_start = at
                at += dur
                parts.append(dst)
            timings.append({
                "i": chapter["index"],
                "title": chapter["title"],
                "a": round(chapter_start, 6),
                "b": round(at, 6),
            })

        listing = td_path / "list.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        tmp_wav = root / "public" / "vo.tmp.wav"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
             "-af", "loudnorm=I=-16:TP=-2:LRA=9", "-ar", "48000", "-ac", "1",
             "-c:a", "pcm_s16le", str(tmp_wav)])
        tmp_wav.replace(root / "public" / "vo.wav")

    run(["ffmpeg", "-v", "error", "-y", "-i", str(root / "public" / "vo.wav"),
         "-ar", "16000", "-ac", "1", str(root / "vo16.wav")])
    (root / "timing.json").write_text(json.dumps(timings, ensure_ascii=False, indent=2), encoding="utf-8")
    return timings


def transcribe(root: Path) -> None:
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        log("--transcribe skipped: install faster-whisper and numpy first.")
        return
    wf = wave.open(str(root / "vo16.wav"))
    audio = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float32) / 32768
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, word_timestamps=True, beam_size=5, vad_filter=False)
    words = []
    for segment in segments:
        for word in segment.words:
            words.append({"w": word.word.strip(), "s": round(word.start, 2), "e": round(word.end, 2)})
    (root / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Transcribed {len(words)} words; language={info.language}, probability={info.language_probability:.2f}")


def archive(args: argparse.Namespace, meta: list[dict], root: Path) -> None:
    zip_path = root / "voiceover.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(root / "public" / "vo.wav", "vo.wav")
        z.write(root / "vo16.wav", "vo16.wav")
        z.write(root / "timing.json", "timing.json")
        z.write(root / "manifest.json", "manifest.json")
        if (root / "words.json").exists():
            z.write(root / "words.json", "words.json")
        for chapter in meta:
            for src in chapter["files"]:
                z.write(src, "audio/" + src.name)
            text_file = root / "texts" / f"{chapter['index']:02d}.txt"
            z.write(text_file, "texts/" + text_file.name)
    log(f"Archive: {zip_path} ({zip_path.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fish Audio voiceover pipeline")
    parser.add_argument("--script", type=Path, required=True, help="chaptered Markdown or plain text")
    parser.add_argument("--voice-id", required=True, help="Fish Audio reference_id or voice page URL")
    parser.add_argument("--out", type=Path, default=Path("voiceover"), help="output folder")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--gap", type=float, default=DEFAULT_GAP, help="pause between chapters, seconds")
    parser.add_argument("--force", action="store_true", help="re-synthesize existing files (new charges)")
    parser.add_argument("--transcribe", action="store_true", help="create words.json with faster-whisper")
    parser.add_argument("--dry-run", action="store_true", help="validate inputs without API calls")
    parser.add_argument("--no-zip", action="store_true")
    args = parser.parse_args()

    if not args.script.exists():
        raise SystemExit(f"Script not found: {args.script}")
    if args.gap < 0:
        raise SystemExit("--gap cannot be negative")
    args.voice_id = find_voice_id(args.voice_id)

    chapters = parse_script(args.script)
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("FFmpeg and ffprobe must be in PATH.")
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)

    meta = synthesize(args, chapters, root)
    if args.dry_run:
        return
    timings = assemble(args, meta, root)
    generated = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        "skill": "fish-audio-voiceover",
        "api": API_URL,
        "model": args.model,
        "voice_id": args.voice_id,
        "gap": args.gap,
        "generated_at": generated,
        "source_script": str(args.script.name),
        "chapters": [
            {
                "index": t["i"],
                "title": t["title"],
                "start": t["a"],
                "end": t["b"],
                "duration": round(t["b"] - t["a"], 3),
                "files": [f"audio/{p.name}" for p in meta[i]["files"]],
            }
            for i, t in enumerate(timings)
        ],
        "total_duration": round(ffprobe_duration(root / "public" / "vo.wav"), 3),
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.transcribe:
        transcribe(root)
    if not args.no_zip:
        archive(args, meta, root)

    log("")
    log(f"Done: {len(chapters)} chapters, {manifest['total_duration']:.2f}s")
    log(f"  {root / 'public' / 'vo.wav'}")
    log(f"  {root / 'timing.json'}")
    if (root / "words.json").exists():
        log(f"  {root / 'words.json'}")
    if not args.no_zip:
        log(f"  {root / 'voiceover.zip'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Video Preparer Utility
──────────────────────
Downloads a YouTube video (MP4), extracts its audio track (MP3), and ensures a
subtitle file (VTT) exists – either by fetching YouTube's transcript or
generating one locally with an OpenAI Whisper model.

This version is asynchronous and can process multiple URLs concurrently.

Basic usage:
    python video_preparer.py "https://youtu.be/VIDEO_ID"

Advanced (process multiple videos at once):
    python video_preparer.py "URL1" "URL2" --model medium
"""

import argparse
import asyncio
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from xml.etree import ElementTree

from yt_dlp import YoutubeDL
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
import whisper


# ──────────────────────────────────────────── helpers ─────────────────────────

YTHOSTS = {
    "www.youtube.com", "youtube.com",
    "m.youtube.com", "music.youtube.com"
}

def video_id_from_url(url: str) -> str:
    """Extract the YouTube video ID from a range of URL formats."""
    p = urlparse(url)
    if p.hostname in {"youtu.be"}:
        return p.path[1:]
    if p.hostname in {"www.youtube.com", "youtube.com"}:
        if p.path == "/watch":
            return parse_qs(p.query)["v"][0]
        if p.path.startswith(("/embed/", "/v/")):
            return p.path.split("/")[2]
    elif p.hostname in YTHOSTS:
        if p.path.startswith("/watch"):
            return parse_qs(p.query)["v"][0]
        for prefix in ("/shorts/", "/live/"):
            if p.path.startswith(prefix):
                return p.path.split(prefix)[1]
    raise ValueError(f"Cannot parse video ID from URL: {url}")


def safe_name(name: str) -> str:
    """Make a filesystem-safe version of the video title."""
    return "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()


def ts(seconds: float) -> str:
    """Seconds → WebVTT timestamp."""
    millis = int(round((seconds - int(seconds)) * 1000))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"


def save_vtt(transcript, path: Path) -> None:
    """Write a YouTubeTranscriptApi list-of-dicts to VTT."""
    with path.open("w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, seg in enumerate(transcript, 1):
            start, end = seg["start"], seg["start"] + seg["duration"]
            text = seg["text"].replace("\n", " ")
            f.write(f"{i}\n{ts(start)} --> {ts(end)}\n{text}\n\n")


async def whisper_to_vtt(audio: Path, vtt: Path, model_size: str) -> None:
    """Run Whisper locally and emit VTT."""
    def _transcribe():
        model = whisper.load_model(model_size)
        return model.transcribe(str(audio))

    result = await asyncio.to_thread(_transcribe)
    with vtt.open("w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for seg in result["segments"]:
            f.write(
                f"{seg['id']+1}\n{ts(seg['start'])} --> {ts(seg['end'])}\n"
                f"{seg['text'].strip()}\n\n"
            )


# ─────────────────────────────────── async workflow ───────────────────────────

async def download_video(url: str, out: Path) -> None:
    """Asynchronously download a video."""
    ydl_opts = {
        "format": "bestvideo+bestaudio/best",
        "outtmpl": str(out),
        "quiet": True,
        "merge_output_format": "mp4",
    }
    await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).download([url]))


async def download_audio(url: str, out: Path) -> None:
    """Asynchronously download and extract an audio track."""
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(out),
        "quiet": True,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
    }
    await asyncio.to_thread(lambda: YoutubeDL(ydl_opts).download([url]))


async def process_url(url: str, model_size: str, output_dir: str):
    """Process a single video URL from download to VTT generation."""
    try:
        vid = video_id_from_url(url)
    except ValueError as e:
        print(f"Error: {e}")
        return

    def _extract_info():
        with YoutubeDL({"quiet": True}) as ydl:
            return ydl.extract_info(url, download=False)
    
    info = await asyncio.to_thread(_extract_info)
    title = info.get("title", vid)
    name = safe_name(title)
    
    print(f"Processing '{name}'...")
    root = Path(output_dir) / name
    root.mkdir(parents=True, exist_ok=True)

    video_path = root / f"{name}.mp4"
    audio_path = root / f"{name}.mp3"
    vtt_path = root / f"{name}.vtt"

    if not video_path.exists():
        print(f"  [*] Downloading video for '{name}'…")
        await download_video(url, video_path)
    else:
        print(f"  [*] Video already exists for '{name}'.")

    if not audio_path.exists():
        print(f"  [*] Extracting audio for '{name}'…")
        await download_audio(url, audio_path)
    else:
        print(f"  [*] Audio already exists for '{name}'.")

    print(f"  [*] Generating VTT for '{name}'…")
    transcript_ready = False
    try:
        def _get_transcript():
            return YouTubeTranscriptApi.get_transcript(vid)
        yt_transcript = await asyncio.to_thread(_get_transcript)
        save_vtt(yt_transcript, vtt_path)
        transcript_ready = True
        print(f"    → YouTube transcript found for '{name}'.")
    except (TranscriptsDisabled, NoTranscriptFound, ElementTree.ParseError) as e:
        print(f"    → YouTube transcript not available for '{name}' ({type(e).__name__}). Falling back to Whisper.")

    if not transcript_ready:
        await whisper_to_vtt(audio_path, vtt_path, model_size)
        print(f"    → Whisper generated VTT for '{name}'.")

    print(f"\n✅ All files for '{name}' saved in: {root.resolve()}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download YouTube videos, extract audio, and prepare VTT subtitles asynchronously."
    )
    parser.add_argument("urls", nargs='+', help="One or more YouTube video URLs")
    parser.add_argument(
        "--model", default="base", help="Whisper model size (tiny, base, small, medium, large)"
    )
    parser.add_argument("--output-dir", default="data", help="Base output directory")
    args = parser.parse_args()

    tasks = [process_url(url, args.model, args.output_dir) for url in args.urls]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProcess interrupted by user.")
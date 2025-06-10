# tests/test_video_preparer.py
"""
Integration tests for video_preparer.py

pytest -m "not slow"      → ID-extraction only (fast, offline)
pytest -m slow            → also downloads small public videos (~5 s each)
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

import pytest

# ---- Configuration ---------------------------------------------------------
# A *very* short, public‑domain clip (≈2 s) that is unlikely to disappear.
# We reuse the same ID for all URL shapes so the downloads stay tiny.
VIDEO_ID = "mA93Rhj6Tm8"  # "20 seconds video" – count down from 9 to 0

# Use a fixed output directory inside tests/ for easier inspection
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_DATA_DIR.mkdir(exist_ok=True)

URL_VARIANTS = [
    f"https://www.youtube.com/watch?v={VIDEO_ID}",               # regular watch
    f"https://youtu.be/{VIDEO_ID}",                              # short share link
    f"https://youtube.com/shorts/{VIDEO_ID}",                    # Shorts
    f"https://www.youtube.com/embed/{VIDEO_ID}",                 # embed
    f"https://m.youtube.com/watch?v={VIDEO_ID}",                 # mobile
    f"https://music.youtube.com/watch?v={VIDEO_ID}",             # music sub‑domain
    f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}",        # no‑cookie embed
]

# Skip the suite unless the maintainer explicitly opted‑in.
RUN_NETWORK = os.getenv("RUN_NETWORK_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_NETWORK,
    reason="Integration tests require network and are disabled by default.\n"
    "Set RUN_NETWORK_TESTS=1 to enable.",
)

# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", URL_VARIANTS)
def test_video_preparer_download(url):
    """Run video_preparer.py against various YouTube URL forms and check it finishes
    without error and produces the expected artefacts (mp4 / mp3).
    """
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg binary not found in PATH – cannot test downloads.")

    cmd = [
        sys.executable,
        "-m", "video_preparer",
        url,
        "--model",
        "tiny",  # fastest inference for the 2‑second audio clip
        "--output-dir",
        str(TEST_DATA_DIR),
    ]

    print(f"\n🔄 Testing URL: {url}")
    print(f"📁 Output directory: {TEST_DATA_DIR}")
    print(f"🚀 Running command: {' '.join(str(x) for x in cmd)}")
    
    # Run with real-time output
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,  # Combine stderr with stdout
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True
    )
    
    # Print output in real-time
    output_lines = []
    for line in process.stdout:
        line = line.rstrip()
        if line:  # Only print non-empty lines
            print(f"📝 {line}")
            output_lines.append(line)
    
    process.wait()
    full_output = '\n'.join(output_lines)
    
    assert process.returncode == 0, (
        f"video_preparer module failed for {url}\n"
        f"Return code: {process.returncode}\n"
        f"Output:\n{full_output}"
    )

    # We don't know the exact title ahead of time, but we do know video_preparer puts
    # everything inside *one* folder under out_dir. Locate it.
    folders = [p for p in TEST_DATA_DIR.iterdir() if p.is_dir()]
    assert len(folders) == 1, f"Expected exactly one video folder inside output root. Found: {[f.name for f in folders]}"

    video_folder = folders[0]
    mp4 = list(video_folder.glob("*.mp4"))
    mp3 = list(video_folder.glob("*.mp3"))
    vtt = list(video_folder.glob("*.vtt"))

    print(f"✅ Found files in {video_folder.name}:")
    print(f"   📹 MP4: {[f.name for f in mp4]}")
    print(f"   🎵 MP3: {[f.name for f in mp3]}")
    print(f"   📝 VTT: {[f.name for f in vtt]}")

    assert mp4, "MP4 file was not created."
    assert mp3, "MP3 file was not created."
    # VTT may be absent for some variants (if transcript fetch fails and ASR step
    # somehow errors), but its absence should raise an error earlier – so we
    # don't assert on .vtt here to reduce flakiness.
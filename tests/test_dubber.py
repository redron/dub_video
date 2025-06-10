"""
Integration tests for dubber module

This test should be run after test_video_preparer.py as it uses the prepared video data.
"""
import os
import sys
import subprocess
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ---- Configuration ---------------------------------------------------------
# Load .env file if it exists in the project root
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"📋 Loaded configuration from {ENV_FILE}")

# Use the same test data directory as video_preparer tests
TEST_DATA_DIR = Path(__file__).parent / "data"
VIDEO_NAME = "10 Second Timer with Voice Countdown"

# Skip the suite unless the maintainer explicitly opted-in.
RUN_NETWORK = os.getenv("RUN_NETWORK_TESTS") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_NETWORK,
    reason="Integration tests require network and are disabled by default.\n"
    "Set RUN_NETWORK_TESTS=1 to enable.",
)

# ---------------------------------------------------------------------------

def test_dubber_integration():
    """Run dubber module against prepared video data and check it produces the dubbed audio file."""
    
    # Check if OpenAI API key is available (from .env file or environment variable)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not found. Set it in .env file or as environment variable. Skipping dubber test.")
    
    # Check that the source VTT file exists (created by video_preparer)
    video_dir = TEST_DATA_DIR / VIDEO_NAME
    vtt_path = video_dir / f"{VIDEO_NAME}.vtt"
    
    if not vtt_path.exists():
        pytest.skip(f"VTT file not found at {vtt_path}. Run test_video_preparer first.")
    
    # Clean up any previous dubber output
    output_path = video_dir / f"{VIDEO_NAME}_dub.mp3"
    if output_path.exists():
        output_path.unlink()
    
    cmd = [
        sys.executable,
        "-m", "dubber",
        "--data-dir", str(TEST_DATA_DIR),
        "--video", VIDEO_NAME,
    ]

    print(f"\n🎙️  Testing dubber with video: {VIDEO_NAME}")
    print(f"📁 Data directory: {TEST_DATA_DIR}")
    print(f"🚀 Running command: {' '.join(str(x) for x in cmd)}")
    
    # Prepare environment with API key
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = api_key
    
    # Run with real-time output
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,  # Combine stderr with stdout
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        env=env  # Pass environment with API key
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
        f"dubber module failed for {VIDEO_NAME}\n"
        f"Return code: {process.returncode}\n"
        f"Output:\n{full_output}"
    )

    # Check that the dubbed audio file was created
    assert output_path.exists(), f"Dubbed audio file was not created at {output_path}"
    
    # Check that the file has some size (not empty)
    file_size = output_path.stat().st_size
    assert file_size > 1000, f"Dubbed audio file seems too small: {file_size} bytes"
    
    print(f"✅ Successfully created dubbed audio:")
    print(f"   🎵 File: {output_path.name}")
    print(f"   📏 Size: {file_size:,} bytes") 
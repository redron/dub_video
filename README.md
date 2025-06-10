# dub_video – Video Dubbing Preparation Utility

Automates the first stage of a dubbing pipeline:

1. **Download** a YouTube video (`yt-dlp`)  
2. **Extract** its audio track as high-quality MP3  
3. **Obtain** subtitles  
   - Fetch existing captions via *youtube-transcript-api*  
   - …or generate accurate VTT subtitles locally with *OpenAI Whisper*  

## Requirements
- Python 3.9 or higher
- Virtual environment (recommended)

## Quick start
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Basic usage with a YouTube URL:
```bash
python video_preparer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

Generate subtitles using Whisper (if no captions available):
```bash
python video_preparer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --use-whisper
```

Specify output directory:
```bash
python video_preparer.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --output-dir ./my_dubs
```

Process multiple videos:
```bash
python video_preparer.py \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  "https://www.youtube.com/watch?v=jNQXAC9IVRw" \
  --output-dir ./batch_dubs
```

For more options and details, run:
```bash
python video_preparer.py --help
```

## Running the integration tests

We use **pytest**.

```bash
# inside dub_video/
pip install -r requirements.txt      # installs pytest, yt-dlp, etc.

# 1 · quick, offline checks (ID parsing only)
pytest -m "not slow"

# 2 · full integration – actually downloads a pair of 5-second clips
pytest -m slow
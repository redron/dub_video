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

## Dubbing a video

Once you have prepared video data (video, audio, and VTT file), you can use the `dubber` module to generate a dubbed audio track using OpenAI's Text-to-Speech API.

### Configuration

The dubber requires an OpenAI API key. You can provide it in two ways:

1. **Using a .env file** (recommended):
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```
   (See `.env.sample` for an example)

2. **Using environment variable**:
   ```bash
   export OPENAI_API_KEY=your-openai-api-key-here
   ```

### Basic usage:
```bash
python -m dubber --data-dir data --video video_name
```

This will:
- Read the VTT subtitles from `data/video_name/video_name.vtt`
- Generate speech for each subtitle using OpenAI's TTS API (model: gpt-4o-mini-tts, voice: coral)
- Preserve the original timing from the VTT file
- Create a dubbed audio file at `data/video_name/video_name_dub.mp3`

### With voice configuration (future feature):
```bash
python -m dubber --data-dir data --video video_name --config voice.config
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
```

### Running integration tests in order

The integration tests need to be run in a specific order:
1. **video_preparer** tests first (to download and prepare test data)
2. **dubber** tests second (uses the prepared data)

#### Configuration for tests

You can configure the tests using either:

1. **A .env file** (recommended):
   ```
   # .env
   RUN_NETWORK_TESTS=1
   OPENAI_API_KEY=your-api-key
   ```

2. **Environment variables**:
   ```bash
   export RUN_NETWORK_TESTS=1
   export OPENAI_API_KEY=your-api-key
   ```

#### Running the tests

```bash
# With .env file configured
./run_integration_tests.sh

# Or manually:
pytest tests/test_video_preparer.py -v
pytest tests/test_dubber.py -v
```

Note: The dubber tests require an OpenAI API key and will make actual API calls to generate speech.

import argparse
import asyncio
import io
import os
from pathlib import Path

import webvtt
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydub import AudioSegment


async def text_to_speech(client, text, voice="coral", model="gpt-4o-mini-tts"):
    """
    Converts text to speech using OpenAI's TTS API.
    """
    response = await client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="mp3"
    )
    return response.content


async def main():
    """
    This is the main function of the dubber utility.
    """
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Dub a video using TTS.")
    parser.add_argument("--data-dir", type=str, required=True, help="Directory with video data.")
    parser.add_argument("--video", type=str, required=True, help="Name of the video to process.")
    parser.add_argument("--config", type=str, help="Path to voice config file.")

    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    video_name = args.video
    video_dir = data_dir / video_name

    if not video_dir.is_dir():
        print(f"Error: Video directory not found at {video_dir}")
        return

    vtt_path = video_dir / f"{video_name}.vtt"

    if not vtt_path.exists():
        print(f"Error: VTT file not found at {vtt_path}")
        return

    output_path = video_dir / f"{video_name}_dub.mp3"

    client = AsyncOpenAI()

    captions = webvtt.read(vtt_path)
    combined_audio = AudioSegment.empty()
    last_end_time = 0

    for caption in captions:
        start_time_ms = caption.start_in_seconds * 1000
        end_time_ms = caption.end_in_seconds * 1000

        # Add silence before the caption if needed
        silence_duration = start_time_ms - last_end_time
        if silence_duration > 0:
            combined_audio += AudioSegment.silent(duration=silence_duration)

        print(f"Generating audio for: {caption.text}")
        audio_data = await text_to_speech(client, caption.text)

        segment_audio = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
        combined_audio += segment_audio

        last_end_time = end_time_ms

    combined_audio.export(output_path, format="mp3")

    print(f"Dubbed audio saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main()) 
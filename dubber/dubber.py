import argparse
import asyncio
import io
import os
from pathlib import Path
import tempfile

import webvtt
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydub import AudioSegment
from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip


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


def create_dubbed_video(video_path, captions, tts_segments, output_video_path, output_audio_path):
    """
    Creates a dubbed video by muting original audio during captions and overlaying TTS.
    Also exports the dubbed audio as a separate file.
    
    Args:
        video_path: Path to the original video file
        captions: List of WebVTT caption objects
        tts_segments: List of tuples (start_time, end_time, audio_data)
        output_video_path: Path for the output video file
        output_audio_path: Path for the output audio file
    """
    print(f"Loading video from {video_path}")
    video = VideoFileClip(str(video_path))
    
    # Get the original audio
    original_audio = video.audio
    
    # Create a modified audio track
    # We'll work with the audio as an array and mute sections
    audio_duration = video.duration
    
    # Export original audio to work with it
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_original:
        original_audio.write_audiofile(temp_original.name)
        original_audio_segment = AudioSegment.from_mp3(temp_original.name)
    
    # Create a copy of the original audio that we'll modify
    modified_audio = original_audio_segment
    
    # Process each TTS segment
    audio_clips = []
    temp_files = []  # Keep track of temporary files for cleanup
    
    try:
        for i, (start_time, end_time, audio_data) in enumerate(tts_segments):
            # Convert times to milliseconds
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            
            # Create TTS audio segment
            tts_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            
            # Mute the original audio during this caption
            # Split the audio into three parts: before, during, and after
            before = modified_audio[:start_ms]
            during = AudioSegment.silent(duration=(end_ms - start_ms))
            after = modified_audio[end_ms:]
            
            # Combine the parts
            modified_audio = before + during + after
            
            # Save TTS segment to temporary file for moviepy
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_tts:
                tts_segment.export(temp_tts.name, format="mp3")
                temp_files.append(temp_tts.name)
                # Create audio clip positioned at the right time
                tts_clip = AudioFileClip(temp_tts.name).with_start(start_time)
                audio_clips.append(tts_clip)
    
        # Export modified original audio
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_modified:
            modified_audio.export(temp_modified.name, format="mp3")
            temp_files.append(temp_modified.name)
            modified_audio_clip = AudioFileClip(temp_modified.name)
        
        # Combine all audio clips
        final_audio = CompositeAudioClip([modified_audio_clip] + audio_clips)
        
        # Set the new audio to the video
        final_video = video.with_audio(final_audio)
        
        # Write the output video
        print(f"Writing dubbed video to {output_video_path}")
        final_video.write_videofile(
            str(output_video_path),
            codec='libx264',
            audio_codec='aac'
        )
        
        # Export the dubbed audio separately
        print(f"Writing dubbed audio to {output_audio_path}")
        final_audio.write_audiofile(str(output_audio_path))
        
    finally:
        # Clean up - ensure all resources are closed and temp files deleted
        try:
            video.close()
        except:
            pass
        
        try:
            if 'final_video' in locals():
                final_video.close()
        except:
            pass
        
        try:
            if 'final_audio' in locals():
                final_audio.close()
        except:
            pass
        
        # Close all audio clips
        for clip in audio_clips:
            try:
                clip.close()
            except:
                pass
        
        # Delete all temporary files
        try:
            os.unlink(temp_original.name)
        except:
            pass
        
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass


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

    # Check for required files
    video_path = video_dir / f"{video_name}.mp4"
    vtt_path = video_dir / f"{video_name}.vtt"
    output_video_path = video_dir / f"{video_name}_dub.mp4"
    output_audio_path = video_dir / f"{video_name}_dub.mp3"

    if not video_path.exists():
        print(f"Error: Video file not found at {video_path}")
        return

    if not vtt_path.exists():
        print(f"Error: VTT file not found at {vtt_path}")
        return

    print(f"Processing video: {video_name}")
    print(f"Reading captions from: {vtt_path}")

    client = AsyncOpenAI()
    captions = webvtt.read(vtt_path)
    
    # Generate TTS for each caption
    tts_segments = []
    
    for i, caption in enumerate(captions):
        print(f"Generating TTS {i+1}/{len(captions)}: {caption.text}")
        audio_data = await text_to_speech(client, caption.text)
        tts_segments.append((
            caption.start_in_seconds,
            caption.end_in_seconds,
            audio_data
        ))
    
    # Create the dubbed video and audio
    create_dubbed_video(video_path, captions, tts_segments, output_video_path, output_audio_path)
    
    print(f"✅ Dubbed video saved to {output_video_path}")
    print(f"✅ Dubbed audio saved to {output_audio_path}")


if __name__ == "__main__":
    asyncio.run(main()) 
"""
Audio recording and processing utilities
"""
import os
import base64
import tempfile
import pyaudio
import wave
from typing import Tuple, Optional

def record_audio(duration: int = 5, sample_rate: int = 16000) -> Tuple[bytes, str]:
    """
    Record audio from the microphone
    
    Args:
        duration: Recording duration in seconds
        sample_rate: Audio sample rate (Hz)
        
    Returns:
        Tuple of (audio_bytes, temp_file_path)
        
    Raises:
        Exception: If microphone hardware is not available or if there's a recording error
    """
    # Audio parameters
    chunk = 1024  # Record in chunks of 1024 samples
    sample_format = pyaudio.paInt16  # 16 bits per sample
    channels = 1  # Mono
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    p = None
    
    try:
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Check if we can open the microphone
        try:
            stream = p.open(
                format=sample_format,
                channels=channels,
                rate=sample_rate,
                input=True,
                frames_per_buffer=chunk,
                start=False
            )
        except Exception as e:
            # Close PyAudio if microphone couldn't be opened
            if p:
                p.terminate()
            raise Exception(f"Could not access microphone. {str(e)}")
        
        # Open stream with error checking
        stream = p.open(
            format=sample_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        # Record data
        frames = []
        seconds = int(sample_rate / chunk * duration)
        
        print(f"Recording audio for {duration} seconds...")
        for i in range(0, seconds):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)
            
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        
        # Save as WAV file
        with wave.open(temp_file_path, 'wb') as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(sample_format))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
            
        # Read the file back as bytes
        with open(temp_file_path, 'rb') as f:
            audio_bytes = f.read()
            
        return audio_bytes, temp_file_path
        
    except Exception as e:
        # Clean up the temp file on error
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        raise Exception(f"Error recording audio: {str(e)}")
        
    finally:
        if p:
            p.terminate()


def encode_audio(audio_bytes: bytes) -> str:
    """
    Encode audio bytes to base64 string
    
    Args:
        audio_bytes: Raw audio bytes to encode
        
    Returns:
        Base64 encoded string
    """
    return base64.b64encode(audio_bytes).decode('utf-8')


def cleanup_audio_file(file_path: str) -> None:
    """
    Delete temporary audio file
    
    Args:
        file_path: Path to the audio file to delete
    """
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"Removed temporary audio file: {file_path}")
        except Exception as e:
            print(f"Error removing temporary audio file: {str(e)}")
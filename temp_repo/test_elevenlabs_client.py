"""
Test using ElevenLabs client approach
"""
import os
from elevenlabs.client import ElevenLabs

# Set API key from environment variable
api_key = os.environ.get("ELEVENLABS_API_KEY")
print(f"API key length: {len(api_key) if api_key else 'None'}")

# Create client
client = ElevenLabs(api_key=api_key)

# Get available voices
print("Getting available voices...")
try:
    response = client.voices.get_all()
    print(f"Found {len(response.voices)} voices")
    for voice in response.voices[:3]:  # Show first 3
        print(f"  - {voice.name} (ID: {voice.voice_id})")
except Exception as e:
    print(f"Error getting voices: {e}")

# Try simple text-to-speech generation
text = "Hello, this is a test of the ElevenLabs text-to-speech API."
print(f"Generating audio for: {text}")
try:
    audio = client.text_to_speech.convert(
        text=text,
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
        model_id="eleven_multilingual_v2"
    )
    # Convert iterator to bytes
    audio_bytes = b"".join(audio)
    print(f"Generated audio of size: {len(audio_bytes)} bytes")
except Exception as e:
    print(f"Error generating audio: {e}")
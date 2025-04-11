"""
Simple ElevenLabs test script - using the newer API format
"""
import os
from elevenlabs import generate, voices, play

# Set API key from environment variable
api_key = os.environ.get("ELEVENLABS_API_KEY")
print(f"API key length: {len(api_key) if api_key else 'None'}")

# Get available voices
print("Getting available voices...")
try:
    available_voices = voices()
    print(f"Found {len(available_voices)} voices")
    for voice in available_voices[:3]:  # Show first 3
        print(f"  - {voice.name} (ID: {voice.voice_id})")
except Exception as e:
    print(f"Error getting voices: {e}")

# Try simple text-to-speech generation
text = "Hello, this is a test of the ElevenLabs text-to-speech API."
print(f"Generating audio for: {text}")
try:
    audio = generate(text=text, voice="Rachel")
    print(f"Generated audio of size: {len(audio)} bytes")
except Exception as e:
    print(f"Error generating audio: {e}")
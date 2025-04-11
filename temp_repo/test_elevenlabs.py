"""
Test ElevenLabs imports and basic functionality
"""
import os
import sys

print("ElevenLabs Test Script")
print("-" * 40)
print(f"Python version: {sys.version}")
print("-" * 40)

try:
    import elevenlabs
    print(f"ElevenLabs version: {elevenlabs.__version__}")
    print(f"Available modules: {dir(elevenlabs)}")
    
    # Check if Client exists
    if hasattr(elevenlabs, 'Client'):
        print("Client class exists in elevenlabs package")
        print(f"Client attributes: {dir(elevenlabs.Client)}")
    else:
        print("Client class NOT found in elevenlabs package")
    
    # Check common functions/classes
    for name in ['generate', 'play', 'save', 'voices', 'set_api_key', 'api_key']:
        if hasattr(elevenlabs, name):
            print(f"✓ Found: elevenlabs.{name}")
        else:
            print(f"✗ Missing: elevenlabs.{name}")
            
    print("-" * 40)
    print("Trying to read API key...")
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        print("API key found in environment variables")
        print(f"API key length: {len(api_key)}")
        
        # Try to use the API directly
        try:
            if hasattr(elevenlabs, 'set_api_key'):
                elevenlabs.set_api_key(api_key)
                print("Successfully set API key using set_api_key()")
            else:
                print("Trying to use Client class...")
                client = elevenlabs.Client(api_key=api_key)
                print("Successfully created Client instance")
                
                # Try to get voices
                try:
                    voices = client.voices.get_all()
                    print(f"Successfully retrieved {len(voices)} voices")
                    for voice in voices[:3]:  # Show first 3
                        print(f"  - {voice.name} (ID: {voice.voice_id})")
                except Exception as e:
                    print(f"Error getting voices: {e}")
                    
        except Exception as e:
            print(f"Error using API key: {e}")
    else:
        print("API key not found in environment variables")
        
except ImportError as e:
    print(f"Error importing elevenlabs: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
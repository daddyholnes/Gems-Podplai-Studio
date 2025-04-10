"""
Text-to-Speech utilities using ElevenLabs API
"""
import os
import base64
import tempfile
import hashlib
import streamlit as st
from typing import Optional, Dict, List, Tuple, Any
from elevenlabs import generate, voices, Voice, set_api_key
from elevenlabs.api import Models

# Initialize API key
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if ELEVENLABS_API_KEY:
    set_api_key(ELEVENLABS_API_KEY)

# Cache directory for storing generated audio
CACHE_DIR = "data/tts_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Default voice settings
DEFAULT_VOICE = "Rachel"
DEFAULT_MODEL = "eleven_turbo_v2"
STABILITY = 0.5
CLARITY = 0.5
STYLE = 0.0


def get_available_voices() -> List[Tuple[str, str]]:
    """
    Get available ElevenLabs voices
    
    Returns:
        List of (voice_id, voice_name) tuples
    """
    try:
        voice_list = voices()
        return [(voice.voice_id, voice.name) for voice in voice_list]
    except Exception as e:
        print(f"Error fetching voices: {e}")
        # Return a few default voices if API call fails
        return [
            ("21m00Tcm4TlvDq8ikWAM", "Rachel"),
            ("AZnzlk1XvdvUeBnXmlld", "Domi"),
            ("EXAVITQu4vr4xnSDxMaL", "Bella"),
            ("ErXwobaYiN019PkySvjV", "Antoni"),
            ("MF3mGyEYCl7XYWbV9V6O", "Elli"),
            ("TxGEqnHWrfWFTfGW9XjX", "Josh"),
            ("VR6AewLTigWG4xSOukaG", "Arnold"),
            ("pNInz6obpgDQGcFmaJgB", "Adam"),
            ("yoZ06aMxZJJ28mfd3POQ", "Sam"),
        ]


def get_available_models() -> List[Tuple[str, str]]:
    """
    Get available ElevenLabs models
    
    Returns:
        List of (model_id, model_name) tuples
    """
    try:
        models = Models.from_api()
        return [(model.model_id, model.name) for model in models]
    except Exception as e:
        print(f"Error fetching models: {e}")
        # Return a few default models if API call fails
        return [
            ("eleven_turbo_v2", "Eleven Turbo v2"),
            ("eleven_multilingual_v2", "Eleven Multilingual v2"),
            ("eleven_monolingual_v1", "Eleven Monolingual v1"),
        ]


def generate_audio_hash(text: str, voice_id: str, model_id: str) -> str:
    """
    Generate a unique hash for the TTS request parameters
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID
        model_id: ElevenLabs model ID
        
    Returns:
        MD5 hash string
    """
    params_str = f"{text}|{voice_id}|{model_id}|{STABILITY}|{CLARITY}|{STYLE}"
    return hashlib.md5(params_str.encode()).hexdigest()


def text_to_speech(
    text: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    use_cache: bool = True
) -> Tuple[Optional[str], Optional[str]]:
    """
    Convert text to speech using ElevenLabs API
    
    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID (defaults to Rachel if None)
        model_id: ElevenLabs model ID (defaults to eleven_turbo_v2 if None)
        use_cache: Whether to use cache for previously generated audio
        
    Returns:
        Tuple of (file_path, base64_audio) if successful, or (None, None) if failed
    """
    # Use default values if not provided
    voice_id = voice_id or DEFAULT_VOICE
    model_id = model_id or DEFAULT_MODEL
    
    # Check if API key is set
    if not ELEVENLABS_API_KEY:
        st.error("ElevenLabs API key is not set. Please add it to your environment variables.")
        return None, None
    
    # Generate cache key
    cache_key = generate_audio_hash(text, voice_id, model_id)
    cache_path = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
    
    # Check cache if enabled
    if use_cache and os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                audio_bytes = f.read()
                base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                return cache_path, base64_audio
        except Exception as e:
            print(f"Cache read error: {e}")
            # Continue to generate if cache read failed
    
    # Generate audio
    try:
        audio = generate(
            text=text,
            voice=voice_id,
            model=model_id,
            stability=STABILITY,
            clarity=CLARITY,
            style=STYLE
        )
        
        # Save to cache if enabled
        if use_cache:
            with open(cache_path, 'wb') as f:
                f.write(audio)
            with open(cache_path, 'rb') as f:
                audio_bytes = f.read()
        else:
            # Create a temporary file for the audio
            temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            with open(temp_path, 'wb') as f:
                f.write(audio)
            with open(temp_path, 'rb') as f:
                audio_bytes = f.read()
            
            return temp_path, base64.b64encode(audio_bytes).decode('utf-8')
        
        return cache_path, base64.b64encode(audio_bytes).decode('utf-8')
        
    except Exception as e:
        st.error(f"Error generating speech: {e}")
        return None, None


def render_tts_controls(default_voice: str = DEFAULT_VOICE, default_model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Render TTS controls in the Streamlit sidebar
    
    Args:
        default_voice: Default voice name
        default_model: Default model ID
        
    Returns:
        Dictionary with voice_id and model_id
    """
    with st.sidebar.expander("🔊 Text-to-Speech Settings", expanded=False):
        st.write("Configure ElevenLabs text-to-speech settings")
        
        # Voice selection
        voice_options = get_available_voices()
        voice_names = [name for _, name in voice_options]
        voice_ids = [id for id, _ in voice_options]
        
        # Find default voice index
        default_voice_index = 0
        for i, (_, name) in enumerate(voice_options):
            if name == default_voice:
                default_voice_index = i
                break
        
        selected_voice_index = st.selectbox(
            "Voice",
            options=range(len(voice_options)),
            format_func=lambda i: voice_names[i],
            index=default_voice_index
        )
        
        selected_voice_id = voice_ids[selected_voice_index]
        
        # Model selection
        model_options = get_available_models()
        model_names = [name for _, name in model_options]
        model_ids = [id for id, _ in model_options]
        
        # Find default model index
        default_model_index = 0
        for i, (id, _) in enumerate(model_options):
            if id == default_model:
                default_model_index = i
                break
        
        selected_model_index = st.selectbox(
            "Model",
            options=range(len(model_options)),
            format_func=lambda i: model_names[i],
            index=default_model_index
        )
        
        selected_model_id = model_ids[selected_model_index]
        
        # Use cache option
        use_cache = st.checkbox("Cache generated audio", value=True,
                              help="Save generated audio to avoid redundant API calls")
        
        return {
            "voice_id": selected_voice_id,
            "model_id": selected_model_id,
            "use_cache": use_cache
        }


def render_play_button(message_text: str, key: str):
    """
    Render a play button that converts text to speech on click
    
    Args:
        message_text: Text to convert to speech
        key: Unique key for this button instance
    """
    if not ELEVENLABS_API_KEY:
        # Don't show the button if API key is not set
        return
    
    # Get TTS settings from session state or use defaults
    tts_settings = st.session_state.get('tts_settings', {
        "voice_id": DEFAULT_VOICE,
        "model_id": DEFAULT_MODEL,
        "use_cache": True
    })
    
    # Create unique key for this button
    button_key = f"tts_button_{key}"
    player_key = f"tts_player_{key}"
    
    # Show/hide audio player in session state
    if f"{player_key}_show" not in st.session_state:
        st.session_state[f"{player_key}_show"] = False
    
    if f"{player_key}_path" not in st.session_state:
        st.session_state[f"{player_key}_path"] = None
    
    # Play button
    if st.button("🔊", key=button_key, help="Play this message (Text-to-Speech)"):
        with st.spinner("Generating audio..."):
            audio_path, _ = text_to_speech(
                text=message_text,
                voice_id=tts_settings.get("voice_id"),
                model_id=tts_settings.get("model_id"),
                use_cache=tts_settings.get("use_cache", True)
            )
            
            if audio_path:
                st.session_state[f"{player_key}_path"] = audio_path
                st.session_state[f"{player_key}_show"] = True
    
    # Show audio player if available
    if st.session_state[f"{player_key}_show"] and st.session_state[f"{player_key}_path"]:
        audio_path = st.session_state[f"{player_key}_path"]
        if os.path.exists(audio_path):
            st.audio(audio_path)
"""
Enhanced audio recording with WebRTC for AI Chat Studio
Provides improved audio recording with configurable duration and visual feedback
"""
import os
import time
import base64
import tempfile
import numpy as np
import streamlit as st
import av
import wave
from typing import Tuple, Optional, List, Dict, Any, Callable
from streamlit_webrtc import (
    AudioProcessorBase,
    RTCConfiguration,
    WebRtcMode,
    webrtc_streamer,
)


# WebRTC configuration using default STUN servers
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)


class AudioRecorder(AudioProcessorBase):
    """Audio recorder processor for WebRTC"""
    
    def __init__(self, 
                 key_prefix: str = "audio_recorder",
                 max_duration: int = 60,
                 sample_rate: int = 16000):
        """
        Initialize audio recorder
        
        Args:
            key_prefix: Prefix for Streamlit session state keys
            max_duration: Maximum recording duration in seconds
            sample_rate: Audio sample rate
        """
        self.key_prefix = key_prefix
        self.max_duration = max_duration
        self.sample_rate = sample_rate
        self.audio_frames: List[np.ndarray] = []
        self.start_time = None
        self.is_recording = False
        
        # Initialize session state variables
        if f"{key_prefix}_frames" not in st.session_state:
            st.session_state[f"{key_prefix}_frames"] = []
        if f"{key_prefix}_recording" not in st.session_state:
            st.session_state[f"{key_prefix}_recording"] = False
        if f"{key_prefix}_elapsed" not in st.session_state:
            st.session_state[f"{key_prefix}_elapsed"] = 0.0
        if f"{key_prefix}_file_path" not in st.session_state:
            st.session_state[f"{key_prefix}_file_path"] = None
        if f"{key_prefix}_base64" not in st.session_state:
            st.session_state[f"{key_prefix}_base64"] = None
            
    def start(self):
        """Start recording"""
        self.audio_frames = []
        self.start_time = time.time()
        self.is_recording = True
        st.session_state[f"{self.key_prefix}_recording"] = True
        st.session_state[f"{self.key_prefix}_elapsed"] = 0.0
        st.session_state[f"{self.key_prefix}_frames"] = []
        
    def stop(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Stop recording and save the audio file
        
        Returns:
            Tuple of (file_path, base64_audio) if successful, or (None, None) if not
        """
        self.is_recording = False
        st.session_state[f"{self.key_prefix}_recording"] = False
        
        if not self.audio_frames:
            return None, None
        
        # Save audio frames to a temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        file_path = temp_file.name
        temp_file.close()
        
        # Save as WAV file
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(1)  # Mono
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                
                # Convert float32 samples to int16
                audio_data = np.concatenate(self.audio_frames)
                audio_data = (audio_data * 32767).astype(np.int16).tobytes()
                wf.writeframes(audio_data)
                
            # Read and encode to base64
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()
                base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
                
            # Save to session state
            st.session_state[f"{self.key_prefix}_file_path"] = file_path
            st.session_state[f"{self.key_prefix}_base64"] = base64_audio
            
            return file_path, base64_audio
        
        except Exception as e:
            st.error(f"Error saving audio: {e}")
            # Clean up the file if there was an error
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            return None, None
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        """Process audio frame"""
        if self.is_recording:
            # Update elapsed time
            elapsed = time.time() - self.start_time
            st.session_state[f"{self.key_prefix}_elapsed"] = elapsed
            
            # Check if we've hit the maximum duration
            if elapsed >= self.max_duration:
                self.is_recording = False
                st.session_state[f"{self.key_prefix}_recording"] = False
                
            # Convert to numpy array and append to frames
            audio_data = frame.to_ndarray()[0]  # Get first channel
            self.audio_frames.append(audio_data)
            st.session_state[f"{self.key_prefix}_frames"] = self.audio_frames
            
        return frame
    
    def get_elapsed_time(self) -> float:
        """Get elapsed recording time in seconds"""
        return st.session_state[f"{self.key_prefix}_elapsed"]
    
    def is_currently_recording(self) -> bool:
        """Check if currently recording"""
        return st.session_state[f"{self.key_prefix}_recording"]
    
    def cleanup(self):
        """Clean up temporary audio file"""
        file_path = st.session_state.get(f"{self.key_prefix}_file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                st.session_state[f"{self.key_prefix}_file_path"] = None
                st.session_state[f"{self.key_prefix}_base64"] = None
                print(f"Removed temporary audio file: {file_path}")
            except Exception as e:
                print(f"Error removing temporary audio file: {str(e)}")


def create_webrtc_audio_recorder(
    key: str = "audio_recorder",
    max_duration: int = 60,
    sample_rate: int = 16000,
    audio_html_attrs: Optional[Dict[str, Any]] = None,
    start_recording_label: str = "Start Recording",
    stop_recording_label: str = "Stop Recording",
) -> AudioRecorder:
    """
    Create a WebRTC audio recorder with controls
    
    Args:
        key: Unique key for this recorder instance
        max_duration: Maximum recording duration in seconds
        sample_rate: Audio sample rate
        audio_html_attrs: HTML attributes for audio element
        start_recording_label: Label for start recording button
        stop_recording_label: Label for stop recording button
        
    Returns:
        AudioRecorder instance
    """
    # Create recorder instance
    recorder = AudioRecorder(
        key_prefix=key,
        max_duration=max_duration,
        sample_rate=sample_rate
    )
    
    # Create WebRTC streamer
    ctx = webrtc_streamer(
        key=key,
        mode=WebRtcMode.SENDONLY,
        rtc_configuration=RTC_CONFIGURATION,
        audio_processor_factory=lambda: recorder,
        media_stream_constraints={"audio": True, "video": False},
    )
    
    # Session state for recording state
    if f"{key}_started" not in st.session_state:
        st.session_state[f"{key}_started"] = False
    
    # Start/Stop control buttons
    col1, col2 = st.columns(2)
    
    if ctx.state.playing:
        if col1.button(
            start_recording_label,
            key=f"{key}_start_btn",
            disabled=recorder.is_currently_recording(),
            use_container_width=True
        ):
            recorder.start()
            st.session_state[f"{key}_started"] = True
        
        if col2.button(
            stop_recording_label,
            key=f"{key}_stop_btn",
            disabled=not recorder.is_currently_recording(),
            use_container_width=True
        ):
            file_path, base64_audio = recorder.stop()
            if file_path:
                st.success("Audio recorded successfully!")
                
                # Show audio player
                audio_container = st.container()
                with audio_container:
                    st.audio(file_path, **audio_html_attrs or {})
    
    # Display progress bar if recording
    if ctx.state.playing and recorder.is_currently_recording():
        elapsed = recorder.get_elapsed_time()
        progress = min(elapsed / max_duration, 1.0)
        
        # Display timer
        st.markdown(f"Recording: **{elapsed:.1f}s** / {max_duration}s")
        
        # Display progress bar
        st.progress(progress)
    
    return recorder


def audio_recorder_ui(
    key: str = "audio_recorder",
    title: str = "Audio Recording",
    description: str = "Click the start button to begin recording audio. Click stop when you're done.",
    durations: List[int] = [30, 60, 120],
    show_description: bool = True,
    show_playback: bool = True,
    max_duration: int = 60,
    sample_rate: int = 16000,
) -> Optional[str]:
    """
    Create a complete audio recorder UI with configurable durations
    
    Args:
        key: Unique key for this recorder instance
        title: Title for the recorder section
        description: Description text to display
        durations: List of recording durations to offer (in seconds)
        show_description: Whether to show the description text
        show_playback: Whether to show audio playback controls
        max_duration: Default maximum recording duration in seconds
        sample_rate: Audio sample rate
    
    Returns:
        Base64-encoded audio string if recording was made, None otherwise
    """
    # Display title and description
    st.markdown(f"### {title}")
    if show_description:
        st.markdown(description)
    
    # Allow user to select recording duration
    selected_duration = st.select_slider(
        "Select recording duration (seconds):",
        options=durations,
        value=min([d for d in durations if d >= max_duration], default=durations[0]),
        key=f"{key}_duration"
    )
    
    # Create the recorder with the selected duration
    recorder = create_webrtc_audio_recorder(
        key=key,
        max_duration=selected_duration,
        sample_rate=sample_rate,
        audio_html_attrs={"style": "width: 100%"},
        start_recording_label="🎙️ Start Recording",
        stop_recording_label="⏹️ Stop Recording"
    )
    
    # Return the base64-encoded audio if available
    return st.session_state.get(f"{key}_base64")
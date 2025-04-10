"""
WebRTC-based audio recording for Streamlit applications

This module provides enhanced audio recording capabilities using WebRTC,
which offers better quality and real-time processing compared to basic
audio recording.
"""

import base64
import numpy as np
import streamlit as st
import av
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from streamlit_webrtc import (
    webrtc_streamer, 
    WebRtcMode, 
    RTCConfiguration, 
    VideoProcessorBase,
    AudioProcessorBase
)
import tempfile
import os
import time
import uuid

# Configure RTC for STUN servers
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

class AudioProcessor(AudioProcessorBase):
    """Audio processor for WebRTC streaming that saves audio frames to a buffer"""
    
    def __init__(self, max_duration: int = 60):
        """
        Initialize the audio processor with the specified maximum duration
        
        Args:
            max_duration: Maximum recording duration in seconds
        """
        self.audio_buffer = []
        self.sample_rate = 48000  # WebRTC typically uses 48kHz
        self.channels = 1  # Mono audio
        self.max_frames = max_duration * self.sample_rate
        self.start_time = None
        self.recording_complete = False
        self.stopped = False
        self.output_file = None
        
        # Create a temporary file to store the audio
        fd, self.output_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        """
        Process each incoming audio frame
        
        Args:
            frame: Audio frame from WebRTC
            
        Returns:
            The unmodified audio frame
        """
        if self.stopped or self.recording_complete:
            return frame
            
        if self.start_time is None:
            self.start_time = time.time()
            
        # Convert frame to numpy array
        sound_array = frame.to_ndarray()
        
        # Append to buffer
        self.audio_buffer.append(sound_array)
        
        # Check if we've reached the maximum duration
        total_samples = sum(len(chunk) for chunk in self.audio_buffer)
        if total_samples >= self.max_frames:
            self.recording_complete = True
            self._save_audio()
            
        return frame
    
    def stop(self):
        """Stop recording and save the audio file"""
        self.stopped = True
        self._save_audio()
    
    def _save_audio(self):
        """Save the recorded audio to a WAV file"""
        if not self.audio_buffer:
            return
            
        try:
            import soundfile as sf
            
            # Concatenate all audio chunks
            audio_data = np.concatenate(self.audio_buffer, axis=0)
            
            # Save as WAV file
            sf.write(
                self.output_path, 
                audio_data, 
                self.sample_rate, 
                format='WAV'
            )
            
            # Set the output file flag
            self.output_file = self.output_path
            
        except Exception as e:
            st.error(f"Error saving audio: {str(e)}")
    
    @property
    def recording_duration(self) -> float:
        """Get the current recording duration in seconds"""
        if self.start_time is None:
            return 0
        return time.time() - self.start_time
        

def audio_recorder_ui(
    key: str = "webrtc_recorder",
    title: str = "Audio Recorder",
    description: str = "Record audio for transcription or analysis",
    durations: List[int] = [30, 60, 120, 300],
    show_description: bool = True,
    show_playback: bool = True
) -> Optional[str]:
    """
    Display a WebRTC-based audio recorder widget
    
    Args:
        key: Unique key for the widget
        title: Title to display above the recorder
        description: Description text
        durations: List of recording duration options in seconds
        show_description: Whether to show the description
        show_playback: Whether to show audio playback after recording
    
    Returns:
        Base64-encoded audio data if recording is complete, None otherwise
    """
    # Session state for audio data
    if f"{key}_data" not in st.session_state:
        st.session_state[f"{key}_data"] = None
    if f"{key}_file_path" not in st.session_state:
        st.session_state[f"{key}_file_path"] = None
    if f"{key}_duration" not in st.session_state:
        st.session_state[f"{key}_duration"] = durations[0]
    
    # Display title and description
    st.subheader(title)
    if show_description:
        st.write(description)
    
    # Duration selector
    selected_duration = st.select_slider(
        "Recording duration (seconds)",
        options=durations,
        value=st.session_state[f"{key}_duration"],
        key=f"{key}_duration_slider"
    )
    
    # Update session state if duration changed
    if selected_duration != st.session_state[f"{key}_duration"]:
        st.session_state[f"{key}_duration"] = selected_duration
        
    # Create columns for controls
    col1, col2 = st.columns(2)
    
    # WebRTC audio recorder in first column
    with col1:
        # Audio processor state
        if f"{key}_processor" not in st.session_state:
            st.session_state[f"{key}_processor"] = AudioProcessor(
                max_duration=selected_duration
            )
        
        # Create the WebRTC streamer
        webrtc_ctx = webrtc_streamer(
            key=key,
            mode=WebRtcMode.SENDONLY,
            audio_processor_factory=lambda: st.session_state[f"{key}_processor"],
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"audio": True, "video": False},
        )
        
        # Check if streamer is active
        if webrtc_ctx.state.playing:
            # Show recording status
            elapsed = st.session_state[f"{key}_processor"].recording_duration
            st.write(f"Recording... ({elapsed:.1f}s / {selected_duration}s)")
            
            progress = min(1.0, elapsed / selected_duration)
            st.progress(progress)
        
        # When stopped, save the recording
        elif webrtc_ctx.state.playing == False and hasattr(st.session_state, f"{key}_processor"):
            processor = st.session_state[f"{key}_processor"]
            
            # Stop the processor to ensure audio is saved
            if not processor.stopped:
                processor.stop()
                
            # Check if we have an output file
            if processor.output_file and os.path.exists(processor.output_file):
                # Save file path to session state
                st.session_state[f"{key}_file_path"] = processor.output_file
                
                # Read the audio file and encode as base64
                with open(processor.output_file, "rb") as f:
                    audio_bytes = f.read()
                    st.session_state[f"{key}_data"] = base64.b64encode(audio_bytes).decode("utf-8")
                
                st.success("Recording saved!")
    
    # Controls for recorded audio in second column
    with col2:
        # Reset button
        if st.button("Reset Recording", key=f"{key}_reset"):
            # Clear session state
            st.session_state[f"{key}_data"] = None
            st.session_state[f"{key}_file_path"] = None
            
            # Create new processor
            st.session_state[f"{key}_processor"] = AudioProcessor(
                max_duration=selected_duration
            )
            
            st.experimental_rerun()
    
    # Display recorded audio playback
    if show_playback and st.session_state[f"{key}_file_path"]:
        st.audio(st.session_state[f"{key}_file_path"])
        
    # Return base64-encoded audio data
    return st.session_state[f"{key}_data"]
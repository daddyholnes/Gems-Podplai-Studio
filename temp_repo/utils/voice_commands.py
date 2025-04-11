"""
Voice Command Integration for accessibility
This module provides speech recognition and voice command processing
"""

import os
import time
import threading
import json
import pyaudio
import wave
import tempfile
import speech_recognition as sr
from typing import Dict, List, Callable, Optional, Tuple

# Command mapping: Maps spoken phrases to actions
COMMAND_MAPPING = {
    # Navigation commands
    "new chat": "new_chat",
    "clear chat": "new_chat",
    "start new": "new_chat",
    "logout": "logout",
    
    # Model selection commands
    "use gemini": "select_model_gemini",
    "switch to gemini": "select_model_gemini",
    "use claude": "select_model_claude",
    "switch to claude": "select_model_claude",
    "use gpt": "select_model_gpt",
    "switch to gpt": "select_model_gpt",
    "use openai": "select_model_gpt",
    "switch to openai": "select_model_gpt",
    
    # Settings commands
    "increase temperature": "increase_temperature",
    "more creative": "increase_temperature",
    "decrease temperature": "decrease_temperature",
    "more precise": "decrease_temperature",
    
    # Input commands
    "upload image": "upload_image",
    "record audio": "record_audio",
    "upload file": "upload_file",
    "upload document": "upload_file",
    
    # Send message commands
    "send message": "send_message",
    "submit message": "send_message",
    
    # Accessibility commands
    "stop listening": "stop_voice_commands",
    "pause voice commands": "stop_voice_commands",
    "start listening": "start_voice_commands", 
    "resume voice commands": "start_voice_commands",
    "help": "show_voice_help",
    "voice commands help": "show_voice_help",
    "what can I say": "show_voice_help",
}

class VoiceCommandProcessor:
    """
    Handles voice command recognition and processing
    """
    def __init__(self, callback_registry: Dict[str, Callable] = None):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_listening = False
        self.listen_thread = None
        self.callback_registry = callback_registry or {}
        self.adjust_for_ambient_noise()
        
    def adjust_for_ambient_noise(self):
        """Calibrate the recognizer for ambient noise levels"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                print("Ambient noise calibration complete")
        except Exception as e:
            print(f"Could not calibrate for ambient noise: {str(e)}")
    
    def register_callback(self, command_name: str, callback_function: Callable):
        """Register a callback function for a specific command"""
        self.callback_registry[command_name] = callback_function
    
    def start_listening(self):
        """Start the voice command listener in a separate thread"""
        if self.is_listening:
            return
            
        self.is_listening = True
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
    def stop_listening(self):
        """Stop the voice command listener"""
        self.is_listening = False
        if self.listen_thread:
            # The thread will exit on its own when is_listening becomes False
            self.listen_thread = None
    
    def _listen_loop(self):
        """Continuous listening loop that runs in a separate thread"""
        while self.is_listening:
            try:
                self._process_audio()
            except Exception as e:
                print(f"Error in voice command listener: {str(e)}")
                time.sleep(1)  # Prevent tight loop on error
    
    def _process_audio(self):
        """Listen for audio and process commands"""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                
                # Attempt to recognize speech
                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"Voice command detected: {text}")
                    
                    # Process the detected command
                    self._process_command(text)
                    
                except sr.UnknownValueError:
                    # Speech was unintelligible
                    pass
                except sr.RequestError as e:
                    print(f"Could not request results from Google Speech Recognition service: {e}")
                
        except Exception as e:
            print(f"Error capturing audio: {str(e)}")
    
    def _process_command(self, text: str):
        """
        Process the recognized text and execute the appropriate command
        
        Args:
            text: The recognized speech text
        """
        # Check if the text directly matches any command phrase
        command_action = None
        
        # Look for exact command matches
        for phrase, action in COMMAND_MAPPING.items():
            if phrase in text:
                command_action = action
                break
                
        # If a command was found, execute the associated callback
        if command_action and command_action in self.callback_registry:
            # Call the registered function for this command
            callback = self.callback_registry[command_action]
            callback()
        
        # If no command matches were found but there's text to send
        elif "send message" in text or "submit message" in text:
            # Extract the message content (if any)
            parts = text.split("message", 1)
            if len(parts) > 1 and parts[1].strip():
                message = parts[1].strip()
                if "send_message" in self.callback_registry:
                    self.callback_registry["send_message"](message)
        
        # For dictation mode
        elif "dictate" in text and len(text) > 10:
            # Strip "dictate" and any surrounding words to get the message
            message = text.replace("dictate", "").strip()
            if message and "send_message" in self.callback_registry:
                self.callback_registry["send_message"](message)


def record_voice_command(duration=3) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Record a short audio clip for voice command processing
    
    Args:
        duration: Recording duration in seconds
        
    Returns:
        Tuple of (audio_bytes, temp_file_path) or (None, None) on error
    """
    # Audio parameters
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    sample_rate = 16000
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file_path = temp_file.name
    temp_file.close()
    
    p = None
    
    try:
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(
            format=sample_format,
            channels=channels,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk
        )
        
        # Record data
        frames = []
        for i in range(0, int(sample_rate / chunk * duration)):
            data = stream.read(chunk)
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
        print(f"Error recording voice command: {str(e)}")
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        return None, None
        
    finally:
        if p:
            p.terminate()


def transcribe_voice_command(audio_file_path: str) -> str:
    """
    Transcribe a voice command from an audio file
    
    Args:
        audio_file_path: Path to the audio file to transcribe
        
    Returns:
        Transcribed text or empty string on error
    """
    if not os.path.exists(audio_file_path):
        return ""
        
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_file_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data)
            return text.lower()
    except Exception as e:
        print(f"Error transcribing voice command: {str(e)}")
        return ""


def get_voice_help_text() -> str:
    """
    Get help text for available voice commands
    
    Returns:
        Formatted help text for voice commands
    """
    help_text = """
    # Voice Command Reference

    ## Navigation Commands
    - "New chat" - Start a new conversation
    - "Clear chat" - Clear the current conversation
    - "Logout" - Log out of the application

    ## Model Selection
    - "Use Gemini" - Switch to Gemini model
    - "Switch to Claude" - Switch to Claude model
    - "Use GPT" or "Use OpenAI" - Switch to OpenAI GPT model

    ## Settings
    - "Increase temperature" or "More creative" - Make responses more creative
    - "Decrease temperature" or "More precise" - Make responses more precise

    ## Input Methods
    - "Upload image" - Open image upload tab
    - "Record audio" - Open audio recording tab
    - "Upload file" or "Upload document" - Open file upload tab

    ## Message Control
    - "Send message" - Send the current message
    - "Dictate [your message]" - Dictate a message and send it

    ## Voice Command Control
    - "Stop listening" or "Pause voice commands" - Disable voice commands
    - "Start listening" or "Resume voice commands" - Enable voice commands
    - "Help" or "What can I say" - Show this help reference
    """
    return help_text
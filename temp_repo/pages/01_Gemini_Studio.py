"""
Gemini Studio - Advanced multimodal interactions with Gemini models

This page provides an enhanced interface for interacting with the latest Gemini models,
including Gemini 2.0 Pro. It supports:
- Real-time streaming responses
- Multimodal inputs (text, images, audio)
- Webcam integration
- Screen sharing
- Two-way conversation
"""

import streamlit as st
import os
import base64
import json
import time
import datetime
from io import BytesIO
from PIL import Image
import tempfile

# Import Gemini-specific utilities
from utils.gemini_api import (
    initialize_gemini, 
    get_gemini_models,
    get_gemini_response,
    get_gemini_streaming_response
)

# Import database utilities for conversation storage
from utils.database import (
    init_db, 
    save_conversation, 
    load_conversations, 
    get_most_recent_chat
)

# Auth utilities
from utils.google_auth import check_login, get_current_user

# Audio utilities 
from utils.webrtc_audio import audio_recorder_ui

# Apply the same theme as the main app
from utils.themes import apply_theme

# Set page title and icon
st.set_page_config(
    page_title="Gemini Studio - AI Chat Studio",
    page_icon="🧠",
    layout="wide"
)

# Apply theme 
theme_css = apply_theme(st.session_state.get("current_theme", "Amazon Q Purple"))
st.markdown(theme_css, unsafe_allow_html=True)

# Check user login
check_login()

# Initialize session state for this page
if "gemini_messages" not in st.session_state:
    st.session_state.gemini_messages = []
if "gemini_current_model" not in st.session_state:
    st.session_state.gemini_current_model = "gemini-1.5-pro"
if "gemini_temperature" not in st.session_state:
    st.session_state.gemini_temperature = 0.7
if "gemini_streaming" not in st.session_state:
    st.session_state.gemini_streaming = True
if "gemini_chat_id" not in st.session_state:
    st.session_state.gemini_chat_id = None
if "gemini_uploaded_image" not in st.session_state:
    st.session_state.gemini_uploaded_image = None
if "gemini_webcam_image" not in st.session_state:
    st.session_state.gemini_webcam_image = None
if "gemini_audio_data" not in st.session_state:
    st.session_state.gemini_audio_data = None
if "gemini_screen_share" not in st.session_state:
    st.session_state.gemini_screen_share = None
if "gemini_message_cooldown" not in st.session_state:
    st.session_state.gemini_message_cooldown = False

# Initialize the database
init_db()

# Initialize Gemini API
gemini_initialized = initialize_gemini()

def encode_image(uploaded_file):
    """Encode an uploaded file to base64 string"""
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        encoded = base64.b64encode(bytes_data).decode('utf-8')
        return encoded
    return None

def clear_multimodal_inputs():
    """Clear all multimodal inputs"""
    st.session_state.gemini_uploaded_image = None
    st.session_state.gemini_webcam_image = None
    st.session_state.gemini_audio_data = None
    st.session_state.gemini_screen_share = None

def load_or_initialize_conversation():
    """Load recent conversation or initialize a new one"""
    username = get_current_user()
    if not username:
        return
        
    # Load most recent conversation for this model
    chat_id, messages = get_most_recent_chat(
        username=username,
        model=st.session_state.gemini_current_model
    )
    
    if chat_id and messages:
        st.session_state.gemini_messages = messages
        st.session_state.gemini_chat_id = chat_id
    else:
        # Initialize new conversation
        st.session_state.gemini_messages = []
        st.session_state.gemini_chat_id = None

def save_current_conversation():
    """Save the current conversation to the database"""
    username = get_current_user()
    if not username:
        return
        
    # Save conversation with the current model
    save_conversation(
        username=username,
        model=st.session_state.gemini_current_model,
        messages=st.session_state.gemini_messages
    )

def main():
    """Main function for the Gemini Studio page"""
    
    # Display header
    st.markdown(f"""
    <div style="text-align: center; padding: 20px 0;">
        <h1 style="font-size: 2.2rem; margin-bottom: 5px;">Gemini Studio</h1>
        <p style="color: #888; font-size: 1.1rem;">Advanced multimodal interactions with Google's Gemini models</p>
        <div style="max-width: 600px; margin: 10px auto; padding: 8px; background-color: #0f0f0f; border-radius: 8px; border: 1px solid #333;">
            <p style="margin: 0; color: #4285f4;">
                <strong>Model:</strong> <span id="current-model">{st.session_state.gemini_current_model}</span>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if Gemini API is initialized
    if not gemini_initialized:
        st.error("Gemini API not initialized. Please check your API key.")
        
        # Add API key input option
        with st.expander("Set Gemini API Key"):
            api_key = st.text_input("Enter your Gemini API Key", type="password")
            if st.button("Save API Key"):
                if api_key:
                    # In a real implementation, this would securely store the API key
                    # For demonstration, we'll just set it in the environment
                    os.environ["GEMINI_API_KEY"] = api_key
                    st.success("API Key saved! Please refresh the page.")
                    time.sleep(2)
                    st.experimental_rerun()
                else:
                    st.warning("Please enter a valid API key")
        
        st.warning("You need to set up the Gemini API key to use this feature.")
        st.info("You can get a Gemini API key from https://ai.google.dev/")
        return
    
    # Create a two-column layout: Chat area and sidebar
    col1, col2 = st.columns([4, 1])
    
    # Sidebar (col2) - Configuration options
    with col2:
        st.sidebar.title("Gemini Settings")
        
        # Model selection
        st.sidebar.subheader("Model")
        model_options = [
            "gemini-1.5-pro", 
            "gemini-1.5-flash", 
            "gemini-2.0-pro",
            "gemini-2.0-pro-vision",
            "gemini-2.0-flash"
        ]
        
        selected_model = st.sidebar.selectbox(
            "Select Gemini Model", 
            options=model_options,
            index=model_options.index(st.session_state.gemini_current_model)
            if st.session_state.gemini_current_model in model_options else 0
        )
        
        # Update the model in session state if changed
        if selected_model != st.session_state.gemini_current_model:
            st.session_state.gemini_current_model = selected_model
            # Load conversation for the new model
            load_or_initialize_conversation()
            st.sidebar.success(f"Loaded conversations for {selected_model}")
        
        # Temperature slider
        st.sidebar.subheader("Generation Settings")
        temperature = st.sidebar.slider(
            "Temperature", 
            min_value=0.0, 
            max_value=1.0, 
            value=st.session_state.gemini_temperature,
            step=0.1,
            help="Higher values make output more random, lower values more focused"
        )
        
        # Update temperature if changed
        if temperature != st.session_state.gemini_temperature:
            st.session_state.gemini_temperature = temperature
        
        # Streaming toggle
        streaming = st.sidebar.checkbox(
            "Enable streaming responses", 
            value=st.session_state.gemini_streaming,
            help="Show AI responses as they are generated"
        )
        
        # Update streaming setting if changed
        if streaming != st.session_state.gemini_streaming:
            st.session_state.gemini_streaming = streaming
        
        # Conversation management section
        st.sidebar.subheader("Conversation")
        
        # New conversation button
        if st.sidebar.button("Start New Conversation", use_container_width=True):
            st.session_state.gemini_messages = []
            st.session_state.gemini_chat_id = None
            clear_multimodal_inputs()
            st.sidebar.success("Started new conversation")
            st.experimental_rerun()
            
    # Main chat area (col1)
    with col1:
        # Custom CSS for chat styling
        st.markdown("""
        <style>
        .chat-container {
            height: 500px !important;
            overflow-y: auto;
            padding-right: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
            background-color: rgba(40, 40, 40, 0.2);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create a taller fixed-height container for chat messages
        chat_container = st.container(height=500, border=False)
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display chat messages
        with chat_container:
            for i, message in enumerate(st.session_state.gemini_messages):
                is_user = message["role"] == "user"
                
                # Create message container with avatar
                avatar_color = "#f50057" if is_user else "#8c52ff"
                avatar_icon = "👤" if is_user else "🤖"
                bg_color = "#1e1e1e" if is_user else "#272727"
                
                # Handle text content
                if isinstance(message["content"], str):
                    message_content = message["content"]
                    st.markdown(f"""
                    <div style="display: flex; align-items: start; margin-bottom: 10px;">
                        <div style="background-color: {avatar_color}; color: white; border-radius: 50%; height: 32px; width: 32px; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0;">
                            <span>{avatar_icon}</span>
                        </div>
                        <div style="background-color: {bg_color}; border-radius: 10px; padding: 10px; max-width: 90%;">
                            <p style="margin: 0; color: white; white-space: pre-wrap;">{message_content.replace(chr(10), '<br>')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # Handle multimodal content
                elif isinstance(message["content"], list):
                    # First render the text part
                    text_parts = [part for part in message["content"] if isinstance(part, str)]
                    text_content = "\n".join(text_parts) if text_parts else ""
                    
                    st.markdown(f"""
                    <div style="display: flex; align-items: start; margin-bottom: 10px;">
                        <div style="background-color: {avatar_color}; color: white; border-radius: 50%; height: 32px; width: 32px; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0;">
                            <span>{avatar_icon}</span>
                        </div>
                        <div style="background-color: {bg_color}; border-radius: 10px; padding: 10px; max-width: 90%;">
                            <p style="margin: 0; color: white; white-space: pre-wrap;">{text_content.replace(chr(10), '<br>')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Then render any images
                    for part in message["content"]:
                        if isinstance(part, dict) and part.get("type") == "image" and part.get("data"):
                            try:
                                image_data = base64.b64decode(part["data"])
                                image = Image.open(BytesIO(image_data))
                                st.image(image, caption="Uploaded Image", width=300)
                            except Exception as e:
                                st.error(f"Could not display image: {str(e)}")
                        
                        elif isinstance(part, dict) and part.get("type") == "audio" and part.get("data"):
                            try:
                                audio_data = base64.b64decode(part["data"])
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                                    tmp.write(audio_data)
                                    tmp_path = tmp.name
                                st.audio(tmp_path)
                            except Exception as e:
                                st.error(f"Could not play audio: {str(e)}")
        
        # Close the chat container
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Multimodal input options
        input_tabs = st.tabs(["Image Upload", "Webcam", "Audio Recording", "Screen Share"])
        
        # Image upload tab
        with input_tabs[0]:
            uploaded_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
            if uploaded_file:
                # Save the uploaded image to session state
                st.session_state.gemini_uploaded_image = encode_image(uploaded_file)
                
                # Preview the image
                st.image(uploaded_file, caption="Image ready for analysis", width=300)
                
                # Show removal button
                if st.button("Remove uploaded image"):
                    st.session_state.gemini_uploaded_image = None
                    st.experimental_rerun()
        
        # Webcam tab
        with input_tabs[1]:
            st.markdown("### Webcam Capture")
            st.markdown("Take a photo with your webcam to include in the conversation")
            
            webcam_image = st.camera_input("Take a photo")
            if webcam_image:
                # Save webcam image to session state
                st.session_state.gemini_webcam_image = encode_image(webcam_image)
                
                # Show removal button
                if st.button("Remove webcam image"):
                    st.session_state.gemini_webcam_image = None
                    st.experimental_rerun()
        
        # Audio recording tab
        with input_tabs[2]:
            st.markdown("### Audio Recording")
            st.markdown("Record audio to include in the conversation")
            
            # Use WebRTC audio recorder
            base64_audio = audio_recorder_ui(
                key="gemini_webrtc_recorder",
                title="Record Audio",
                description="Click start to begin recording. Click stop when done.",
                durations=[15, 30, 60, 120],
                show_description=True,
                show_playback=True
            )
            
            if base64_audio:
                st.session_state.gemini_audio_data = base64_audio
                st.session_state.gemini_audio_path = st.session_state.get("gemini_webrtc_recorder_file_path")
                
                st.success("Audio recorded successfully!")
                st.info("You can now send a message to analyze this audio.")
                
                # Show removal button
                if st.button("Remove recorded audio"):
                    st.session_state.gemini_audio_data = None
                    st.session_state.gemini_audio_path = None
                    st.experimental_rerun()
        
        # Screen share tab
        with input_tabs[3]:
            st.markdown("### Screen Share")
            st.markdown("Currently, screen sharing requires manual screenshot uploads")
            
            screen_file = st.file_uploader("Upload a screenshot", type=["jpg", "jpeg", "png"], key="screen_upload")
            if screen_file:
                # Save screenshot to session state
                st.session_state.gemini_screen_share = encode_image(screen_file)
                
                # Preview the screenshot
                st.image(screen_file, caption="Screenshot ready for analysis", width=300)
                
                # Show removal button
                if st.button("Remove screenshot"):
                    st.session_state.gemini_screen_share = None
                    st.experimental_rerun()
            
            # Note about screen sharing
            st.info("Note: Native screen sharing capabilities will be added in a future update")
        
        # Text input area
        st.markdown("### Message Input")
        
        # Get multimodal status
        has_image = st.session_state.gemini_uploaded_image is not None or st.session_state.gemini_webcam_image is not None
        has_audio = st.session_state.gemini_audio_data is not None
        has_screen = st.session_state.gemini_screen_share is not None
        
        # Show active multimodal inputs
        if has_image or has_audio or has_screen:
            status_items = []
            if has_image:
                status_items.append("📷 Image")
            if has_audio:
                status_items.append("🎤 Audio")
            if has_screen:
                status_items.append("🖥️ Screen")
                
            status_text = ", ".join(status_items)
            st.info(f"Active inputs: {status_text}")
            
            # Add a button to clear all multimodal inputs
            if st.button("Clear all inputs"):
                clear_multimodal_inputs()
                st.experimental_rerun()
        
        # Message input
        user_input = st.text_area("Type your message here", height=100, max_chars=1000)
        
        # Send button
        if st.button("Send", use_container_width=True, type="primary"):
            if st.session_state.gemini_message_cooldown:
                st.warning("Message already sent! Please wait a moment...")
                return
                
            # Set cooldown
            st.session_state.gemini_message_cooldown = True
            
            # Check if there's any input (text or multimodal)
            if not user_input and not has_image and not has_audio and not has_screen:
                st.warning("Please enter a message or add an image/audio input")
                st.session_state.gemini_message_cooldown = False
                return
            
            # Create message content
            message_content = []
            
            # Add text content if provided
            if user_input:
                message_content.append(user_input)
            
            # Add image if provided
            if has_image:
                image_data = st.session_state.gemini_uploaded_image or st.session_state.gemini_webcam_image
                message_content.append({
                    "type": "image",
                    "data": image_data
                })
            
            # Add audio if provided
            if has_audio:
                message_content.append({
                    "type": "audio",
                    "data": st.session_state.gemini_audio_data
                })
            
            # Add screen share if provided
            if has_screen:
                message_content.append({
                    "type": "image",
                    "data": st.session_state.gemini_screen_share
                })
            
            # Create user message - use the first text part as content if multimodal
            if len(message_content) == 1 and isinstance(message_content[0], str):
                # Simple text message
                user_message = {"role": "user", "content": message_content[0]}
            else:
                # Multimodal message
                user_message = {"role": "user", "content": message_content}
            
            # Add message to history
            st.session_state.gemini_messages.append(user_message)
            
            # Clear multimodal inputs after sending
            clear_multimodal_inputs()
            
            # Display "AI is thinking" message
            with st.spinner(f"Gemini is thinking... using {st.session_state.gemini_current_model}"):
                try:
                    # Extract multimodal content
                    image_data = None
                    audio_data = None
                    
                    if isinstance(user_message["content"], list):
                        for part in user_message["content"]:
                            if isinstance(part, dict):
                                if part.get("type") == "image":
                                    image_data = part.get("data")
                                elif part.get("type") == "audio":
                                    audio_data = part.get("data")
                    
                    # Use input text or empty string if content is multimodal
                    user_text = user_input or "Analyze this"
                    
                    if st.session_state.gemini_streaming:
                        # Create a placeholder for streaming output
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        # Get streaming response
                        for chunk in get_gemini_streaming_response(
                            prompt=user_text,
                            conversation_history=st.session_state.gemini_messages,
                            image_data=image_data,
                            audio_data=audio_data,
                            temperature=st.session_state.gemini_temperature,
                            model_name=st.session_state.gemini_current_model
                        ):
                            # Update response with new chunk
                            full_response += chunk
                            # Display the updated response with blinking cursor
                            response_placeholder.markdown(f"{full_response}▌")
                            time.sleep(0.01)  # Small delay for smooth animation
                        
                        # Add AI response to messages
                        st.session_state.gemini_messages.append({
                            "role": "assistant", 
                            "content": full_response
                        })
                        
                        # Remove the placeholder
                        response_placeholder.empty()
                    else:
                        # Get complete response (non-streaming)
                        ai_response = get_gemini_response(
                            prompt=user_text,
                            conversation_history=st.session_state.gemini_messages,
                            image_data=image_data,
                            audio_data=audio_data,
                            temperature=st.session_state.gemini_temperature,
                            model_name=st.session_state.gemini_current_model
                        )
                        
                        # Add AI response to messages
                        st.session_state.gemini_messages.append({
                            "role": "assistant", 
                            "content": ai_response
                        })
                        
                    # Save conversation to database
                    save_current_conversation()
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
                finally:
                    # Reset cooldown
                    st.session_state.gemini_message_cooldown = False
            
            # Rerun to update UI
            st.experimental_rerun()

# Call main function
if __name__ == "__main__":
    main()
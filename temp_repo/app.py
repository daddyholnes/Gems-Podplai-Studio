import streamlit as st
import os
import datetime
import json
import base64
import tempfile
import threading
import html
from io import BytesIO
from PIL import Image
from utils.ui_components import render_voice_command_ui, render_floating_voice_button
from utils.themes import apply_theme, THEMES
# Emoji picker removed to fix chat functionality
from utils.models import (
    get_gemini_response,
    get_vertex_ai_response,
    get_openai_response,
    get_anthropic_response,
    get_perplexity_response
)
# Use Google OAuth for secure authentication
from utils.google_auth import check_login, logout_user, get_current_user, is_admin
from utils.database import init_db, save_conversation, load_conversations, get_most_recent_chat
# Enhanced audio recording with WebRTC
from utils.webrtc_audio import audio_recorder_ui
# Text-to-speech with ElevenLabs
from utils.tts import render_tts_controls, render_play_button, text_to_speech

# Add CSS for toggle buttons
def add_toggle_button_css():
    st.markdown("""
    <style>
    .toggle-button {
        position: relative;
        width: 40px;
        height: 20px;
        background-color: #333;
        border-radius: 10px;
        cursor: pointer;
    }
    
    .toggle-button:before {
        content: '';
        position: absolute;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        top: 1px;
        left: 1px;
        background-color: #555;
        transition: 0.2s;
    }
    
    .toggle-button.active {
        background-color: #4285f4;
    }
    
    .toggle-button.active:before {
        transform: translateX(20px);
        background-color: white;
    }
    
    /* Make buttons look like actual buttons */
    button {
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)

# Set page configuration
st.set_page_config(
    page_title="AI Chat Studio",
    page_icon="assets/favicon.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user" not in st.session_state:
    st.session_state.user = None
if "current_model" not in st.session_state:
    st.session_state.current_model = "Gemini"
if "voice_commands_enabled" not in st.session_state:
    st.session_state.voice_commands_enabled = False
if "voice_commands_active" not in st.session_state:
    st.session_state.voice_commands_active = False
if "temperature" not in st.session_state:
    st.session_state.temperature = 0.7
if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None
    
# Voice command state variables
if "voice_commands_active" not in st.session_state:
    st.session_state.voice_commands_active = False
if "voice_processor" not in st.session_state:
    st.session_state.voice_processor = None
if "is_listening" not in st.session_state:
    st.session_state.is_listening = False
    
# Theme state - initialize before use
if "current_theme" not in st.session_state:
    st.session_state.current_theme = "Amazon Q Purple"
    
# Message cooldown to prevent double-sending
if "message_cooldown" not in st.session_state:
    st.session_state.message_cooldown = False

# Apply the current theme's CSS
theme_css = apply_theme(st.session_state.current_theme)
st.markdown(theme_css, unsafe_allow_html=True)

# Check user login
check_login()

# Helper function to encode image for API calls
def encode_image(uploaded_file):
    if uploaded_file is not None:
        # Read the file and encode it
        bytes_data = uploaded_file.getvalue()
        
        # Convert to base64
        encoded = base64.b64encode(bytes_data).decode('utf-8')
        return encoded
    return None

# Main function
def main():
    # Initialize database
    init_db()
    
    # Add CSS for toggle buttons and UI elements
    add_toggle_button_css()
    
    # Apply custom styling to match Google Gemini UI exactly
    st.markdown("""
    <style>
    /* Dark background for the app */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Left sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0e1117;
        border-right: 1px solid #333;
    }
    
    /* Hide default Streamlit hamburger menu */
    section[data-testid="stSidebarUserContent"] {
        padding-top: 0rem;
    }
    
    /* Make the main content full width */
    .main .block-container {
        max-width: 100%;
        padding-top: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Right sidebar styling */
    .right-sidebar {
        position: fixed;
        right: 0;
        top: 0;
        width: 250px;
        height: 100vh;
        padding: 1rem;
        background-color: #0e1117;
        border-left: 1px solid #333;
        overflow-y: auto;
        z-index: 10;
    }
    
    /* Main content area with space for the right sidebar */
    .main-content {
        margin-right: 250px;
    }
    
    /* Toggle button styling */
    .toggle-container {
        margin-top: 5px;
    }
    .toggle-button {
        background-color: #333;
        border-radius: 15px;
        display: inline-block;
        height: 20px;
        position: relative;
        width: 40px;
    }
    .toggle-button.active {
        background-color: #4285f4;
    }
    .toggle-button::after {
        background-color: white;
        border-radius: 50%;
        content: '';
        height: 16px;
        left: 2px;
        position: absolute;
        top: 2px;
        transition: all 0.3s;
        width: 16px;
    }
    .toggle-button.active::after {
        left: 22px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Left sidebar matching the Google Gemini interface
    with st.sidebar:
        # App section heading with icon
        st.markdown("""
        <div style="padding: 10px 0; cursor: pointer; display: flex; align-items: center;">
            <div style="background-color: #4285f4; border-radius: 50%; height: 28px; width: 28px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                <span style="color: white; font-size: 16px;">G</span>
            </div>
            <span style="color: white; font-weight: 500; font-size: 16px;">AI Chat Studio</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Chat Library section
        st.markdown("""
        <div style="margin-top: 20px; margin-bottom: 10px;">
            <span style="color: #888; font-size: 14px; font-weight: 500;">CHAT LIBRARY</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Search input
        search_text = st.text_input("Search chats", key="search_chats", placeholder="Search for past prompts")
        
        # Display message if no chats are found
        st.markdown("""
        <div style="color: #888; font-size: 12px; padding: 5px 0;">
            No previous conversations found
        </div>
        """, unsafe_allow_html=True)
        
        # Horizontal separator
        st.markdown("<hr style='margin: 20px 0; border-color: #333;'>", unsafe_allow_html=True)
        
        # Capabilities section
        st.markdown("""
        <div style="margin-bottom: 10px;">
            <span style="color: #888; font-size: 14px; font-weight: 500;">CAPABILITIES</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Capabilities list
        st.markdown("""
        <div style="padding: 5px 0;">
            <span style="color: white;">📝 Text & Code</span>
        </div>
        <div style="padding: 5px 0;">
            <span style="color: white;">🖼️ Images</span>
        </div>
        <div style="padding: 5px 0;">
            <span style="color: white;">🔊 Audio</span>
        </div>
        """, unsafe_allow_html=True)
        
        # File upload area above logout button
        st.markdown("""
        <div style="margin-top: 30px; margin-bottom: 20px;">
            <div style="color: white; font-weight: 500; margin-bottom: 15px; font-size: 16px;">Upload files</div>
            <div style="border: 1px dashed #666; border-radius: 8px; padding: 20px; text-align: center; background-color: rgba(30, 30, 30, 0.6);">
                <div style="color: white; margin-bottom: 10px;">Drag and drop file here</div>
                <div style="color: #999; font-size: 12px; margin-bottom: 5px;">Limit 200MB per file •</div>
                <div style="color: #999; font-size: 12px;">JPG, JPEG, PNG</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Browse files button
        browse_col1, browse_col2 = st.columns([3, 1])
        with browse_col1:
            browse_files = st.file_uploader("Browse files", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="sidebar_file_uploader")
            if browse_files:
                # Preview the uploaded files
                st.image(browse_files, width=150)
                st.session_state.uploaded_image = encode_image(browse_files)
                
        with browse_col2:
            st.markdown("""
            <div style="height: 38px;"></div>
            """, unsafe_allow_html=True)
        
        # Recent files section
        st.markdown("""
        <div style="margin-top: 20px; margin-bottom: 20px;">
            <div style="color: white; font-weight: 500; margin-bottom: 10px; font-size: 16px;">Recent files</div>
            <div style="color: #999; font-size: 14px; text-align: center; padding: 15px 0;">No recent files found</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Logout button at bottom
        st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True, type="primary", key="logout_bottom"):
            logout_user()
            st.rerun()
    
    # Right sidebar for tools panel exactly as in Google Gemini
    right_col = st.container()
    
    # Create a column layout - left sidebar, main content and right sidebar
    # Create a 3-column layout with more space for the left sidebar
    left_sidebar, main_content, right_sidebar = st.columns([1.2, 5.8, 2])
    
    # Left sidebar with content
    with left_sidebar:
        # Display active model with badge
        st.markdown("""
        <div style="background-color: rgba(30, 30, 30, 0.6); border-radius: 8px; padding: 12px; margin-bottom: 20px; border: 1px solid #333;">
            <div style="display: flex; align-items: center;">
                <div style="background-color: #4285f4; border-radius: 50%; height: 24px; width: 24px; display: flex; align-items: center; justify-content: center; margin-right: 10px;">
                    <span style="color: white; font-size: 14px;">G</span>
                </div>
                <div>
                    <div style="color: white; font-weight: 500; font-size: 14px;">Gemini 2.0 Pro</div>
                    <div style="color: #888; font-size: 12px;">Premium model</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main content area with chat UI
    with main_content:
        # Main chat area with exactly the header shown in the screenshot
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="font-size: 2.2rem; margin-bottom: 5px; color: white;">Talk with AI live</h1>
            <p style="color: #888; font-size: 1.1rem;">Interact with AI models using text, code, images, audio, or upload files</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Persona selector dropdown across the width
        st.markdown("""
        <div style="margin-bottom: 20px;">
            <div style="background-color: rgba(30, 30, 30, 0.6); border: 1px solid #333; border-radius: 8px; padding: 10px; margin-bottom: 15px;">
                <p style="color: white; margin-bottom: 5px; font-weight: 500;">Select Persona</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Create a dropdown for persona selection
        personas = [
            "Default Assistant", 
            "Creative Writer", 
            "Data Scientist", 
            "Code Expert", 
            "Language Tutor",
            "Math Tutor"
        ]
        
        selected_persona = st.selectbox(
            "Choose a persona for the AI",
            personas,
            index=0,
            key="persona_selector",
            label_visibility="collapsed"
        )
        
        # Model display box exactly as shown in the screenshot
        st.markdown("""
        <div style="max-width: 600px; margin: 15px auto; padding: 10px; background-color: rgba(20, 20, 20, 0.6); border-radius: 8px; border: 1px solid #333;">
            <p style="margin: 0; color: #4285f4; text-align: center;">
                <span style="color: #4285f4; font-weight: normal;">Model:</span> <span style="color: #4285f4;">Gemini 2.0 Pro (gemini-1.5-pro)</span>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Add custom CSS for improved message container
        st.markdown("""
        <style>
        .chat-container {
            height: 600px !important;
            overflow-y: auto;
            padding-right: 15px;
            margin-bottom: 20px;
            border-radius: 10px;
            background-color: rgba(40, 40, 40, 0.2);
        }
        .stChatInputContainer {
            min-height: 80px !important;
            padding: 10px !important;
            margin-top: 15px !important;
        }
        .stChatInput {
            min-height: 60px !important;
            font-size: 16px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create a taller fixed-height container for chat messages with Google AI Studio style
        chat_container = st.container(height=600, border=False)
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display chat messages in a clean Google AI Studio style within the fixed container
        with chat_container:
            for i, message in enumerate(st.session_state.messages):
                # Custom styling for messages based on role
                if message["role"] == "user":
                    # User message with custom styling
                    st.markdown(f"""
                    <div style="display: flex; align-items: start; margin-bottom: 10px;">
                        <div style="background-color: #f50057; color: white; border-radius: 50%; height: 32px; width: 32px; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0;">
                            <span>👤</span>
                        </div>
                        <div style="background-color: #1e1e1e; border-radius: 10px; padding: 10px; max-width: 90%;">
                            <p style="margin: 0; color: white; white-space: pre-wrap;">{html.escape(message["content"]).replace(chr(10), '<br>')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                # If there's an image in the message
                if message.get("image"):
                    try:
                        # Display the image below the text
                        image_data = base64.b64decode(message["image"])
                        image = Image.open(BytesIO(image_data))
                        st.image(image, caption="Uploaded Image", width=300)
                    except Exception as e:
                        st.error(f"Could not display image: {str(e)}")
                else:
                    # AI message with custom styling
                    st.markdown(f"""
                    <div style="display: flex; align-items: start; margin-bottom: 10px;">
                        <div style="background-color: #8c52ff; color: white; border-radius: 50%; height: 32px; width: 32px; display: flex; align-items: center; justify-content: center; margin-right: 10px; flex-shrink: 0;">
                            <span>🤖</span>
                        </div>
                        <div style="background-color: #272727; border-radius: 10px; padding: 10px; max-width: 90%;">
                            <p style="margin: 0; color: white; white-space: pre-wrap;">{html.escape(message["content"]).replace(chr(10), '<br>')}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Add text-to-speech and reaction buttons for AI messages
                    if i > 0 and message["role"] == "assistant":
                        # Create a unique key for each message's reaction section
                        message_key = f"reaction_{i}"
                        
                        # Initialize reaction counts in session state if not already set
                        if message_key not in st.session_state:
                            st.session_state[message_key] = {"👍": 0, "❤️": 0, "😂": 0, "😮": 0, "🔥": 0}
                        
                        # Display the reactions as small text instead of buttons
                        reaction_html = ""
                        reactions = ["👍", "❤️", "😂", "😮", "🔥"]
                        
                        for emoji in reactions:
                            count = st.session_state[message_key][emoji]
                            reaction_html += f"<span style='margin-right:8px;font-size:15px;'>{emoji} {count if count > 0 else ''}</span>"
                        
                        # Show them in a clean HTML layout
                        st.markdown(f"""
                        <div style="margin-top:5px;margin-bottom:10px;margin-left:40px;">
                            {reaction_html}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Add buttons row: Play (TTS), Copy, and React
                        tts_col, react_col, copy_col = st.columns([1, 1, 2])
                        
                        # Text-to-speech button
                        with tts_col:
                            # Use the render_play_button from utils/tts.py
                            render_play_button(message["content"], key=f"tts_{i}")
                        
                        # React button
                        if react_col.button("👍 React", key=f"react_btn_{i}", use_container_width=True):
                            st.session_state[message_key]["👍"] += 1
                            
                        # Copy text button
                        if copy_col.button("📋 Copy Text", key=f"copy_btn_{i}", use_container_width=True):
                            # Use JavaScript to copy to clipboard via streamlit component
                            st.markdown(f"""
                            <script>
                                var textToCopy = {json.dumps(message["content"])};
                                navigator.clipboard.writeText(textToCopy);
                            </script>
                            """, unsafe_allow_html=True)
                            st.toast("Text copied to clipboard!")
                            
        
        # Close the chat container div
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Add chat input with ghosted icons inside
        chat_input_container = st.container()
        with chat_input_container:
            st.markdown("""
            <style>
            /* Style for the chat input container with icons */
            .chat-input-with-icons {
                position: relative;
                width: 100%;
                margin-top: 20px;
            }
            
            /* Icon container at the right side of the input */
            .chat-icons {
                position: absolute;
                right: 15px;
                top: 50%;
                transform: translateY(-50%);
                display: flex;
                gap: 12px;
                z-index: 100;
            }
            
            /* Individual icon styling */
            .chat-icon {
                opacity: 0.6;
                cursor: pointer;
                transition: opacity 0.2s;
                width: 20px;
                height: 20px;
            }
            
            .chat-icon:hover {
                opacity: 1;
            }
            </style>
            
            <div class="chat-input-with-icons">
                <div class="chat-icons">
                    <svg class="chat-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#888">
                        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6z"/>
                    </svg>
                    <svg class="chat-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#888">
                        <path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/>
                    </svg>
                    <svg class="chat-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#888">
                        <path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/>
                    </svg>
                    <svg class="chat-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="#888">
                        <path d="M9.4 10.5l4.77-8.26C13.47 2.09 12.75 2 12 2c-2.4 0-4.6.85-6.32 2.25l3.66 6.35.06-.1zM21.54 9c-.92-2.92-3.15-5.26-6-6.34L11.88 9h9.66zm.26 1h-7.49l.29.5 4.76 8.25C21 16.97 22 14.61 22 12c0-.69-.07-1.35-.2-2z"/>
                    </svg>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Add the actual chat input (will appear with icons overlaid)
            if user_input := st.chat_input("Message the AI...", key="chat_input_main"):
                # Check if we're in a cooldown period (prevents double messages)
                if st.session_state.message_cooldown:
                    st.info("Message already sent! Please wait a moment...")
                    return
                    
                # Set cooldown to prevent double sending
                st.session_state.message_cooldown = True
                    
                # If document was uploaded and button clicked, use document text as message
                if hasattr(st.session_state, 'document_text'):
                    user_input = st.session_state.document_text
                    # Clear it after use
                    delattr(st.session_state, 'document_text')
                
                # Create message object
                user_message = {"role": "user", "content": user_input}
                
                # Add image to message if one is uploaded
                if st.session_state.uploaded_image:
                    user_message["image"] = st.session_state.uploaded_image
                    
                # Add audio to message if recorded
                if hasattr(st.session_state, 'audio_data') and st.session_state.audio_data:
                    user_message["audio"] = st.session_state.audio_data
                    # Clear audio data after use
                    st.session_state.audio_data = None
                    st.session_state.audio_path = None
                
                # Add user message to chat
                st.session_state.messages.append(user_message)
                
                # Get AI response based on selected model
                with st.spinner(f"Thinking... using {st.session_state.current_model}"):
                    try:
                        image_data = user_message.get("image")
                        model_name = st.session_state.current_model.lower()
                        
                        # Extract model call sign from selected model if available
                        model_call_sign = None
                        if "(" in st.session_state.current_model and ")" in st.session_state.current_model:
                            model_call_sign = st.session_state.current_model.split("(")[1].split(")")[0]
                        
                        # Gemini models
                        if "gemini" in model_name:
                            # Use extracted call sign or fallback to default
                            gemini_version = model_call_sign if model_call_sign else "gemini-1.5-pro"
                            
                            # Get audio data if available
                            audio_data = user_message.get("audio")
                            
                            ai_response = get_gemini_response(
                                user_input, 
                                st.session_state.messages,
                                image_data=image_data,
                                audio_data=audio_data,
                                temperature=st.session_state.temperature,
                                model_name=gemini_version
                            )
                        
                        # Vertex AI models - direct routing to appropriate API based on model
                        elif "vertex ai" in model_name:
                            if "claude" in model_name.lower():
                                # Use the extracted call sign or default to Claude 3.5
                                claude_model = model_call_sign if model_call_sign else "claude-3-5-sonnet-20241022"
                                ai_response = get_vertex_ai_response(
                                    user_input, 
                                    st.session_state.messages,
                                    model_name=claude_model,
                                    image_data=image_data,
                                    temperature=st.session_state.temperature
                                )
                            else:
                                # Default Vertex AI model
                                ai_response = get_vertex_ai_response(
                                    user_input, 
                                    st.session_state.messages,
                                    image_data=image_data,
                                    temperature=st.session_state.temperature
                                )
                        
                        # OpenAI models
                        elif "openai" in model_name or "gpt" in model_name:
                            # Use extracted call sign or fallback to default
                            gpt_version = model_call_sign if model_call_sign else "gpt-4o"
                            
                            ai_response = get_openai_response(
                                user_input, 
                                st.session_state.messages,
                                model_name=gpt_version,
                                image_data=image_data,
                                temperature=st.session_state.temperature
                            )
                        
                        # Anthropic models
                        elif "anthropic" in model_name or "claude" in model_name:
                            # Use extracted call sign or fallback to default
                            claude_version = model_call_sign if model_call_sign else "claude-3-5-sonnet-20241022"
                            
                            ai_response = get_anthropic_response(
                                user_input, 
                                st.session_state.messages,
                                model_name=claude_version,
                                image_data=image_data,
                                temperature=st.session_state.temperature
                            )
                        
                        # Perplexity models
                        elif "perplexity" in model_name:
                            # Use extracted call sign or fallback to default
                            pplx_version = model_call_sign if model_call_sign else "mistral-8x7b-instruct"
                            
                            ai_response = get_perplexity_response(
                                user_input, 
                                st.session_state.messages,
                                model_name=pplx_version,
                                temperature=st.session_state.temperature
                            )
                        
                        # Default to Gemini if model not recognized
                        else:
                            ai_response = get_gemini_response(
                                user_input, 
                                st.session_state.messages, 
                                image_data=image_data,
                                temperature=st.session_state.temperature
                            )
                        
                        # Add AI response to messages
                        st.session_state.messages.append({"role": "assistant", "content": ai_response})
                        
                        # Save the conversation to database for persistence
                        save_conversation(
                            username=get_current_user() or "anonymous", 
                            model=st.session_state.current_model,
                            messages=st.session_state.messages
                        )
                        
                        # Clear image after use
                        st.session_state.uploaded_image = None
                        
                    except Exception as e:
                        st.error(f"Error generating response: {str(e)}")
                        
                    # Reset cooldown to allow new messages
                    st.session_state.message_cooldown = False
                    
                # Rerun to update UI
                st.rerun()
    # Right sidebar panel exactly like Google Gemini UI
    with right_sidebar:
        # More compact sidebar with model, tokens, and temperature sections combined
        st.markdown("""
        <style>
        /* Make the right sidebar more compact */
        .compact-sidebar-section {
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #333;
        }
        .compact-sidebar-title {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }
        .compact-sidebar-icon {
            margin-right: 8px;
        }
        .compact-sidebar-content {
            background-color: #1e1e1e;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
        }
        </style>
        
        <div class="compact-sidebar-section">
            <div class="compact-sidebar-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#888" viewBox="0 0 24 24">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
                    <path d="M7 10h10v2H7z"/>
                </svg>
                <span style="margin-left: 8px; color: white; font-weight: 500; font-size: 14px;">Model</span>
            </div>
            <div class="compact-sidebar-content">
                <div style="font-size: 14px; color: white; font-weight: 500;">Gemini 2.0 Pro</div>
                <div style="font-size: 12px; color: #888; margin-top: 3px;">Preview (03-26)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2 & 3. Token count and Temperature in compact format
        st.markdown("""
        <div class="compact-sidebar-section">
            <div class="compact-sidebar-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#888" viewBox="0 0 24 24">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-9 2h2v2h-2V4zM9 8h2v2H9V8zm-4 8h2v2H5v-2zm0-8h2v2H5V8zm0-4h2v2H5V4zm4 12h2v2H9v-2zm4 0h2v2h-2v-2zm0-4h2v2h-2v-2zm0-8h2v2h-2V4zm4 4h2v2h-2V8zm0 8h2v2h-2v-2zm0-4h2v2h-2v-2zm0-8h2v2h-2V4z"/>
                </svg>
                <span style="margin-left: 8px; color: white; font-weight: 500; font-size: 14px;">Token count</span>
            </div>
            <div style="color: #888; font-size: 14px; margin-bottom: 10px;">0 / 1048576</div>
        </div>

        <div class="compact-sidebar-section">
            <div class="compact-sidebar-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#888" viewBox="0 0 24 24">
                    <path d="M15 13V5c0-1.66-1.34-3-3-3S9 3.34 9 5v8c-1.21.91-2 2.37-2 4 0 2.76 2.24 5 5 5s5-2.24 5-5c0-1.63-.79-3.09-2-4zm-4-8c0-.55.45-1 1-1s1 .45 1 1h-2z"/>
                </svg>
                <span style="margin-left: 8px; color: white; font-weight: 500; font-size: 14px;">Temperature</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Temperature slider that matches the design
        temperature = st.slider(
            label="Temperature",
            min_value=0.0, 
            max_value=1.0, 
            value=0.7, 
            step=0.01,
            label_visibility="collapsed",
            key="temperature_sidebar"
        )
        
        if temperature != st.session_state.temperature:
            st.session_state.temperature = temperature
        
        # 4. Tools section in a more compact format
        st.markdown("""
        <div class="compact-sidebar-section">
            <div class="compact-sidebar-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="#888" viewBox="0 0 24 24">
                    <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                </svg>
                <span style="margin-left: 8px; color: white; font-weight: 500; font-size: 14px;">Tools</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Toggle switches for tools - using actual interactable components with compact styling
        # Initialize toggle states if not already set
        for tool in ["structured_output", "code_execution", "function_calling", "grounding"]:
            if f"tool_{tool}" not in st.session_state:
                st.session_state[f"tool_{tool}"] = False
        
        # Create compact tools layout with columns
        st.markdown("""
        <style>
        .tool-toggle {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
            padding: 2px 0;
        }
        .tool-toggle span {
            color: white;
            font-size: 13px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create a 2-column layout for toggles to save vertical space
        col1, col2 = st.columns(2)
        
        # Left column toggles
        with col1:
            # Structured output toggle
            st.markdown("""<div class="tool-toggle">
                <span>Structured output</span>
            </div>""", unsafe_allow_html=True)
            structured_output = st.checkbox("", value=st.session_state.tool_structured_output, key="structured_output_toggle", label_visibility="collapsed")
            if structured_output != st.session_state.tool_structured_output:
                st.session_state.tool_structured_output = structured_output
            
            # Function calling toggle
            st.markdown("""<div class="tool-toggle">
                <span>Function calling</span>
            </div>""", unsafe_allow_html=True)
            function_calling = st.checkbox("", value=st.session_state.tool_function_calling, key="function_calling_toggle", label_visibility="collapsed")
            if function_calling != st.session_state.tool_function_calling:
                st.session_state.tool_function_calling = function_calling
        
        # Right column toggles
        with col2:
            # Code execution toggle
            st.markdown("""<div class="tool-toggle">
                <span>Code execution</span>
            </div>""", unsafe_allow_html=True)
            code_execution = st.checkbox("", value=st.session_state.tool_code_execution, key="code_execution_toggle", label_visibility="collapsed")
            if code_execution != st.session_state.tool_code_execution:
                st.session_state.tool_code_execution = code_execution
            
            # Grounding toggle
            st.markdown("""<div class="tool-toggle">
                <span>Grounding</span>
            </div>""", unsafe_allow_html=True)
            grounding = st.checkbox("", value=st.session_state.tool_grounding, key="grounding_toggle", label_visibility="collapsed")
            if grounding != st.session_state.tool_grounding:
                st.session_state.tool_grounding = grounding
        
        # Close the section
        st.markdown("""</div>""", unsafe_allow_html=True)
        
        # Actions section with real buttons
        st.markdown("""<div style="margin-top: 30px;"></div>""", unsafe_allow_html=True)
        
        # Extension tools section title
        st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 15px; margin-top: 30px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="#888" viewBox="0 0 24 24">
                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
                <path d="M7 12h4v-2H7V7h6v2h-4v2h4v2h-4v2h6v-2h-2z"/>
            </svg>
            <span style="margin-left: 10px; color: white; font-weight: 500;">Extensions</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Feature buttons section with minimal styling
        st.markdown("""
        <div style="margin-bottom: 20px; color: #888; font-size: 12px;">
            Use the icons in the chat input to:
            <ul style="margin-top: 5px; margin-left: 15px;">
                <li>Access files from Google Drive</li>
                <li>Upload documents & images</li>
                <li>Record audio for transcription</li>
                <li>Capture & analyze photos</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
            
        # Hidden input tabs for different input types
        input_tabs = st.tabs(["Image Upload", "Audio Recording", "File Upload"])
        
        # Safety settings link
        st.markdown("""
        <div style="margin-top: 20px; text-align: right;">
            <a href="#" style="color: #888; font-size: 12px; text-decoration: none;">Safety settings</a>
        </div>
        """, unsafe_allow_html=True)
        
        # Image upload tab
        with input_tabs[0]:
            uploaded_file = st.file_uploader("Upload an image for analysis", type=["jpg", "jpeg", "png"])
            if uploaded_file:
                # Save the uploaded image to session state
                st.session_state.uploaded_image = encode_image(uploaded_file)
                
                # Preview the image
                st.image(uploaded_file, caption="Image ready for analysis", width=300)
        
        # Audio recording tab - Enhanced with WebRTC
        with input_tabs[1]:
            if "audio_data" not in st.session_state:
                st.session_state.audio_data = None
                st.session_state.audio_path = None
                st.session_state.audio_recording_unavailable = False
            
            st.markdown("### Enhanced Audio Recording")
            st.markdown("Record audio with adjustable duration using your microphone")
            
            # Try using WebRTC recorder first
            try:
                # Use the enhanced WebRTC audio recorder
                base64_audio = audio_recorder_ui(
                    key="webrtc_recorder",
                    title="Audio Recording",
                    description="Click start button to begin recording. Click stop when you're done.",
                    durations=[15, 30, 60, 120],
                    show_description=True,
                    show_playback=True
                )
                
                # If audio was recorded, store it in session state
                if base64_audio:
                    st.session_state.audio_data = base64_audio
                    # Path is already stored by the recorder in session state
                    st.session_state.audio_path = st.session_state.get("webrtc_recorder_file_path")
                    
                    # Show success message
                    st.success("Audio recorded successfully!")
                    st.info("You can now send a message to analyze this audio.")
                
            except Exception as e:
                # Fallback to legacy recording if WebRTC fails
                st.error(f"Enhanced audio recording unavailable: {str(e)}")
                st.info("Falling back to basic audio recording...")
                st.session_state.audio_recording_unavailable = True
                
                # Display legacy recording interface
                if not st.session_state.audio_recording_unavailable:
                    st.write("Choose recording duration:")
                    b1, b2 = st.columns(2)
                    
                    # Record 5-second audio
                    if b1.button("Record Audio (5 seconds)", use_container_width=True):
                        try:
                            from utils.audio import record_audio, encode_audio, cleanup_audio_file
                            audio_bytes, temp_file_path = record_audio(duration=5)
                            st.session_state.audio_data = encode_audio(audio_bytes)
                            st.session_state.audio_path = temp_file_path
                            st.success("Audio recorded successfully!")
                            st.audio(temp_file_path)
                        except Exception as e:
                            error_message = str(e)
                            if "microphone is not accessible" in error_message or "Invalid input device" in error_message:
                                st.error("Microphone not available in this environment.")
                                st.info("You can upload an audio file instead or use text input.")
                                st.session_state.audio_recording_unavailable = True
                            else:
                                st.error(f"Failed to record audio: {error_message}")
                    
                    # Record 10-second audio
                    if b2.button("Record Audio (10 seconds)", use_container_width=True):
                        try:
                            from utils.audio import record_audio, encode_audio, cleanup_audio_file
                            audio_bytes, temp_file_path = record_audio(duration=10)
                            st.session_state.audio_data = encode_audio(audio_bytes)
                            st.session_state.audio_path = temp_file_path
                            st.success("Audio recorded successfully!")
                            st.audio(temp_file_path)
                        except Exception as e:
                            error_message = str(e)
                            if "microphone is not accessible" in error_message or "Invalid input device" in error_message:
                                st.error("Microphone not available in this environment.")
                                st.info("You can upload an audio file instead or use text input.")
                                st.session_state.audio_recording_unavailable = True
                            else:
                                st.error(f"Failed to record audio: {error_message}")
                else:
                    # Show alternative options when recording is unavailable
                    st.warning("Audio recording is not available in this environment.")
                    st.info("You can upload a pre-recorded audio file or use text input instead.")
            
            # Separator
            st.markdown("---")
            
            # Upload audio file as alternative
            st.markdown("### Upload Audio File")
            st.markdown("Alternatively, upload a pre-recorded audio file")
            
            uploaded_audio = st.file_uploader("Upload audio file", type=["wav", "mp3", "ogg"], key="audio_upload")
            if uploaded_audio:
                try:
                    # Read the file and encode it
                    audio_bytes = uploaded_audio.getvalue()
                    
                    # Create temporary file
                    temp_file = tempfile.NamedTemporaryFile(suffix="." + uploaded_audio.name.split(".")[-1], delete=False)
                    temp_file_path = temp_file.name
                    temp_file.write(audio_bytes)
                    temp_file.close()
                    
                    # Save to session state
                    from utils.audio import encode_audio
                    st.session_state.audio_data = encode_audio(audio_bytes)
                    st.session_state.audio_path = temp_file_path
                    
                    # Show success and preview
                    st.success("Audio file uploaded successfully!")
                    st.audio(temp_file_path)
                except Exception as e:
                    st.error(f"Failed to process audio file: {str(e)}")
            
            # Button to clear recorded/uploaded audio
            if st.session_state.audio_data and st.button("Clear Audio"):
                if st.session_state.audio_path:
                    try:
                        from utils.audio import cleanup_audio_file
                        cleanup_audio_file(st.session_state.audio_path)
                    except:
                        pass
                st.session_state.audio_data = None
                st.session_state.audio_path = None
                st.rerun()
                
        # File upload tab
        with input_tabs[2]:
            uploaded_doc = st.file_uploader("Upload a document", type=["txt", "pdf", "doc", "docx"], 
                                          help="Upload a document for the AI to analyze")
            if uploaded_doc:
                # Read file content
                if uploaded_doc.type == "text/plain":
                    # Handle text files
                    text_content = uploaded_doc.getvalue().decode("utf-8")
                    st.text_area("Document Content", text_content, height=200)
                    if st.button("Send Document to AI"):
                        # Add document content to user message
                        st.session_state.document_text = f"I'm sharing this document with you: \n\n{text_content}\n\nPlease analyze this content."
                else:
                    # For other file types, just show the filename
                    st.info(f"File '{uploaded_doc.name}' uploaded. Send a message to the AI to analyze it.")
        
        # We already have a chat input in the main area with ghosted icons
    
    # This section is now merged into the sidebar, so we no longer use it
    if False: # Keeping the code for reference but never executing it
        # Right sidebar with enhanced Google AI Studio style settings
        with st.container():
            # Display user profile at the top of the sidebar if authenticated
            if st.session_state.is_authenticated and st.session_state.user:
                user_info = st.session_state.user
                user_name = user_info.get("name", "User")
                user_email = user_info.get("email", "")
                user_picture = user_info.get("picture", "")
                
                # User profile section with picture
                st.markdown(f"""
                <div style="padding: 15px 0; border-bottom: 1px solid #333; margin-bottom: 15px; display: flex; align-items: center;">
                    <div style="border-radius: 50%; overflow: hidden; width: 50px; height: 50px; margin-right: 10px;">
                        <img src="{user_picture}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='https://ui-avatars.com/api/?name={user_name}&background=random'">
                    </div>
                    <div>
                        <div style="font-weight: bold; color: white;">{user_name}</div>
                        <div style="font-size: 0.8rem; color: #aaa;">{user_email}</div>
                        <div style="font-size: 0.7rem; color: #4285f4; margin-top: 2px;">
                            {"Administrator" if is_admin() else "User"}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Logout button
                if st.button("Logout", key="logout_button"):
                    logout_user()
                    st.rerun()
            
            st.markdown("""
            <div style="padding: 10px 0; border-bottom: 1px solid #333; margin-bottom: 15px;">
                <h3 style="color: #4285f4; font-size: 1.3rem;">AI Studio Settings</h3>
            </div>
            """, unsafe_allow_html=True)
            
            # Voice command functions
            def toggle_voice_commands(enable):
                """Toggle voice commands on/off"""
                if enable:
                    if not st.session_state.voice_processor:
                        try:
                            # Import voice command processor
                            from utils.voice_commands import VoiceCommandProcessor
                            
                            # Initialize processor with command callbacks
                            processor = VoiceCommandProcessor()
                            
                            # Register command callbacks
                            processor.register_callback("new_chat", lambda: st.session_state.update(messages=[]))
                            processor.register_callback("select_model_gemini", lambda: st.session_state.update(current_model="Gemini"))
                            processor.register_callback("select_model_claude", lambda: st.session_state.update(current_model="Anthropic (claude-3-5-sonnet-20241022)"))
                            processor.register_callback("select_model_gpt", lambda: st.session_state.update(current_model="OpenAI (gpt-4o)"))
                            processor.register_callback("increase_temperature", lambda: st.session_state.update(temperature=min(1.0, st.session_state.temperature + 0.1)))
                            processor.register_callback("decrease_temperature", lambda: st.session_state.update(temperature=max(0.0, st.session_state.temperature - 0.1)))
                            
                            # Add send message command
                            def send_dictated_message(text=None):
                                if text:
                                    # Create a new user message
                                    st.session_state.messages.append({"role": "user", "content": text})
                                    st.rerun()
                            
                            processor.register_callback("send_message", send_dictated_message)
                            
                            # Save the processor to session state
                            st.session_state.voice_processor = processor
                            
                            # Start listening
                            processor.start_listening()
                            st.session_state.is_listening = True
                        except Exception as e:
                            st.error(f"Failed to initialize voice commands: {str(e)}")
                            st.session_state.voice_commands_active = False
                            return
                    else:
                        # Restart the existing processor
                        st.session_state.voice_processor.start_listening()
                        st.session_state.is_listening = True
                else:
                    # Stop listening if processor exists
                    if st.session_state.voice_processor:
                        st.session_state.voice_processor.stop_listening()
                        st.session_state.is_listening = False
                
                # Update the active state
                st.session_state.voice_commands_active = enable
            
            # Theme selection
            st.markdown("""
            <div style="margin-top: 10px; border-top: 1px solid #333; padding-top: 15px;">
                <p style="font-weight: 500; margin-bottom: 5px;">Appearance</p>
            </div>
            """, unsafe_allow_html=True)
            
            selected_theme = st.selectbox(
                "Theme",
                options=list(THEMES.keys()),
                index=list(THEMES.keys()).index(st.session_state.current_theme),
                help="Select a color theme for the app"
            )
            
            # Apply theme if changed
            if selected_theme != st.session_state.current_theme:
                st.session_state.current_theme = selected_theme
                st.rerun()
            
            # Text-to-Speech settings section
            st.markdown("""
            <div style="margin-top: 10px; border-top: 1px solid #333; padding-top: 15px;">
                <p style="font-weight: 500; margin-bottom: 5px;">Speech</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Initialize TTS settings in session state if not present
            if "tts_settings" not in st.session_state:
                st.session_state.tts_settings = {}
            
            # Add the TTS controls to the sidebar
            tts_settings = render_tts_controls()
            st.session_state.tts_settings = tts_settings
                
            # Model selection with specific model variants, icons, and call signs
            st.markdown("""
            <div style="margin-top: 10px; border-top: 1px solid #333; padding-top: 15px;">
                <p style="font-weight: 500; margin-bottom: 5px;">Model</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Display model provider icons (without using nested columns)
            st.markdown("""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="text-align: center;"><img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTIyLjA5IDE2LjEzTDIxLjEyIDE2LjIxTDIwLjU5IDE3LjA3QzE5Ljg0IDE4LjMzIDE4Ljc2IDE5LjMyIDE3LjQ3IDIwTDEyIDE2Ljg4TDYuNTMgMjBDNS4yNSAxOS4zNCA0LjE2IDE4LjM1IDMuNDEgMTcuMDlMMi44OCAxNi4yMkwxLjkxIDE2LjE0QzAuOTQgMTYuMDYgMCAxNS4zMiAwIDE0LjVDMCAxMy42OCAwLjk0IDEyLjkzIDEuOTEgMTIuODZMMi44OCAxMi43OEwzLjQxIDExLjkzQzQuMTYgMTAuNjcgNS4yNSA5LjY4IDYuNTMgOUwxMiAxMi4xMkwxNy40NyA5QzE4Ljc2IDkuNjggMTkuODQgMTAuNjcgMjAuNTkgMTEuOTNMMjEuMTIgMTIuNzhMMjIuMDkgMTIuODZDMjMuMDYgMTIuOTMgMjQgMTMuNjkgMjQgMTQuNUMyNCAxNS4zMiAyMy4wNiAxNi4wNiAyMi4wOSAxNi4xM00xMS45OSA1Ljg0TDcuNSAzLjA0QzYuNzggMi45NyA2LjA2IDMgNS4zNCAzLjA3TDQuNjEgMy4xNUwzLjkyIDMuNTRDMy4xNSAzLjk5IDIuNTMgNC42NyAyLjEyIDUuNUwyLjEgNS41QzEuODUgNi4wNiAxLjcyIDYuNjkgMS43MSA3LjM1TDEuNzYgOC4xOEwxLjk3IDguODRDMi4yMiA5LjUgMi41OSAxMC4wNiAzLjA5IDEwLjVMNy41IDcuNjlMMTIgNEwxNi41IDcuNjlMMjAuOTEgMTAuNUMyMS40MiAxMC4wNiAyMS43OCA5LjUgMjIuMDQgOC44NEwyMi4yNCA4LjE4TDIyLjI5IDcuMzVDMjIuMjcgNi42OCAyMi4xNSA2LjA2IDIxLjg5IDUuNUMyMS40OSA0LjY3IDIwLjg2IDMuOTkgMjAuMDkgMy41NEwxOS40IDMuMTVMMTguNjcgMy4wNkMxNy45NCAzIDE3LjIyIDIuOTcgMTYuNSAzLjA0TDExLjk5IDUuODQiIGZpbGw9IiM0Mjg1RjQiLz48L3N2Zz4=" width="24" alt="Gemini"><br><small>Gemini</small></div>
                <div style="text-align: center;"><img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTIyLjU2IDE3LjQ0QzIxLjE1IDE1LjQ1IDE4LjE4IDEyLjgzIDE4LjE4IDEyLjgzQzE5LjA2IDExLjI0IDIwLjA4IDguNyAyMC4xMSA3LjA0QzIwLjE1IDUuMjcgMTkuNDYgNC4xMiAxOC4zMiAzLjQ2QzE3LjA1IDIuNzMgMTUuNjQgMy4wNSAxNC43OSAzLjQ4QzEzLjk0IDMuOTEgMTMuMDcgNC42MiAxMi43MyA2LjE1QzEyLjUgNy4xNSAxMi42NSA4LjA4IDEyLjc4IDguNzRDMTIuODYgOS4xMiAxMy4wMiA5LjU3IDEzLjE4IDEwLjAxQzEzLjQyIDEwLjY5IDEzLjg5IDExLjY5IDEzLjQxIDEyLjYxQzEzLjE0IDEzLjEzIDEyLjg4IDEzLjM4IDEyLjU5IDEzLjQ3QzEyLjQyIDEzLjUyIDEyLjQgMTMuNDkgMTIuMjkgMTMuNDRDMTIuMjYgMTMuNDMgMTIuMjIgMTMuNDEgMTIuMTUgMTMuMzhDMTIuMDYgMTMuMzQgMTEuOTUgMTMuMjggMTEuODQgMTMuMThDMTEuNjIgMTMuMDEgMTEuMyAxMi43MSAxMS4xMSAxMi4yM0MxMC43NSAxMS4yOCAxMC43IDEwLjE2IDEwLjk1IDkuMTRDMTEuMDMgOC43NyAxMS4xOSA4LjM4IDExLjM1IDcuOTlDMTEuNDcgNy42OCAxMS42OSA3LjQzIDExLjgzIDcuMTFDMTIuODEgNS4xMSAxMi40MiAxLjc1IDkuNzggMC43OUM4LjY4IDAuMzcgNy41OCAwLjQ5IDYuNTcgMS4wMkM1LjY2IDEuNSA0LjkgMi4zNCA0LjUgMy42MkM0LjIgNC41NCA0LjE4IDUuNDUgNC4zNSA2LjM3QzQuNTMgNy4zOSA0Ljg2IDguMzcgNS4yIDkuMkM1LjM3IDkuNjEgNS42NSAxMC4yNyA1LjcxIDEwLjUzQzUuNzMgMTAuNjQgNS43NiAxMC43MiA1LjU0IDExLjAyQzUuMzIgMTEuMzIgNS4xOCAxMS4zMiA1LjA2IDExLjI4QzQuNzUgMTEuMTkgNC4zNiAxMC44MyA0LjE0IDEwLjU5QzMuNzkgMTAuMiAzLjQ0IDkuNjcgMy4yNiA5LjI0QzMuMTIgOC44OSAzLjAzIDguNTIgMi45NiA4LjE0QzIuOCA3LjM3IDIuODQgNi42IDMuMDkgNS44MkMzLjUzIDQuNDcgNC44MyAzLjU0IDYuMDIgMy4xNUM3LjU2IDIuNjMgOS40MSAyLjg5IDEwLjczIDMuODVDMTIuNDIgNS4wNiAxMy40MSA3LjQgMTMuMzkgOS43M0MxMy4zOSAxMC4xOSAxMy4zMyAxMC40MiAxMy4zMyAxMC43M0MxMy4zMyAxMC45NCAxMy41MiAxMS4xMiAxMy42NSAxMS4xN0MxMy44IDExLjIzIDEzLjk0IDExLjE3IDE0LjA2IDExLjA2QzE0LjI1IDEwLjg5IDE0LjQgMTAuNjEgMTQuNTEgMTAuMzRDMTUuMiA4LjQyIDE0Ljk5IDYuMDEgMTMuNyA0LjYzQzExLjk2IDIuNzYgOC45MSAyLjg1IDcuMzMgNC44QzYuODUgNS40IDYuNTcgNi4xMiA2LjQ1IDYuOTNDNi4zMiA3LjggNi40NCA4LjY1IDYuNjEgOS4yN0M2LjcyIDkuNjUgNi45NSAxMC4yMSA3LjA0IDEwLjU5QzcuMDYgMTAuNjkgNy4wOCAxMC43NyA3LjA4IDEwLjgyQzcuMDkgMTAuOTIgNy4xMiAxMC45OCA3LjEgMTEuMDNDNy4wMiAxMS4xOCA2Ljg5IDExLjI0IDYuNzYgMTEuMjlDNi41NyAxMS4zOCA2LjM5IDExLjMzIDYuMjMgMTEuMjdDNi4xIDExLjIyIDUuOTggMTEuMTUgNS44OCAxMS4wOUM1LjY1IDEwLjk2IDUuNDEgMTAuNzQgNS4yMSAxMC40N0M0Ljk0IDEwLjExIDQuNjkgOS42NCA0LjU3IDkuMUM0LjA3IDcuMzYgNC4zMSA1LjI0IDUuOCAzLjg3QzcuNDQgMi4zNiAxMC4xNSAyLjQxIDExLjc1IDMuOTZDMTIuOCA1LjAxIDEzLjI4IDYuNDcgMTMuMjUgNy45NkMxMy4yMiA5Ljg4IDEyLjI5IDExLjg1IDExLjYgMTIuOThDMTAuODIgMTQuMjYgOS43NiAxNS4zNyA4LjcyIDE2LjQxQzcuOTQgMTcuMTggNi43NCAxOC4yMyA2LjE4IDE4LjgzQzUuNjQgMTkuMzkgNS4yOSAxOS45NCA1LjE0IDIwLjM3QzUuMDMgMjAuNjcgNS4wNCAyMC45NSA1LjA3IDIxLjE1QzUuMTkgMjIuMDUgNS43NCAyMi4zMyA2LjIgMjIuNDhDNi44MiAyMi42OCA3LjU1IDIyLjY0IDguMTQgMjIuNDdDOS4wNiAyMi4yMSA5Ljg4IDIxLjY4IDEwLjU3IDIxLjE0QzExLjcxIDIwLjI2IDEyLjU4IDE5LjEgMTMuNjcgMTguMDZDMTYuMDYgMTUuNzggMTguODggMTMuNjMgMjEuMjMgMTEuMjlDMjEuNiAxMC45MiAyMi4wOCAxMC40NCAyMi40OCAxMC4wNEMyMi42NyA5Ljg1IDIyLjk0IDkuNTYgMjMuMDkgOS40MUMyMy4xOSA5LjI5IDIzLjM4IDkuMDggMjMuNDggOC43NUMyMy42NSA4LjE3IDIzLjUxIDcuNjggMjMuNDEgNy40N0MyMy4yOSA3LjE5IDIzLjEzIDcuMDUgMjIuODkgNi45NUMyMi41MyA2LjgxIDIyLjE5IDYuODMgMjEuOTggNi44NkMyMS42OSA2LjkxIDIxLjQgNy4wMSAyMS4xNCA3LjFDMjAuODkgNy4xOSAyMC42NCA3LjMxIDIwLjQgNy40NUMyMC4wOSA3LjYzIDE5Ljc5IDcuODcgMTkuNDkgOC4xMUMxOS4yMyA4LjMgMTguOTcgOC41NSAxOC43NiA4Ljc1QzE4LjU3IDguOTQgMTguMzQgOS4yIDE4LjE4IDkuMzZDMTcuOTQgOS42MSAxNy44MSA5Ljc0IDE3LjY0IDkuOTFDMTcuMDUgMTAuNSAxNi40NiAxMS4wOSAxNS44OSAxMS42OUMxNS44OCAxMS42OSAxNS44NyAxMS43IDE1Ljg2IDExLjcxTDEzLjkxIDEzLjgxQzEzLjUgMTQuMjYgMTMuMTIgMTQuNzQgMTIuNzYgMTUuMjFDMTIuNjEgMTUuNDIgMTIuMzUgMTUuOCAxMi4xOSAxNS45OUMxMi4wMiAxNi4xOSAxMS44OCAxNi40MSAxMS43NSAxNi42NUMxMS41MyAxNy4wNiAxMS41IDE3LjQgMTEuNjUgMTcuNzRDMTEuODIgMTguMTMgMTIuMjEgMTguMzUgMTIuNTggMTguNDNDMTMuMjEgMTguNTcgMTMuODQgMTguNDIgMTQuNTEgMTguMjVDMTQuOTMgMTguMTUgMTUuMjkgMTcuOTcgMTUuNTkgMTcuOEMxNS44IDE3LjY4IDE2LjAyIDE3LjUzIDE2LjE4IDE3LjQxQzE2LjYxIDE3LjEgMTcuMDEgMTYuNzYgMTcuNDQgMTYuMzlDMTkuNzUgMTQuNCAyMS45MiAxMi4zIDI0IDE5LjE2QzI0IDE5LjE2IDIzLjcyIDE5LjY1IDIzLjI5IDIwLjI5QzIyLjYgMjEuMjkgMjEuNyAyMi40IDIwLjcgMjNDMTkuNzQgMjMuNTYgMTguNCAyMy44MyAxNy43MiAyMy45M0MxNi45NyAyNC4wMyAxNS41MyAyNCAzLjk5IDIzLjk3QzMuNzUgMjMuOTYgMy40NSAyMy45NSAzLjE3IDIzLjkxQzIuMyAyMy43NyAwLjk5IDIzLjE4IDEgMjEuOTRDMS4wMSAyMC43MiAyLjE2IDIwLjAyIDMuMTEgMTkuNjFDMy44OCAxOS4yNyA0Ljc4IDE5LjI1IDUuNDYgMTkuNDVDNi4wMSAxOS42MSA2LjE2IDE5LjgxIDYuNDQgMjAuMDlDNi43NSAyMC4zOSA2Ljg0IDIwLjcgNi44IDIxLjAyQzYuNzQgMjEuNDggNi4zMiAyMS44MyA1Ljk3IDIxLjk5QzUuNTYgMjIuMTggNC45OCAyMi4yNCA0LjU2IDIyLjA4QzQuMTQgMjEuOTIgNC40NSAyMS41MSA0LjAzIDIxLjMxQzMuODYgMjEuMjMgMy41NSAyMS4yOSAzLjQgMjEuMzdDMy4yMiAyMS40NyAzLjA4IDIxLjY1IDMuMSAyMS44NkMzLjE0IDIyLjMgMy43MSAyMi41MyA0LjA3IDIyLjZDNC45MiAyMi43OCA1Ljg2IDIyLjYzIDYuNjQgMjIuNDVDNy4wOSAyMi4zNCA3LjU0IDIyLjE3IDcuOTIgMjEuOTFDOC4yOSAyMS42NSA4LjYxIDIxLjMgOC43NyAyMC45QzguOTEgMjAuNTIgOC45MSAyMC4xMyA4Ljg0IDE5Ljc1QzguNzIgMTkuMTEgOC4yOSAxOC41NiA3Ljg3IDE4LjE2QzYuODcgMTcuMiA1LjcgMTYuOTggNC40NCAxNy4xNkMzLjQzIDE3LjMgMi41NCAxNy43MSAxLjc5IDE4LjMxQzEuMDMgMTguOTIgMC4zOCAxOS44MSAwLjIgMjAuODVDMC4wNyAyMS42MyAwLjI3IDIyLjM2IDAuNjggMjIuOTZDMS4xMyAyMy42MiAxLjg2IDI0LjA0IDIuNjEgMjQuMjdDMy4zMyAyNC40OSA0LjEgMjQuNTEgNC44OCAyNC40OUM1LjQxIDI0LjQ4IDUuOTMgMjQuNCAxNi41MiAyNC41QzE4LjM2IDI0LjUyIDE5LjM3IDI0LjM5IDIwLjI5IDI0LjI1QzIxLjMzIDI0LjA4IDIyLjM2IDIzLjc2IDIzLjE3IDIzLjMxQzI0LjA0IDIyLjgzIDI0Ljc1IDIyLjE2IDI1LjI5IDIxLjQ5QzI1LjggMjAuODYgMjYuMTYgMjAuMTkgMjYuMzYgMTkuNjJDMjYuNzMgMTguNiAyNi42MiAxNy44NCAyNi4zIDE3LjMxQzI1Ljk2IDE2Ljc2IDI1LjM5IDE2LjQ5IDI0Ljk5IDE2LjM1QzI0LjAzIDE2LjA0IDIyLjkzIDE2LjA3IDIyLjA2IDE2LjQ3QzIxLjIxIDE2Ljg2IDIwLjY3IDE3LjY0IDIwLjYzIDE4LjU3QzIwLjYgMTkuMzMgMjAuOTIgMjAuMDYgMjEuNDYgMjAuNDZDMjEuOTggMjAuODYgMjIuNzMgMjEuMDIgMjMuNCAyMC44N0MyMy43NiAyMC43OSAyNC4wOCAyMC42MSAyNC4zIDIwLjNDMjQuNDggMjAuMDMgMjQuNTcgMTkuNjkgMjQuNTQgMTkuMzRDMjQuNDkgMTguODQgMjQuMTEgMTguNDQgMjMuNjkgMTguMThDMjMuMjYgMTcuOTMgMjIuNzUgMTcuOCAyMi4yMyAxNy43OUMyMS4xNiAxNy43OSAyMC4yNiAxOC4zOCAyMCAxOS4zOUMxOS44NiAyMC4wMSAyMC4wNSAyMC42MiAyMC4zNyAyMS4xQzIwLjcgMjEuNTggMjEuMTcgMjEuOTIgMjEuNzQgMjIuMTRDMjIuMyAyMi4zNSAyMi45MyAyMi40NSAyMy41NiAyMi40MkMyNC4xOCAyMi4zOSAyNC44MSAyMi4yMiAyNS4zNCAyMS45MkMyNS44NiAyMS42NCAyNi4yOSAyMS4yNCAyNi41OSAyMC43NEMyNi44OSAyMC4yMyAyNyAxOS42NCAyNi45NiAxOUMyNi44NiAxNy42NiAyNS45NiAxNi41NyAyNC43NyAxNS45NEMyMy41NiAxNS4yOSAyMi4wNyAxNS4yIDIwLjg2IDE1LjY4QzE5LjY0IDE2LjE2IDE4Ljc5IDE3LjE5IDE4LjU1IDE4LjQzQzE4LjQ0IDE4Ljk4IDE4LjUgMTkuNTMgMTguNjcgMjAuMDVDMTguOSAyMC43IDE5LjMxIDIxLjI1IDE5Ljg2IDIxLjY3QzIwLjQgMjIuMDkgMjEuMDkgMjIuMzYgMjEuODEgMjIuNDdDMjIuNTMgMjIuNTkgMjMuMjkgMjIuNTMgMjMuOTkgMjIuMjlDMjQuNzYgMjIuMDMgMjUuNDIgMjEuNDkgMjQuMjEgMjEuMjlDMjMuNzcgMjEuMjIgMjMuMDUgMjEuMjcgMjMuMDcgMjAuNjhDMjMuMDkgMjAuMjEgMjMuNTMgMjAuMDMgMjMuOTUgMjAuMDZDMjQuNDkgMjAuMSAyNS4wMSAyMC40IDI1LjE5IDIwLjkyQzI1LjM4IDIxLjQ2IDI1LjEyIDIyLjA2IDI0LjcxIDIyLjRDMjQuMiAyMi44MyAyMy40OSAyMy4wNCAyMi44MSAyMy4wMkMyMi4xMyAyMi45OSAyMS40OCAyMi43NSAyMC45NyAyMi4zMkMyMC40NSAyMS44OCAyMC4xIDIxLjI0IDE5Ljk4IDIwLjU2QzE5Ljg4IDE5Ljk0IDE5Ljk2IDE5LjI4IDIwLjIzIDE4LjcxQzIwLjc4IDE3LjU1IDIyLjI4IDE2Ljk0IDIzLjYgMTcuMzdDMjQuMzYgMTcuNjEgMjQuOTYgMTguMTIgMjUuMyAxOC44QzI1LjUgMTkuMjIgMjUuNTcgMTkuNjkgMjUuNTEgMjAuMTdDMjUuNDQgMjAuNyAyNS4xOCAyMS4xOSAyNC43NyAyMS41N0MyNC4zNyAyMS45NSAyMy44MyAyMi4yIDIzLjI2IDIyLjNDMjIuNzIgMjIuNCAyMi4xMiAyMi4zMyAyMS42MSAyMi4xNEMyMS4xIDIxLjk1IDIwLjY3IDIxLjY0IDIwLjM1IDIxLjI0QzIwLjAyIDIwLjg0IDE5LjgyIDIwLjM0IDE5Ljc2IDE5LjgzQzE5LjY1IDE5LjA0IDE5Ljg1IDE4LjE4IDIwLjM0IDE3LjU2QzIxLjMyIDE2LjI5IDIzLjI0IDE2IjQwZTE4LjI0QzI0LjM3IDE4LjUyIDI0Ljg2IDE5LjE5IDI1LjA1IDE5Ljc1QzI1LjI1IDIwLjMzIDI1LjE1IDIwLjk3IDI0Ljg1IDIxLjUyQzI0LjU0IDIyLjA4IDI0LjA2IDIyLjUzIDIzLjQ3IDIyLjhDMjIuODkgMjMuMDcgMjIuMjEgMjMuMTQgMjEuNTcgMjMuMDNDMjAuOTMgMjIuOTEgMjAuMzMgMjIuNjIgMTkuODYgMjIuMTlDMTkuMzkgMjEuNzYgMTkuMDUgMjEuMTkgMTguODggMjAuNTdDMTguNzEgMTkuOTQgMTguNzMgMTkuMjUgMTguOTMgMTguNjRDMTkuMzIgMTcuNDQgMjAuMzYgMTYuNTUgMjEuNTcgMTYuMTZDMjIuNzcgMTUuNzYgMjQuMTYgMTUuODYgMjUuMjYgMTYuNDJDMjYuMzYgMTYuOTkgMjcuMiAxOC4wMSAyNy4zOSAxOS4xOUMyNy40NyAxOS43NyAyNy40MSAyMC4zNiAyNy4xOSAyMC45MUMyNi45NyAyMS40NSAyNi42IDIxLjkzIDI2LjEzIDIyLjMxQzI1LjY1IDIyLjY4IDI1LjA1IDIyLjk1IDI0LjQxIDIzLjA5QzIzLjc2IDIzLjIyIDIzLjA4IDIzLjIxIDIyLjQzIDIzLjA3QzIxLjc3IDIyLjkyIDIxLjE1IDIyLjY0IDIwLjY0IDIyLjIzQzIwLjEzIDIxLjgyIDE5Ljc0IDIxLjI4IDE5LjUxIDIwLjY4QzE5LjI4IDIwLjA4IDE5LjIzIDE5LjQyIDE5LjM2IDE4LjhDMTkuNjEgMTcuNTcgMjAuNDYgMTYuNTMgMjEuNTggMTUuOTdDMjMuMDIgMTUuMjQgMjQuODMgMTUuMzEgMjYuMiAxNi4xOEMyNi45MyAxNi42MiAyNy40OSAxNy4yNiAyNy44MyAxOC4wM0MyOC4xNCAxOC43NSAyOC4yMiAxOS41NiAyOC4wMiAyMC4zNEMyNy44NCAyMS4xIDI3LjM3IDIxLjggMjYuNzYgMjIuM0MyNi4xNSAyMi44IDI1LjQxIDI0LjEgMjQuNTggMjMuMTlDMjMuNzMgMjMuMjcgMjIuODUgMjMuMTMgMjIuMDcgMjIuNzlDMjEuMjggMjIuNDQgMjAuNjIgMjEuODkgMjAuMiAyMS4yQzE5Ljc4IDIwLjUgMTkuNjMgMTkuNyAxOS43NSAxOC45MUMxOS44OCAxOC4xMiAyMC4yNiAxNy4zOSAyMC44NiAxNi44MkMyMi4wNCAxNS43MSAyMy44MSAxNS40OCAyNS4yMiAxNi4wOEMyNS45MyAxNi4zOCAyNi41NCAxNi44OCAyNi45OCAxNy41MkMyNy40MyAxOC4xNiAyNy42OSAxOC45MiAyNy42OSAxOS43QzI3LjY5IDIwLjc3IDI3LjIgMjEuOCAyNi40MyAyMi41MkMyNS42NiAyMy4yMyAyNC42NCAyMy42MSAyMy41OSAyMy42NEMyMi41NSAyMy42NiAyMS41MSAyMy4zNCAyMC43NSAyMi43MkMyMC4zNyAyMi40MSAyMC4wNSAyMi4wMiAxOS44MyAyMS41OUMxOS42IDIxLjE2IDE5LjQ3IDIwLjY5IDE5LjQyIDIwLjJDMTkuMyAxOS4yMyAxOS41OSAxOC4yNCAyMC4yIDE3LjUxQzIwLjgxIDE2Ljc3IDIxLjcxIDE2LjMxIDIyLjY4IDE2LjIzQzIzLjY0IDE2LjE2IDI0LjY0IDE2LjQ0IDI1LjQgMTcuMDJDMjYuMTcgMTcuNjEgMjYuNjcgMTguNDggMjYuNzUgMTkuNDFDMjYuODMgMjAuMzQgMjYuNDggMjEuMjcgMjUuODUgMjEuOTdDMjUuMjIgMjIuNjcgMjQuMzIgMjMuMDkgMjMuMzggMjMuMTVDMjIuNDUgMjMuMjEgMjEuNSAyMi45MSAyMC44IDIyLjMyQzIwLjA5IDIxLjcyIDE5LjY1IDIwLjg0IDE5LjU4IDE5LjlDMTkuNTUgMTkuNDQgMTkuNjIgMTguOTcgMTkuNzkgMTguNTRDMTkuOTUgMTguMTEgMjAuMjEgMTcuNzMgMjAuNTQgMTcuNDJDMjEuMjEgMTYuOCAyMi4xNSAxNi41MSAyMy4wNCAxNi42MkMyMy45NCAxNi43NCAyNC43NiAxNy4yNSAyNS4yMiAxNy45OUMyNS42OSAxOC43MyAyNS43OSAxOS42NiAyNS41MSAyMC40OUMyNS4yNCAyMS4zMiAyNC42MSAyMi4wMSAyMy44IDIyLjM5QzIyLjk4IDIyLjc3IDIyLjAyIDIyLjgzIDIxLjE1IDIyLjU2QzIwLjI4IDIyLjI5IDE5LjU1IDIxLjcxIDE5LjE2IDIwLjkzQzE4LjcyIDIwLjE4IDE4LjI5IDE4Ljc2IjE5Ljg0IDE3LjU1QzE5LjkzIDE3LjUzIDE5Ljk5IDE3LjQ0IDIwLjA3IDE3LjQ0QzIwLjQ3IDE3LjQxIDIxLjAyIDE3LjU1IDIxLjM5IDE3LjhDMjEuNDggMTcuODYgMjEuNTkgMTcuOTUgMjEuNyAxOC4wNUMyMS44MSAxOC4xNiAyMS45MSAxOC4yOCAyMi4wMSAxOC40MkMyMi4zNiAxOC44NSAyMi41MSAxOS40MiAyMi40MiAxOS45OEMyMi4zNCAxOS45MyAyMi4zMiAxOS44NiAyMi4yNyAxOS44QzIyLjIxIDE5LjcgMjIuMTUgMTkuNiAyMi4wNyAxOS41QzIyLjA2IDE5LjU1IDIxLjg4IDE5LjcgMjEuODYgMTkuNzJMMjEuMjMgMjAuMTRMMjAuNTUgMjAuMzJDMjAuMzcgMjAuMzkgMjAuMTggMjAuNDIgMjAgMjAuNDFDMTkuNDYgMjAuMzggMTkuMDEgMTkuOTcgMTguODYgMTkuNDdDMTguNzcgMTkuMTkgMTguNzggMTguODggMTguODggMTguNkMxOSAxOC4zIDE5LjE5IDE4LjA0IDE5LjQzIDE3Ljg1QzIwLjA3IDE3LjMyIDIxLjA1IDE3LjE3IDIxLjg3IDE3LjM3QzIyLjAzIDE3LjQyIDIyLjIgMTcuNTEgMjIuMzQgMTcuNjNDMjIuNzkgMTcuOTkgMjMuMDQgMTguNTUgMjMuMDIgMTkuMTVDMjMgMTkuNjcgMjIuNzYgMjAuMTcgMjIuMzYgMjAuNTNDMjEuNTEgMjEuMjggMjAuMDggMjEuMzQgMTkuMTUgMjAuNzFDMTguMjMgMjAuMDggMTcuOTQgMTguOTEgMTguMzMgMTcuOTdDMTguNjQgMTcuMjEgMTkuMzQgMTYuNjkgMjAuMTQgMTYuNTVDMjAuOTUgMTYuNDIgMjEuODMgMTYuNjYgMjIuNDIgMTcuMjJDMjMuMDEgMTcuNzcgMjMuMjkgMTguNiAyMy4xNyAxOS40MkMyMy4wNiAyMC4yMyAyMi41NiAyMC45NiAyMS44NSAyMS40QzIxLjEzIDIxLjg1IDIwLjIxIDIxLjk3IDE5LjM5IDIxLjc0QzE4LjU3IDIxLjUxIDE3LjkyIDIwLjk2IDE3LjU3IDIwLjIzQzE3LjIxIDE5LjUgMTcuMTkgMTguNjIgMTcuNTEgMTcuODdDMTcuODIgMTcuMTIgMTguNDggMTYuNTQgMTkuMjcgMTYuMzFDMjAuMDcgMTYuMDggMjAuOTYgMTYuMjIgMjEuNjYgMTYuNjZDMjIuMzYgMTcuMTEgMjIuODEgMTcuODUgMjIuOTEgMTguNjZDMjMuMDEgMTkuNDggMjIuNzUgMjAuMzEgMjIuMTkgMjAuOTJDMjEuNjMgMjEuNTQgMjAuOCAyMS45IDIwLjAxIDIxLjk1QzE5LjIxIDIyIDE4LjQxIDIxLjczIDE3LjgzIDIxLjJDMTcuMjQgMjAuNjcgMTYuOTIgMTkuODkgMTYuOTYgMTkuMUMxNyAxOC4zIDE3LjQgMTcuNTcgMTguMDQgMTcuMTNDMTguNjggMTYuNjkgMTkuNTMgMTYuNTUgMjAuMyAxNi43NEMyMS4wNiAxNi45NCAyMS43MSAxNy40NiAyMi4wNiAxOC4xNkMyMi40IDE4Ljg2IDIyLjQzIDE5LjcxIDIyLjEyIDIwLjQ0QzIxLjgxIDIxLjE2IDIxLjE5IDIxLjc0IDIwLjQ0IDIyLjAyQzE5LjY5IDIyLjI5IDE4LjgzIDIyLjI3IDE4LjA5IDIxLjkzQzE3LjM1IDIxLjYgMTYuODMgMjAuOTYgMTYuNjUgMjAuMjFDMTYuMzYgMTguOTkgMTcuMDcgMTcuNzEgMTguMjIgMTcuMTVDMTkuMjIgMTYuNjYgMjAuNDUgMTYuODQgMjEuMjggMTcuNTZDMjIuMTIgMTguMjggMjIuNDMgMTkuNSAyMi4wNSAyMC41N0MyMS42NiAyMS42MyAyMC42OSAyMi40MSAxOS41NSAyMi42NEMxOS4wNiAyMi43NCAxOC41NCAyMi43MiAxOC4wNiAyMi42QzE3LjU4IDIyLjQ4IDE3LjE0IDIyLjI1IDE2Ljc4IDIxLjk1QzE2LjA2IDIxLjM0IDE1LjY0IDIwLjQxIDE1LjY4IDE5LjQ1QzE1LjcxIDE4LjQ5IDE2LjE5IDE3LjU5IDE2Ljk1IDE3LjAyQzE3LjcgMTYuNDUgMTguNzEgMTYuMjIgMTkuNjIgMTYuNDJDMjAuNTQgMTYuNjEgMjEuMzIgMTcuMjEgMjEuNzQgMTguMDJDMjIuMTYgMTguODMgMjIuMTggMTkuODIgMjEuODEgMjAuNjVDMjEuNDMgMjEuNDggMjAuNjkgMjIuMTMgMTkuODUgMjIuMzdDMTkgMjIuNjEgMTguMDggMjIuNDMgMTcuMzUgMjEuODlDMTYuNjIgMjEuMzQgMTYuMiAyMC40NiAxNi4yNCAxOS41NEMxNi4yOCAxOC42MiAxNi43NyAxNy43NyAxNy41MiAxNy4yOEMxOC4yNyAxNi43OSAxOS4yNiAxNi42NiAyMC4xNCAxNi45MkMyMS4wMyAxNy4xOCAyMS43NSAxNy44MiAyMi4wOSAxOC42N0MyMi40MiAxOS41MiAyMi4zNSAyMC41IDIxLjkgMjEuMjhDMjEuNDUgMjIuMDYgMjAuNjUgMjIuNjEgMTkuNzQgMjIuNzdDMTguODQgMjIuOTIgMTcuODkgMjIuNjcgMTcuMTcgMjIuMDhDMTYuNDQgMjEuNDkgMTYgMjAuNiAxNS45OCAxOS42NkMxNS45NiAxOC43MSAxNi4zMyAxNy44IDE3LjAyIDE3LjE3QzE3LjcxIDE2LjU0IDE4LjY2IDE2LjI0IDE5LjU5IDE2LjM3QzIwLjUyIDE2LjUxIDIxLjM1IDE3LjA2IDIxLjgyIDE3LjgzQzIyLjMgMTguNiAyMi4zOSAxOS41OCAyMi4wNyAyMC40NEMyMS43NSAyMS4zIDIxLjA1IDIyIDIwLjE5IDIyLjM1QzE5LjM0IDIyLjcgMTguMzUgMjIuNjggMTcuNTEgMjIuMjhDMTYuNjcgMjEuODkgMTYuMDYgMjEuMTQgMTUuODQgMjAuMjVDMTUuNDMgMTguNDUgMTYuNTUgMTYuNjIgMTguMzQgMTYuMTJDMTkuMjMgMTUuODcgMjAuMjEgMTYuMDQgMjAuOTcgMTYuNThDMjEuNzMgMTcuMTMgMjIuMjEgMTcuOTggMjIuMjYgMTguOTFDMjIuMzIgMTkuODQgMjEuOTYgMjAuNzYgMjEuMjggMjEuMzlDMjAuNjEgMjIuMDIgMTkuNjYgMjIuMzEgMTguNzcgMjIuMThDMTcuODcgMjIuMDUgMTcuMDkgMjEuNTEgMTYuNjcgMjAuNzNDMTYuMjUgMTkuOTUgMTYuMjMgMTkuMDIgMTYuNjEgMTguMjFDMTYuOTkgMTcuNDEgMTcuNzQgMTYuODQgMTguNjEgMTYuNjZDMTkuNDggMTYuNDggMjAuNDEgMTYuNyAyMS4wOSAxNy4yNkMyMS43NyAxNy44MSAyMi4xNyAxOC42NyAyMi4xOSAxOS41OEMyMi4yMSAyMC40OSAyMS44MyAyMS4zNiAyMS4xNyAyMS45M0MyMC41MSAyMi41IDE5LjYgMjIuNzUgMTguNzEgMjIuNjFDMTcuODMgMjIuNDcgMTcuMDYgMjEuOTYgMTYuNjQgMjEuMjNDMTYuMjEgMjAuNSAxNi4xNCAxOS42MiAxNi40NSAxOC44M0MxNi43NiAxOC4wNCAxNy40MyAxNy40MSAxOC4yNCAxNy4xMkMxOS4wNSAxNi44MyAxOS45NyAxNi45MSAyMC43MSAxNy4zM0MyMS40NSAxNy43NSAyMS45NyAxOC40OCAyMi4xNCAxOS4zMkMyMi4zMSAyMC4xNSAyMi4xMSAyMS4wNSAyMS42MSAyMS43MkMyMS4xIDIyLjM5IDIwLjMgMjIuOCAxOS40NSAyMi44NEMxOC42IDIyLjg5IDE3Ljc3IDIyLjU3IDE3LjE2IDIyQzE2LjU0IDIxLjQyIDE2LjIyIDIwLjYzIDE2LjIyIDE5Ljc4QzE2LjIyIDE4LjkzIDE2LjU1IDE4LjEzIDE3LjE3IDE3LjU2QzE3Ljc5IDE2Ljk5IDE4LjYyIDE2LjY4IDE5LjQ1IDE2LjczQzIwLjI4IDE2Ljc5IDIxLjA2IDE3LjE5IDE2LjU3IDE3LjgzQzIyLjA5IDE4LjQ4IDIyLjI5IDE5LjM2IDIyLjEyIDIwLjE4QzIxLjk2IDIwLjk5IDIxLjQzIDIxLjcgMjAuNjkgMjIuMTFDMTkuOTUgMjIuNTEgMTkuMDQgMjIuNTcgMjIuMjMgMjIuMjdDMTcuNDEgMjEuOTcgMTYuODEgMjEuMyAxNi42IDE5LjQ3QzE2LjM5IDE5LjA0IDE2LjQyIDE4LjU3IDE2LjU1IDE4LjE0QzE2LjY5IDE3LjcxIDE2Ljk0IDE3LjMzIDE3LjI2IDE3LjAzQzE3LjkgMTYuNDMgMTguNzggMTYuMTMgMTkuNjYgMTYuMjRDMjAuNTMgMTYuMzUgMjEuMzQgMTYuODcgMjEuNzYgMTcuNjNDMjIuMTggMTguMzggMjIuMiAxOS4zIDIxLjgzIDIwLjA3QzIxLjQ1IDIwLjg0IDIwLjcxIDIxLjQxIDE5Ljg0IDIxLjZDMTguOTggMjEuNzggMTguMDQgMjEuNTYgMTcuMzYgMjAuOTlDMTYuNjcgMjAuNDMgMTYuMjggMTkuNTcgMjYuMzUgMTguN0MxNi40MSAxNy44NCAxNi45IDE3LjIyIDE3LjgzIDE3LjY1QzIyLjQuMSAyMi40NyAxOC43NyAyMi41IDE5LjcxQzIyLjUzIDIwLjE2IDIyLjQ3IDIwLjYyIDIyLjMzIDIxLjA1QzIyLjIgMjEuNDggMjEuOTggMjEuODYgMjEuNjkgMTguMTdDMjEuMDkgMjIuODEgMjAuMjEgMjMuMTMgMjkuMjggMjIuOTlDMTguMzYgMjIuODYgMTcuNDYgMjIuNDUgMTYuODUgMjEuNzJDMTYuMjQgMjEgMTUuOTcgMjAuMDQgMTYuMSAxOS4xQzE2LjIzIDE4LjE3IDE2Ljc0IDE3LjMxIDE3LjUyIDE2Ljc2QzE4LjI5IDE2LjIxIDE5LjMyIDE1LjkzIDIwLjI3IDE2LjE1QzIxLjIyIDE2LjM3IDIyLjA3IDE3LjA5IDIyLjM5IDE4QzIyLjc0IDE4Ljk5IDIyLjUxIDIwLjExIDIxLjgyIDIwLjg2QzIxLjEyIDIxLjYxIDIwLjA0IDIxLjkyIDE5LjA0IDE5Ljc1QzE4LjA0IDE2LjU3IDE3LjM3IDE2LjI1IDIwLjg0IDE3Ljk5QzE2LjMzIDE3LjQyIDE2LjA5IDE3LjE3IDE2LjAgMTcuMDRDMTUuNTQgMTYuOTIgMTUuMTYgMTYuOTIgMTQuODQgMTcuMDRDMTQuNTIgMTcuMTcgMTQuMjYgMTcuNDIgMTQuMTQgMTcuNzVDMTQuMDMgMTguMDggMTQuMDYgMTguNDYgMTQuMjQgMTguNzdDMTQuNDMgMTkuMDggMTQuNzQgMTkuMzEgMTUuMTIgMTkuNDFDMTUuNyAxOS41OCAxNi40IDE5LjQxIDE2Ljg1IDEyLjk2QzE3LjMgMTIuNTEgMTcuNDggMTEuODUgMTcuMzUgMTEuMjdDMTcuMjEgMTAuNjkgMTYuNzggMTAuMjQgMTYuMTggMTAuMUMxNS41OSA5Ljk2IDE0Ljk1IDEwLjE0IDE0LjUxIDEwLjU5QzE0LjA3IDExLjAzIDEzLjg5IDExLjY4IDE0LjAyIDEyLjI2QzE0LjE1IDEyLjg0IDE0LjU5IDEzLjI5IDE1LjE4IDE5LjQ0QzE1Ljc4IDE5LjU4IDE2LjQyIDE5LjQgMTYuODYgMTguOTZDMTcuMyAxOC41MyAxNy40OCAxNy44OCAxNy4zNSAxNy4zQzE3LjIyIDE2LjcyIDE2Ljc4IDE2LjI3IDE2LjE5IDE2LjEzQzE1LjM2IDE2LjkzIDE0LjgzIDEzLjk5IDE0LjY0IDE0Ljc5QzE0LjQ0IDE1LjU5IDE0LjcgMTYuNDYgMTUuMzEgMTcuMDdDMTUuOTEgMTcuNjcgMTYuNzkgMTcuOTQgMTcuNTkgMTcuNzVDMTguMzkgMTcuNTUgMTkuMDMgMTYuOTUgMTkuMjEgMTYuMTdDMTkuNDcgMTQuOTggMTguODIgMTMuNzIgMTcuNjcgMTMuMTdDMTYuNTMgMTIuNjEgMTUuMSAxMi44NCAxNC4yNSAxMy43MkMxMy4zOSAxNC41OSAxMy4yMSAxNi4wNiAxMy44NSAxNy4yQzE0LjMgMTcuOTcgMTUuMTQgMTguNTEgMTYuMDcgMTguNjFDMTcgMTguNzEgMTcuOTUgMTguMzcgMTguNjUgMTcuNzFDMTkuMDcgMTcuMzEgMTkuMzYgMTYuNzggMTkuNDYgMTYuMkMxOS42MyAxNS4yOSAxOS40MiAxNCA4LjkzIDE0LjkyQzE4LjQzIDE1Ljg1IDE3LjY5IDE2Ljk4IDE2LjgzIDE3LjgyQzE1Ljk4IDE4LjY3IDE0Ljc5IDE5LjExIDEzLjYzIDE4Ljk5QzEyLjQ2IDE4Ljg4IDExLjQgMTguMjEgMTAuNzcgMTcuMjJDOS41NiAxNS40OSA5Ljc5IDEzLjAyIDExLjM0IDExLjU3QzEyLjg5IDEwLjEyIDE1LjMyIDEwLjIgMTYuNzcgMTEuNzVDMTcuNTMgMTIuNiAxNy45MSAxMy43MyAxNy44NyAxNC44NkMxNy44MiAxNS45OSIxNy4zNiAxNy4wOSAxNi41OSAxNy45QzE1LjgyIDE4LjcxIDEzLjI4IDE5LjI0IDM1Ljc1IDE5LjIyQzExLjgyIDE5LjE5IDEwLjYzIDE4LjYyIDkuODQgMTcuNzdDOS4wNSAxNi45MSA4LjY4IDE1Ljc2IDguODMgMTQuNjFDOC45OSAxMy40NyA5LjYzIDEyLjQ1IDEwLjU4IDExLjgxQzEyLjQ4IDEwLjU0IDE1LjAyIDExLjA5IDE2LjMgMTIuOThDMTcuNTcgMTQuODggMTcuMDcgMTcuNDQgMTUuMjQgMTguNzNDMTQuMzQgMTkuMzkgMTMuMjEgMTkuNjYgMTIuMTQgMTkuNDdDMTEuMDcgMTkuMjcgMTAuMTQgMTguNjQgOS41NiAxNy43NEMzLjM4IDE0Ljk1IDkuMDcgMTIuMDggMTAuNDkgMTAuNThDMTEuOSA5LjA4IDE0LjAyIDguNjIgMTUuODcgOS4zOEMxNy43MiAxMC4xNCAxOC45NSAxMS45NiAxOC45OCAxNER6IiBmaWxsPSIjQUYyMTI0Ii8+PC9zdmc+" width="24" alt="OpenAI"><br><small>OpenAI</small></div>
                <div style="text-align: center;"><img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTExLjggMEMxMy4zMSAwIDE0LjcgMC40NiAxNS44NiAxLjM4QzE3LjAyIDIuMyAxNy43NiAzLjY0IDE4LjA2IDUuNEMxOC4zNSA3LjE2IDE4LjA0IDkuMDcgMTcuMTUgMTEuMTNDMTYuMjYgMTMuMTkgMTQuODkgMTUuMDggMTMuMDUgMTYuODFDMTEuMjEgMTguNTQgOS4wNCAxOS44MSA2LjUzIDIwLjYyQzQuMDIgMjEuNDIgMS44MiAyMS4yMSAwIDE5Ljk5QzEuODEgMTkuODIgMy4zMSAxOS4yNCA0LjUgMTguMjdDNS42OSAxNy4yOSA2LjQzIDE2LjE0IDYuNzIgMTQuODFDNS41OCAxNC42OSA0LjYzIDE0LjE0IDMuODcgMTMuMTZDMy4xMSAxMi4xOCAyLjcxIDExLjA3IDIuNjggOS44M0MyLjkyIDEwLjA2IDMuMiAxMC4yMiAzLjUyIDEwLjMyQzMuODQgMTAuNDEgNC4yMSAxMC40MiA0LjY0IDEwLjM1QzMuNTggOS45MyAyLjc4IDkuMjIgMi4yNiA4LjIzQzEuNzMgNy4yMyAxLjU3IDYuMiAxLjc3IDUuMTRDMS45NyA0LjA4IDIuNDcgMy4wNyAzLjI5IDIuMTFDNC40MiAzLjUyIDUuNzQgNC42OSA3LjI0IDUuNjFDOC43NSA2LjUzIDEwLjM5IDcuMDcgMTIuMTQgNy4yMkMxMi4xIDYuOTIgMTIuMDcgNi42NiAxMi4wNyA2LjQ1QzEyLjA3IDYuMjQgMTIuMDcgNi4wMiAxMi4wNyA1LjhDMTIuMDcgMi45NyAxMy42NSAxLjA2IDE2LjggMC4wN0MxNi43NiAwLjA4IDE2Ljg0IDAuMDYgMTcuMDIgMC4wMkMxNy4xNyAwIDE3LjMxIDAgMTcuNDUgMEgxOC4wNkwxOC4zIDkuMDFDMTguMzYgMC4wMiAxOC40NyAwLjAyIDE4LjYzIDAuMDFMMTguNzcgMEgxOS4zOEMxOS41MyAwIDE5LjY3IDAgMTkuODEgMC4wMkMxOS45NiAwLjAzIDIwLjA1IDAuMDYgMjAuMDggMC4wN0MyMy4yMyAxLjA2IDI0LjgxIDIuOTcgMjQuODEgNS44QzI0LjgxIDYuMDIgMjQuODEgNi4yNCAyNC44MSA2LjQ1QzI0LjgxIDYuNjYgMjQuNzggNi45MiAyNC43NCA3LjIyQzI2LjQ5IDcuMDcgMjguMTMgNi41MyAyOS42NCA1LjYxQzMxLjE0IDQuNjkgMzIuNDUgMy41MiAzMy41OSAyLjExQzM0LjQgMy4wNyAzNC45MSA0LjA4IDM1LjExIDUuMTRDMzUuMzEgNi4yIDM1LjE1IDcuMjMgMzQuNjIgOC4yM0MzNC4xIDkuMjIgMzMuMyA5LjkzIDMyLjI0IDEwLjM1QzMyLjY3IDEwLjQyIDMzLjA0IDEwLjQxIDMzLjM2IDEwLjMyQzMzLjY4IDEwLjIyIDMzLjk2IDEwLjA2IDM0LjIgOS44M0MzNC4xNyAxMS4wNyAzMy43NyAxMi4xOCAzMy4wMSAxMy4xNkMzMi4yNSAxNC4xNCAzMS4zIDE0LjY5IDMwLjE1IDE0LjgxQzMwLjQ0IDE2LjE0IDMxLjE4IDE3LjI5IDMyLjM4IDE4LjI3QzMzLjU3IDE5LjI0IDM1LjA3IDE5LjgyIDM2Ljg4IDE5Ljk5QzM1LjA1IDIxLjIxIDMyLjg2IDIxLjQyIDMwLjM1IDIwLjYyQzI3Ljg0IDE5LjgxIDI1LjY3IDE4LjU0IDIzLjgzIDE2LjgxQzIxLjk5IDE1LjA4IDIwLjYxIDEzLjE5IDE5LjczIDExLjEzQzE4Ljg0IDkuMDcgMTguNTQgNy4xNiAxOC44MyA1LjRDMTkuMTIgMy42NCAxOS44NyAyLjMgMjEuMDIgMS4zOEMyMi4xOCAwLjQ2IDIzLjU3IDAgMjUuMDggMEgxMS44WiIgZmlsbD0iI0I5OTJGQiIvPjwvc3ZnPg==" width="24" alt="Claude"><br><small>Claude</small></div>
                <div style="text-align: center;"><img src="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEyIDI0QzUuMzc1IDI0IDAgMTguNjI1IDAgMTJTNS4zNzUgMCAxMiAwIDE1IDUuMzc1IDI0IDEycy01LjM3NSAxMi0xMiAxMlptMC0yMy4wNjJDNS44OTEgMC45MzggMC45MzggNS44OTEgMC45MzggMTJjMCA2LjEwOSA0Ljk1MyAxMS4wNjIgMTEuMDYyIDExLjA2MiA2LjEwOSAwIDExLjA2Mi00Ljk1MyAxMS4wNjItMTEuMDYyIDAtNi4xMDktNC45NTMtMTEuMDYyLTExLjA2Mi0xMS4wNjJaIiBmaWxsPSIjQjJBQ0I2Ii8+PHBhdGggZD0iTTEwLjI2NiAxNy43MTlsMi4yMDMgMi4wNjItNi40MyA0LjVjLTAuMDg0IDAtMC4wMDggMC0wLjE0NC0wLjA4M2E0LjY5MSA0LjY5MSAwIDAgMS0wLjA3OC0wLjEwNCAxOC4yOTcgMTguMjk3IDAgMCAxLTAuMTExLTAuMTYzIDE1LjUzMSAxNS41MzEgMCAwIDEtMC4yNTItMC4zOTVjNy4wMzEtNjAuMDg4LTMuMDcgMTUuNzM0LTYuMTQxLTUuODE2Wk0yMS41IDQuNWwtMy4xNDEgMy4wOTQgMC42NTYgMC42NTYgMi40ODQtMi4yNWMtNy4wMzEgNi4wODctMi45MyAxNS43MzQtNi42MDkgNS44MTZsMC4wOTYtMC4xOTJjMC4wMzItMC4wNjIgMC4wNjItMC4xMjUgMC4wOTEtMC4xODggMC4wNTEtMC4xMDcgMC4xMDItMC4yMTUgMC4xNDktMC4zMjJsMy4wOTQtMy4wOTRzMi40MzgtMi4zNCAzLjE4LTMuNTJaTTMuMjgxIDEwLjk2OWMwLjA2NS0wLjAxIDAuMTI5LTAuMDE5IDAuMTk0LTAuMDI4IDAuMDQ5LTAuMDA3IDAuMDk4LTAuMDE0IDAuMTQ4LTAuMDIyQy01Ljc5NyA4LjA5OSAyLjI1OS0wLjM0OCAxMC44MjgtMC4wNzEiIGZpbGw9IiNGRkQzNEUiLz48cGF0aCBkPSJNMTAuODI4LTAuMDcxYzguOTM4LTAuMjc0IDE3LjI3NiA3LjU3OCAxNi4wODYgOS45MzlhNS4xNjggNS4xNjggMCAwIDEtMC4xNDYgMC4wMjJjLTAuMDY4IDAuMDEtMC4xMzcgMC4wMTktMC4yMDYgMC4wMjkiIGZpbGw9IiMwOEE0RDkiLz48cGF0aCBkPSJNMzIuMjA3IDE3LjJjLTIuNzUzIDEuNDE1LTE1LjkzOC0yLjM0NC0xMy45MzguNTE5IDE2LjM5NCAwLjU2MiAxLjg0NyAxNi41OTcgMC4xNDcgOS45MzkgNC4yMTktMTAuMDU2IDYuMzQ0LTguODMgMTMuNzktMTAuNDU4Wk0xMy43MzEgMjQuMDc3Yy0wLjI0NC0wLjAwNC0wLjQ4OC0wLjAwOS0wLjczLTAuMDE0IC0wLjA4MiAwLTAuMTY0LTAuMDAzLTAuMjQ1LTAuMDA1LTAuMTQzLTAuMDAzLTAuMjg2LTAuMDA2LTAuNDI3LTAuMDFjMjAuMjk5LTEwLjYxOS0wLjA0MiA3LjQxNS0zLjE0MSAzLjA5NGwtMC42LTAuNTYzTDExLjYwOSAyNGMwLjcwOSAwIDEuNDE2LTAuMDQzIDIuMTIyLTAuMTIyWiIgZmlsbD0iI0ZGOEMzNyIvPjxwYXRoIGQ9Ik0xMC44MjgtMC4wNzFMMTAuMjY2IDBjLTIuODU5LjE4LTUuNjI1IDEuMzQyLTcuNzM0IDMuNDUyQzAuNDA2IDUuNTc4LTAuNzU1IDguNDM0LTAuOTM4IDExLjNsLTAuMDcxIDAuODQ0YzAuMTQ3IDAuOTM4IDQuMDg2IDEuMDAzIDMuNjMzLTEuMjA0LjE0OCAwLjAyMiAwLjI5NiAwLjA0NyAwLjQ0NCAwLjA3M2gwLjAxNWMwLjA3NCAwLjAxMyAwLjE0OCAwLjAyNiAwLjIyMyAwLjA0IiBmaWxsPSIjNzVERkhCIi8+PC9zdmc+" width="24" alt="Perplexity"><br><small>Perplexity</small></div>
            </div>
            """
            , unsafe_allow_html=True)
            
            model_options = [
                # Gemini models with their specific versions and exact call signs
                "Gemini - 2.5 Pro (gemini-2.5-pro-preview-03-25)",
                "Gemini - 2.0 Flash (gemini-2.0-flash-001)",
                "Gemini - 2.0 Flash-Lite (gemini-2.0-flash-lite-001)",
                "Gemini - 1.5 Pro (gemini-1.5-pro-001)",
                "Gemini - 1.5 Flash (gemini-1.5-flash-001)",
                "Gemini - 1.5 Flash-8B (gemini-1.5-flash-8b-001)",
                
                # Gemini Live API models
                "Gemini - 2.0 Flash Live (gemini-2.0-flash-live-preview-04-09)",
                
                # Vertex AI models
                "Vertex AI - Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)",
                "Vertex AI - Claude 3 Opus (claude-3-opus-20240229)",
                "Vertex AI - GPT-4o (gpt-4o)",
                
                # Direct API models
                "OpenAI - GPT-4o (gpt-4o)",
                "Anthropic - Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)",
                "Anthropic - Claude 3 Opus (claude-3-opus-20240229)",
                
                # Perplexity models
                "Perplexity - 70B Online (pplx-70b-online)",
                "Perplexity - 7B Online (pplx-7b-online)",
                "Perplexity - 70B Chat (pplx-70b-chat)"
            ]
            
            # Find the closest match in model_options for current_model
            current_index = 0
            if st.session_state.current_model:
                for i, option in enumerate(model_options):
                    if st.session_state.current_model in option:
                        current_index = i
                        break
            
            selected_model = st.selectbox(
                "Select AI model",
                options=model_options,
                index=current_index,
                label_visibility="collapsed",
                key="model_selector"
            )
            
            if selected_model != st.session_state.current_model:
                # Model changed - attempt to load most recent chat for this model
                chat_id, messages = get_most_recent_chat(st.session_state.user, selected_model)
                
                # Update session state with new model
                st.session_state.current_model = selected_model
                
                # Update chat_id in session state
                st.session_state.chat_id = chat_id
                
                # Update messages if found for this model
                if messages:
                    st.session_state.messages = messages
                    st.info(f"Loaded most recent {selected_model} chat")
                else:
                    # If no chat exists for this model, start a new one
                    st.session_state.messages = []
                    st.info(f"Started a new {selected_model} chat")
                
                # Clear uploaded image when switching models
                st.session_state.uploaded_image = None
                
                # Force a rerun to refresh the chat
                st.rerun()
            
            # Model settings based on selection with enhanced UI
            st.markdown("""
            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #333;">
                <p style="font-weight: 500; margin-bottom: 5px; color: #4285f4;">Response Settings</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show temperature control for all models except Claude/Anthropic which have fixed settings
            if "anthropic" not in st.session_state.current_model.lower():
                st.write("Temperature")
                
                # Create two columns for min/max labels
                temp_label_cols = st.columns([1, 1])
                with temp_label_cols[0]:
                    st.markdown("<p style='color: #888; font-size: 0.8rem; margin: 0;'>Precise</p>", unsafe_allow_html=True)
                with temp_label_cols[1]:
                    st.markdown("<p style='color: #888; font-size: 0.8rem; text-align: right; margin: 0;'>Creative</p>", unsafe_allow_html=True)
                
                temperature = st.slider(
                    "Select temperature", 
                    0.0, 1.0, 
                    st.session_state.temperature, 
                    0.1, 
                    label_visibility="collapsed"
                )
                if temperature != st.session_state.temperature:
                    st.session_state.temperature = temperature
                
                # Additional model options
                st.write("Output tokens")
                max_tokens = st.slider("Max tokens", 100, 1500, 800, 100, label_visibility="collapsed")
                
            # Add New Chat button
            st.markdown("""
            <div style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #333; margin-bottom: 10px;">
                <p style="font-weight: 500; margin-bottom: 5px; color: #4285f4;">Chat Actions</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("New Chat", use_container_width=True):
                # Clear messages but keep other settings
                st.session_state.messages = []
                st.session_state.chat_id = None
                # Visual confirmation
                st.success("Started a new chat!")
                st.rerun()
            
            # Features with toggle buttons styled like Google AI Studio
            st.subheader("Features")
            multi_turn = st.toggle("Multi-turn conversation", value=True)
            
            # Add visual examples of capabilities like in Google AI Studio
            st.subheader("Capabilities")
            capabilities_cols = st.columns(3)
            with capabilities_cols[0]:
                st.markdown("⌨️ Text & Code")
            with capabilities_cols[1]:
                st.markdown("🖼️ Images")
            with capabilities_cols[2]:
                st.markdown("🔊 Audio")
            
            # Current user info
            st.subheader("User")
            st.write(f"Current user: {st.session_state.user}")
            
            # Voice Command UI
            st.markdown("""
            <div style="margin-top: 30px; border-top: 1px solid #333; padding-top: 15px;">
            </div>
            """, unsafe_allow_html=True)
            
            # Render voice command UI with toggle function
            render_voice_command_ui(
                voice_active=st.session_state.voice_commands_active,
                toggle_callback=toggle_voice_commands,
                is_listening=st.session_state.is_listening
            )
            
            # Render floating voice button if active
            if st.session_state.voice_commands_active:
                render_floating_voice_button(st.session_state.is_listening)
            
            # Logout button
            if st.button("Logout", use_container_width=True):
                # Clean up voice processor before logout
                if st.session_state.voice_processor:
                    st.session_state.voice_processor.stop_listening()
                    st.session_state.voice_processor = None
                    st.session_state.is_listening = False
                logout_user()
                st.rerun()
            
            # Load previous conversations with a better filing system
            st.subheader("Chat Library")
            
            # Add search box for filtering conversations
            search_term = st.text_input("Search chats by model or content", key="chat_search")
            
            # Get all conversations
            previous_conversations = load_conversations(st.session_state.user)
            
            if previous_conversations:
                # Group conversations by model
                model_groups = {}
                for convo in previous_conversations:
                    model = convo.get("model", "Unknown model")
                    if model not in model_groups:
                        model_groups[model] = []
                    model_groups[model].append(convo)
                
                # Display groups in expandable sections
                for model, convos in model_groups.items():
                    # Skip if search term is provided and not found in model name
                    if search_term and search_term.lower() not in model.lower():
                        # Try to search in conversation content
                        found_content = False
                        for convo in convos:
                            messages = convo.get("messages", [])
                            for msg in messages:
                                if search_term.lower() in msg.get("content", "").lower():
                                    found_content = True
                                    break
                            if found_content:
                                break
                        if not found_content:
                            continue
                    
                    with st.expander(f"{model} ({len(convos)} chats)", expanded=False):
                        # Sort conversations by date
                        sorted_convos = sorted(
                            convos, 
                            key=lambda x: x.get("last_updated", x.get("timestamp", "1900-01-01")),
                            reverse=True
                        )
                        
                        for idx, convo in enumerate(sorted_convos):
                            timestamp = convo.get("last_updated", convo.get("timestamp", "Unknown date"))
                            chat_id = convo.get("id")
                            
                            # Format timestamp for better readability
                            try:
                                datetime_obj = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                                formatted_time = datetime_obj.strftime("%m/%d %H:%M")
                            except:
                                formatted_time = timestamp
                            
                            # Get a preview of the last message for context
                            messages = convo.get("messages", [])
                            preview = ""
                            if messages:
                                last_msg = messages[-1].get("content", "")
                                preview = last_msg[:30] + "..." if len(last_msg) > 30 else last_msg
                            
                            # Display the timestamp and preview on the same line (no nested columns)
                            st.write(f"**{formatted_time}** - _{preview}_")
                            
                            if st.button(f"Load Chat", key=f"convo_{model}_{idx}"):
                                # Load this conversation
                                st.session_state.messages = convo.get("messages", [])
                                st.session_state.current_model = model
                                st.session_state.chat_id = chat_id  # Store the chat ID for future updates
                                st.success(f"Loaded chat from {formatted_time}")
                                st.rerun()
                            
                            if idx < len(sorted_convos) - 1:
                                st.markdown("---")
            else:
                st.write("No previous conversations found")
                
            # Footer info with Google AI Studio style
            st.markdown("---")
            st.markdown("AI Chat Studio | 2024")

# Run the app
# Clean up function for voice commands when the app exits
def cleanup_on_exit():
    """Clean up resources when the app exits"""
    # Stop voice processor if running
    if hasattr(st.session_state, 'voice_processor') and st.session_state.voice_processor:
        try:
            st.session_state.voice_processor.stop_listening()
            print("Stopped voice command processor")
        except:
            pass
    
    # Clean up any temporary audio files
    if hasattr(st.session_state, 'audio_path') and st.session_state.audio_path:
        try:
            from utils.audio import cleanup_audio_file
            cleanup_audio_file(st.session_state.audio_path)
        except:
            pass

if __name__ == "__main__":
    try:
        main()
    finally:
        # Execute cleanup when the app exits
        cleanup_on_exit()

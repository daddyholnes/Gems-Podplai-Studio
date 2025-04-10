"""
Gemini API implementation for AI Chat Studio.
Supports multimodal inputs (text, images, audio) and streaming responses.
"""
import os
import base64
from typing import List, Dict, Any, Generator, Optional
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import streamlit as st

# Constants
DEFAULT_MODEL = "gemini-1.5-pro"
DEFAULT_TEMPERATURE = 0.7

def initialize_gemini():
    """
    Initialize the Gemini API with the provided API key.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("Gemini API key not found. Please add it to your environment variables.")
        return False
    
    try:
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        st.error(f"Failed to initialize Gemini API: {str(e)}")
        return False

def get_gemini_models() -> List[Dict[str, Any]]:
    """
    Get available Gemini models.
    
    Returns:
        List of model information dictionaries
    """
    try:
        models = genai.list_models()
        gemini_models = [m for m in models if "gemini" in m.name.lower()]
        return gemini_models
    except Exception as e:
        st.error(f"Error fetching Gemini models: {str(e)}")
        return []

def prepare_content_parts(
    prompt: str, 
    image_data: Optional[str] = None, 
    audio_data: Optional[str] = None,
    screen_data: Optional[str] = None
) -> List[Any]:
    """
    Prepare content parts for a Gemini model request.
    
    Args:
        prompt: User's text input
        image_data: Base64-encoded image data
        audio_data: Base64-encoded audio data
        screen_data: Base64-encoded screenshot data
        
    Returns:
        List of content parts
    """
    content_parts = []
    
    # Add image if provided
    if image_data:
        try:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
            content_parts.append(image)
        except Exception as e:
            st.error(f"Error processing image: {str(e)}")
    
    # Add screenshot if provided and different from image_data
    if screen_data and screen_data != image_data:
        try:
            screen_bytes = base64.b64decode(screen_data)
            screen = Image.open(BytesIO(screen_bytes))
            content_parts.append(screen)
        except Exception as e:
            st.error(f"Error processing screenshot: {str(e)}")
    
    # Add audio if provided (Gemini handles audio via similar mechanism as images)
    if audio_data:
        try:
            audio_bytes = base64.b64decode(audio_data)
            content_parts.append({"mime_type": "audio/mp3", "data": audio_bytes})
        except Exception as e:
            st.error(f"Error processing audio: {str(e)}")
    
    # Add text prompt
    content_parts.append(prompt)
    
    return content_parts

def prepare_chat_history(conversation_history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert app conversation history to Gemini format.
    
    Args:
        conversation_history: List of message dictionaries
        
    Returns:
        List of formatted message dictionaries for Gemini
    """
    chat_history = []
    
    for msg in conversation_history:
        role = "user" if msg["role"] == "user" else "model"
        
        # Handle simple text messages
        if isinstance(msg["content"], str):
            chat_history.append({"role": role, "parts": [msg["content"]]})
        # Handle multimodal messages
        elif isinstance(msg["content"], list):
            parts = []
            for part in msg["content"]:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and "type" in part:
                    if part["type"] == "image" and "data" in part:
                        try:
                            image_bytes = base64.b64decode(part["data"])
                            image = Image.open(BytesIO(image_bytes))
                            parts.append(image)
                        except Exception as e:
                            st.error(f"Error processing image in history: {str(e)}")
                    elif part["type"] == "audio" and "data" in part:
                        try:
                            audio_bytes = base64.b64decode(part["data"])
                            parts.append({"mime_type": "audio/mp3", "data": audio_bytes})
                        except Exception as e:
                            st.error(f"Error processing audio in history: {str(e)}")
            
            chat_history.append({"role": role, "parts": parts})
    
    return chat_history

def get_gemini_response(
    prompt: str, 
    conversation_history: List[Dict[str, Any]], 
    image_data: Optional[str] = None, 
    audio_data: Optional[str] = None, 
    screen_data: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE, 
    model_name: str = DEFAULT_MODEL
) -> str:
    """
    Get a response from the Gemini model with multimodal inputs.
    
    Args:
        prompt: User's text input
        conversation_history: List of message dictionaries
        image_data: Base64-encoded image data
        audio_data: Base64-encoded audio data
        screen_data: Base64-encoded screenshot data
        temperature: Temperature for response generation
        model_name: Gemini model version to use
    
    Returns:
        str: AI response text
    """
    try:
        # Select the appropriate model
        model = genai.GenerativeModel(model_name)
        
        # Prepare the content parts
        content_parts = prepare_content_parts(prompt, image_data, audio_data, screen_data)
        
        # Prepare the chat history from conversation history
        chat_history = prepare_chat_history(conversation_history[:-1])  # Exclude the last message (current prompt)
        
        # Start a chat session
        chat = model.start_chat(history=chat_history)
        
        # Generate response
        response = chat.send_message(
            content_parts, 
            generation_config={"temperature": temperature}
        )
        
        return response.text
        
    except Exception as e:
        return f"Error with Gemini model: {str(e)}"

def get_gemini_streaming_response(
    prompt: str, 
    conversation_history: List[Dict[str, Any]], 
    image_data: Optional[str] = None, 
    audio_data: Optional[str] = None, 
    screen_data: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE, 
    model_name: str = DEFAULT_MODEL
) -> Generator[str, None, None]:
    """
    Get a streaming response from Gemini with multimodal inputs.
    
    Args:
        prompt: User's text input
        conversation_history: List of message dictionaries
        image_data: Base64-encoded image data
        audio_data: Base64-encoded audio data
        screen_data: Base64-encoded screenshot data
        temperature: Temperature for response generation
        model_name: Gemini model version to use
        
    Returns:
        Generator yielding response chunks
    """
    try:
        # Select the appropriate model
        model = genai.GenerativeModel(model_name)
        
        # Prepare the content parts
        content_parts = prepare_content_parts(prompt, image_data, audio_data, screen_data)
        
        # Prepare conversation history
        chat_history = prepare_chat_history(conversation_history[:-1])  # Exclude the last message (current prompt)
        
        # Start a chat session
        chat = model.start_chat(history=chat_history)
        
        # Generate streaming response
        response_stream = chat.send_message(
            content_parts, 
            generation_config={"temperature": temperature},
            stream=True
        )
        
        # Yield chunks as they come in
        for chunk in response_stream:
            if chunk.text:
                yield chunk.text
        
    except Exception as e:
        yield f"Error with Gemini streaming: {str(e)}"
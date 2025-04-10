import os
import sys
import requests
import json
from typing import List, Dict, Any

# Gemini API 
def get_gemini_response(prompt: str, message_history: List[Dict[str, str]], image_data=None, audio_data=None, temperature=0.7, model_name="gemini-1.5-pro") -> str:
    """
    Get a response from the Gemini AI model.
    
    Args:
        prompt: The user's input prompt
        message_history: Previous message history
        image_data: Optional base64 encoded image data for multimodal prompts
        audio_data: Optional base64 encoded audio data
        temperature: Temperature for response generation (creativity)
        model_name: The specific Gemini model to use (e.g., "gemini-1.5-pro", "gemini-2.5-pro-preview")
        
    Returns:
        The AI response text
    """
    # Check if this is a live API model (gemini-2.0-flash-live)
    if "live" in model_name:
        # Use the vertex_ai.py implementation
        from utils.vertex_ai import get_vertex_live_response
        return get_vertex_live_response(prompt, message_history, model_name=model_name)
    try:
        import google.generativeai as genai
        import base64
        from PIL import Image
        import io
        
        # Get API key from environment variables
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: Gemini API key not found. Please set the GEMINI_API_KEY environment variable."
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Convert message history to the format expected by Gemini
        formatted_history = []
        for message in message_history:
            # Include all messages in the history, don't exclude the last one
            role = "user" if message["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [message["content"]]})
        
        # Use the provided model_name parameter
        
        # Create a Gemini model instance with generation config
        model = genai.GenerativeModel(
            model_name,
            generation_config={"temperature": temperature}
        )
        
        # If there's an image, we need to handle it differently
        if image_data:
            # Convert base64 to image
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            
            # Create content parts with both text and image
            content = [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
            ]
            
            # Generate response with image input
            response = model.generate_content(content)
            return response.text
        else:
            # Start a chat session with history for text-only conversations
            chat = model.start_chat(history=formatted_history)
            
            # Send the user's message and get a response
            response = chat.send_message(prompt)
            return response.text
            
    except Exception as e:
        return f"Error with Gemini API: {str(e)}"

# Google Vertex AI (Alternative implementation without requiring vertex-ai packages)
def get_vertex_ai_response(prompt: str, message_history: List[Dict[str, str]], project_id=None, location=None, model_type=None, model_name=None) -> str:
    """
    Get a response similar to Vertex AI using Gemini API with advanced parameters.
    This is an alternative implementation that doesn't require Vertex AI libraries.
    
    Args:
        prompt: The user's input prompt
        message_history: Previous message history
        project_id: Not used in this implementation
        location: Not used in this implementation
        model_type: Type of model to use (e.g., "claude", "gpt")
        model_name: Specific model identifier to use (e.g., "claude-3-5-sonnet-20241022")
        
    Returns:
        The AI response text
    """
    try:
        import google.generativeai as genai
        
        # Get API key from environment variables
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: Gemini API key not found. Please set the GEMINI_API_KEY environment variable."
        
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Convert message history to the format expected by Gemini
        formatted_history = []
        for message in message_history:
            # Include all messages in the history, don't exclude the last one
            role = "user" if message["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [message["content"]]})
        
        # Create a Gemini model instance with advanced settings
        # Using more advanced settings to mimic Vertex AI capabilities
        # Use the specified model_name if provided, otherwise fallback to gemini-1.5-pro
        model_version = model_name if model_name else "gemini-1.5-pro"
        model = genai.GenerativeModel(
            model_version,
            generation_config={
                "temperature": 0.4,  # Lower temperature for more factual responses
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 2048,
            },
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        )
        
        # Start a chat session with history
        chat = model.start_chat(history=formatted_history)
        
        # Send the user's message and get a response
        response = chat.send_message(prompt)
        
        return response.text
    except Exception as e:
        return f"Error with Vertex AI alternative: {str(e)}"

# OpenAI API
def get_openai_response(prompt: str, message_history: List[Dict[str, str]], model_name="gpt-4o") -> str:
    """
    Get a response from the OpenAI GPT model.
    
    Args:
        prompt: The user's input prompt
        message_history: Previous message history
        model_name: Specific model identifier to use (e.g., "gpt-4o")
        
    Returns:
        The AI response text
    """
    try:
        from openai import OpenAI
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        # do not change this unless explicitly requested by the user
        
        # Get API key from environment variables
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return "Error: OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Format the conversation history for OpenAI
        formatted_messages = []
        for message in message_history:
            formatted_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        # Call the OpenAI API with the specified model
        response = client.chat.completions.create(
            model=model_name,  # Use the provided model_name
            messages=formatted_messages,
            max_tokens=800
        )
        
        return response.choices[0].message.content
    except Exception as e:
        return f"Error with OpenAI API: {str(e)}"

# Anthropic API
def get_anthropic_response(prompt: str, message_history: List[Dict[str, str]], model_name="claude-3-5-sonnet-20241022") -> str:
    """
    Get a response from the Anthropic Claude model.
    
    Args:
        prompt: The user's input prompt
        message_history: Previous message history
        model_name: Specific model identifier to use (e.g., "claude-3-5-sonnet-20241022")
        
    Returns:
        The AI response text
    """
    try:
        from anthropic import Anthropic
        
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
        
        # Get API key from environment variables
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return "Error: Anthropic API key not found. Please set the ANTHROPIC_API_KEY environment variable."
        
        # Initialize Anthropic client
        client = Anthropic(api_key=api_key)
        
        # Format message history for Anthropic
        formatted_messages = []
        for message in message_history:
            role = "user" if message["role"] == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": message["content"]
            })
        
        # Call the Anthropic API with the specified model
        response = client.messages.create(
            model=model_name,  # Use the provided model_name
            messages=formatted_messages,
            max_tokens=1000
        )
        
        return response.content[0].text
    except Exception as e:
        return f"Error with Anthropic API: {str(e)}"

# Perplexity API
def get_perplexity_response(prompt: str, message_history: List[Dict[str, str]], temperature=0.2, model_name=None) -> str:
    """
    Get a response from the Perplexity API.
    
    Args:
        prompt: The user's input prompt
        message_history: Previous message history
        temperature: Temperature value (0.0 to 1.0) that controls randomness
        model_name: Specific model identifier to use (e.g., "pplx-70b-online")
        
    Returns:
        The AI response text
    """
    try:
        # Get API key from environment variables
        api_key = os.environ.get("PERPLEXITY_API_KEY")
        if not api_key:
            return "Error: Perplexity API key not found. Please set the PERPLEXITY_API_KEY environment variable."
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Format all messages for Perplexity
        formatted_messages = []
        
        # Add a system message for better performance
        formatted_messages.append({
            "role": "system",
            "content": "You are a helpful, accurate AI assistant. Provide detailed and informative responses."
        })
        
        # Add chat history
        for message in message_history:
            role = "user" if message["role"] == "user" else "assistant"
            formatted_messages.append({
                "role": role,
                "content": message["content"]
            })
        
        # Use the specified model if provided, otherwise use fallback mechanism
        if model_name:
            models_to_try = [model_name]
        else:
            # List of models to try in order (fallback mechanism)
            models_to_try = ["pplx-70b-online", "pplx-7b-online", "pplx-70b-chat", "pplx-7b-chat"]
        
        # Try each model in sequence until one works
        last_error = None
        for model in models_to_try:
            try:
                # Prepare request data with model name and parameters
                data = {
                    "model": model,  # Try each model in sequence
                    "messages": formatted_messages,
                    "max_tokens": 1000,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "stream": False
                }
                
                # Make request to Perplexity API
                response = requests.post(
                    "https://api.perplexity.ai/chat/completions",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                last_error = f"Error from Perplexity API with model {model}: {response.text}"
            except Exception as e:
                last_error = f"Error with Perplexity API using model {model}: {str(e)}"
        
        # If we get here, all models failed
        return f"All Perplexity models failed. Last error: {last_error}"
    except Exception as e:
        return f"General error with Perplexity API: {str(e)}"

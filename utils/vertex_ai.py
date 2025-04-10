"""
Vertex AI integration for models using service account authentication
"""
import os
import json
from google import genai
from google.genai import types
import base64

def initialize_vertex_ai(service_account_path="service-account-key.json"):
    """
    Initialize Vertex AI with service account credentials
    
    Args:
        service_account_path: Path to the service account JSON key file
    """
    # Read service account file
    try:
        with open(service_account_path, 'r') as f:
            service_account_info = json.load(f)
            
        # Initialize client with Vertex AI and project details
        client = genai.Client(
            vertexai=True,
            project=service_account_info["project_id"],
            location="us-central1",
        )
        return client
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
        return None

def get_vertex_gemini_response(prompt: str, message_history: list, temperature=0.7, model_name="gemini-2.5-pro-preview-03-25", image_data=None):
    """
    Get response from Gemini model using Vertex AI
    
    Args:
        prompt: User's text prompt
        message_history: Previous conversation history
        temperature: Generation temperature (0.0-1.0)
        model_name: Specific Gemini model name
        image_data: Optional base64 encoded image
        
    Returns:
        Generated response text
    """
    try:
        client = initialize_vertex_ai()
        if not client:
            return "Error initializing Vertex AI client"
        
        # Format conversation history for Vertex AI
        contents = []
        
        # Add conversation history
        for msg in message_history:
            if msg["role"] == "user":
                # For user messages
                parts = [types.Part.from_text(text=msg["content"])]
                
                # Add image if it exists in this message
                if "image" in msg and msg["image"]:
                    image_bytes = base64.b64decode(msg["image"])
                    parts.append(types.Part.from_data(data=image_bytes, mime_type="image/jpeg"))
                    
                contents.append(types.Content(role="user", parts=parts))
            else:
                # For assistant messages
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
        
        # Add current prompt
        parts = [types.Part.from_text(text=prompt)]
        
        # Add image data if provided
        if image_data:
            image_bytes = base64.b64decode(image_data)
            parts.append(types.Part.from_data(data=image_bytes, mime_type="image/jpeg"))
            
        contents.append(types.Content(role="user", parts=parts))
        
        # Configure generation parameters
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=0.8,
            max_output_tokens=1024,
            response_modalities=["TEXT"],
        )
        
        # Generate content
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            generation_config=generate_content_config
        )
        
        # Extract and return text response
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            return response.candidates[0].content.parts[0].text
        else:
            return "No response generated"
    
    except Exception as e:
        return f"Error with Vertex AI Gemini model: {str(e)}"

def get_vertex_live_response(prompt: str, message_history: list, model_name="gemini-2.0-flash-live-preview-04-09"):
    """
    Get response from Gemini model using Vertex AI Live API
    
    Args:
        prompt: User's text prompt
        message_history: Previous conversation history
        model_name: Specific Gemini model name
        
    Returns:
        Generated response text
    """
    try:
        client = initialize_vertex_ai()
        if not client:
            return "Error initializing Vertex AI client"
        
        # Format conversation history for Vertex AI
        contents = []
        
        # Add conversation history
        for msg in message_history:
            if msg["role"] == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
            else:
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=msg["content"])]
                ))
        
        # Add current prompt
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)]
        ))
        
        # Generate content with streaming for live API
        response_parts = []
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            generation_config=types.GenerateContentConfig(
                temperature=0.7,
                top_p=0.8,
                max_output_tokens=1024,
                response_modalities=["TEXT"],
            )
        ):
            # Collect text chunks
            if chunk.candidates:
                for part in chunk.candidates[0].content.parts:
                    if part.text:
                        response_parts.append(part.text)
        
        # Combine all parts into full response
        return "".join(response_parts)
    
    except Exception as e:
        return f"Error with Vertex AI Gemini Live model: {str(e)}"
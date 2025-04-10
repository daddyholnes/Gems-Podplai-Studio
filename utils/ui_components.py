"""
UI components for the AI Chat Studio
"""
import streamlit as st
from typing import Dict, Any, List, Optional, Callable
from utils.voice_commands import get_voice_help_text

def render_voice_command_ui(
    voice_active: bool,
    toggle_callback: Callable,
    is_listening: bool
) -> None:
    """
    Render the voice command UI component
    
    Args:
        voice_active: Whether voice commands are enabled
        toggle_callback: Callback function to toggle voice commands
        is_listening: Whether the app is currently listening for voice commands
    """
    
    # Voice command container with styling
    with st.container():
        st.markdown("""
        <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #333;">
            <p style="font-weight: 500; margin-bottom: 5px; color: #4285f4;">Accessibility</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Voice command toggle
        voice_enabled = st.toggle(
            "Voice Commands", 
            value=voice_active,
            help="Enable voice commands for accessibility"
        )
        
        # If status changed, call the toggle callback
        if voice_enabled != voice_active:
            toggle_callback(voice_enabled)
        
        # Show status indicator and help button when voice commands are enabled
        if voice_enabled:
            # Status indicator with colored dot
            if is_listening:
                st.markdown("""
                <div style="display: flex; align-items: center; margin: 10px 0;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: #4CAF50; margin-right: 10px;"></div>
                    <span style="color: #4CAF50; font-size: 0.9rem;">Listening for commands</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                <div style="display: flex; align-items: center; margin: 10px 0;">
                    <div style="width: 10px; height: 10px; border-radius: 50%; background-color: #FF5252; margin-right: 10px;"></div>
                    <span style="color: #FF5252; font-size: 0.9rem;">Voice commands paused</span>
                </div>
                """, unsafe_allow_html=True)
            
            # Help with available commands
            with st.expander("Available Voice Commands"):
                st.markdown(get_voice_help_text())


def render_floating_voice_button(is_active: bool) -> None:
    """
    Render a floating voice command indicator/button
    
    Args:
        is_active: Whether voice commands are active
    """
    # Define color based on active state
    color = "#4CAF50" if is_active else "#888888"
    
    # Floating button HTML 
    html = f"""
    <style>
    .floating-voice-button {{
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background-color: #1E1E1E;
        display: flex;
        justify-content: center;
        align-items: center;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        z-index: 9999;
        cursor: pointer;
        border: 2px solid {color};
    }}
    
    .mic-icon {{
        width: 24px;
        height: 24px;
        fill: {color};
    }}
    
    @keyframes pulse {{
        0% {{ transform: scale(1); }}
        50% {{ transform: scale(1.1); }}
        100% {{ transform: scale(1); }}
    }}
    
    .pulse {{
        animation: pulse 1.5s infinite;
    }}
    </style>
    
    <div class="floating-voice-button {('pulse' if is_active else '')}">
        <svg class="mic-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
    </div>
    """
    
    # Render the floating button
    st.markdown(html, unsafe_allow_html=True)


def create_tooltip_html(message: str, position: str = "top") -> str:
    """
    Create HTML for a tooltip
    
    Args:
        message: The tooltip message
        position: Tooltip position (top, bottom, left, right)
        
    Returns:
        HTML string for the tooltip
    """
    return f"""
    <div class="tooltip">
        <span class="tooltiptext tooltip-{position}">{message}</span>
    </div>
    """
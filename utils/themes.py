"""
Color themes for AI Chat Studio
"""
import streamlit as st

# Available themes
THEMES = {
    "Default Blue": {
        "primary": "#4285F4",
        "background": "#0E1117",
        "secondary_bg": "#1E1E1E",
        "text": "#FFFFFF",
        "accent": "#4285F4",
        "header_color": "#4285F4",
        "message_user_bg": "#303030",
        "message_ai_bg": "#1e1e1e",
    },
    "Amazon Q Purple": {
        "primary": "#8c52ff",
        "background": "#121212",
        "secondary_bg": "#1A1A1A",
        "text": "#FFFFFF",
        "accent": "#8c52ff",
        "header_color": "#8c52ff",
        "message_user_bg": "#292929",
        "message_ai_bg": "#1d1d1d",
    },
    "Dark Teal": {
        "primary": "#00BFA5",
        "background": "#0F1419",
        "secondary_bg": "#1A1E23",
        "text": "#E0E0E0",
        "accent": "#00BFA5",
        "header_color": "#00BFA5",
        "message_user_bg": "#2A2E33",
        "message_ai_bg": "#1A1E23",
    },
    "Midnight": {
        "primary": "#BB86FC",
        "background": "#121212",
        "secondary_bg": "#1F1F1F",
        "text": "#E0E0E0",
        "accent": "#BB86FC",
        "header_color": "#BB86FC",
        "message_user_bg": "#2D2D2D",
        "message_ai_bg": "#1F1F1F",
    },
    "Ocean": {
        "primary": "#03A9F4",
        "background": "#102A43",
        "secondary_bg": "#1C3A57",
        "text": "#F0F4F8",
        "accent": "#03A9F4",
        "header_color": "#03A9F4",
        "message_user_bg": "#2B4C6F",
        "message_ai_bg": "#1C3A57",
    }
}

def get_theme(theme_name):
    """Get a specific theme by name, defaulting to Default Blue if not found"""
    return THEMES.get(theme_name, THEMES["Default Blue"])

def apply_theme(theme_name):
    """Apply a theme to the current session"""
    theme = get_theme(theme_name)
    
    # Update the theme in session state
    if "theme" not in st.session_state:
        st.session_state.theme = theme
    else:
        st.session_state.theme = theme
    
    # Generate and apply custom CSS
    css = f"""
    <style>
        /* Main container styling */
        .main {{
            background-color: {theme["background"]};
            color: {theme["text"]};
        }}
        
        /* Chat container styling */
        .chat-container {{
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 10px;
            max-height: 85vh;
            overflow-y: auto;
        }}
        
        /* Make chat messages more visible and expandable */
        .message-container {{
            margin-bottom: 15px;
            border-radius: 8px;
            border: 1px solid #444;
            overflow-y: auto;
            max-height: 600px;
        }}
        
        /* User message styling */
        .user-message {{
            background-color: {theme["message_user_bg"]};
            color: {theme["text"]};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 8px;
            overflow-wrap: break-word;
        }}
        
        /* AI message styling */
        .ai-message {{
            background-color: {theme["message_ai_bg"]};
            color: {theme["text"]};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 8px;
            overflow-wrap: break-word;
        }}
        
        /* Sidebar styling */
        .css-1d391kg {{
            background-color: {theme["secondary_bg"]};
        }}
        
        /* Input box styling */
        .stChatInputContainer {{
            background-color: {theme["secondary_bg"]};
            border-radius: 20px;
            padding: 5px;
        }}
        
        /* Improve scrollable areas */
        [data-testid="stVerticalBlock"] {{
            max-height: 100vh;
        }}
        
        /* Make chat container fill available height */
        .block-container {{
            max-width: 100%;
            padding-top: 2rem;
            padding-bottom: 1rem;
        }}
        
        /* Style expandable message containers */
        .expandable-container {{
            border: 1px solid #444;
            border-radius: 8px;
            margin-bottom: 12px;
        }}
        
        .expandable-header {{
            padding: 10px 15px;
            background-color: {theme["secondary_bg"]};
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            font-weight: 500;
        }}
        
        .expandable-content {{
            padding: 15px;
            border-top: 1px solid #444;
            max-height: 500px;
            overflow-y: auto;
        }}
        
        /* Button styling */
        .stButton > button {{
            background-color: {theme["primary"]};
            color: white;
            border-radius: 4px;
            border: none;
            padding: 8px 16px;
        }}
        
        /* Dropdown styling */
        .stSelectbox > div > div {{
            background-color: {theme["secondary_bg"]};
            color: {theme["text"]};
            border: 1px solid {theme["primary"]};
            border-radius: 4px;
        }}
        
        /* Header styling */
        h1, h2, h3 {{
            color: {theme["text"]};
        }}
        
        /* Accent colors for headings */
        .accent-text {{
            color: {theme["accent"]};
        }}
        
        /* Basic chat styling - keep it simple but effective */
        .stChatMessage {{
            margin-bottom: 10px;
        }}
        
        /* Chat input container */
        .stChatInputContainer {{
            border-top: 1px solid #444;
            padding-top: 15px;
        }}
    </style>
    """
    
    return css
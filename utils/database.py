import streamlit as st
import os
import datetime
import json
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
import uuid

# Helper function to get the database URL from environment variables
def get_db_url() -> Optional[str]:
    """Get the PostgreSQL connection string from environment variables."""
    return os.environ.get("POSTGRESQL_URL") or os.environ.get("DATABASE_URL")

def init_db() -> None:
    """
    Initialize database connection.
    If PostgreSQL connection is available via environment variable,
    it will use that. Otherwise, it falls back to JSON file storage.
    """
    # Initialize session state variables for chat persistence
    if "chat_id" not in st.session_state:
        st.session_state.chat_id = None
    
    # Get database URL from helper function
    db_url = get_db_url()
    
    if db_url and "db_initialized" not in st.session_state:
        try:
            # Try to connect to PostgreSQL
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Check if the table exists first to avoid sequence conflicts
            cursor.execute("SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations')")
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                # Create table with updated schema if it doesn't exist
                cursor.execute('''
                    CREATE TABLE conversations (
                        id SERIAL PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        model TEXT NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        last_updated TIMESTAMP NOT NULL,
                        messages JSONB NOT NULL
                    )
                ''')
            
            # Check if last_updated column exists, add it if not
            try:
                cursor.execute("""
                    ALTER TABLE conversations 
                    ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP;
                """)
                
                # Update any NULL last_updated values to match timestamp
                cursor.execute("""
                    UPDATE conversations 
                    SET last_updated = timestamp 
                    WHERE last_updated IS NULL;
                """)
            except Exception as column_e:
                st.warning(f"Note: Unable to modify table schema: {str(column_e)}")
            
            conn.commit()
            conn.close()
            
            st.session_state.db_type = "postgresql"
            st.session_state.db_initialized = True
            st.success("PostgreSQL database connected successfully!")
        except Exception as e:
            # If connecting to PostgreSQL fails, fall back to JSON file storage
            st.session_state.db_type = "json"
            st.session_state.db_initialized = True
            st.warning(f"Database connection failed: {str(e)}. Using local JSON storage instead.")
            # Create data directory if it doesn't exist
            os.makedirs("data", exist_ok=True)
    else:
        # Default to JSON file storage
        st.session_state.db_type = "json"
        st.session_state.db_initialized = True
        if not db_url:
            st.warning("No PostgreSQL connection string found. Using local JSON storage.")
        # Create data directory if it doesn't exist
        os.makedirs("data", exist_ok=True)

def save_conversation(username: str, model: str, messages: List[Dict[str, str]]) -> None:
    """
    Save the current conversation to the database.
    If chat_id exists in session state, update that conversation.
    Otherwise, create a new conversation.
    
    Args:
        username: The user's username
        model: The AI model used for the conversation
        messages: The list of message objects in the conversation
    """
    # Current timestamp
    now = datetime.datetime.now()
    
    if st.session_state.db_type == "postgresql":
        try:
            # Connect to PostgreSQL using helper function
            db_url = get_db_url()
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Check if we're updating an existing conversation or creating a new one
            if st.session_state.chat_id:
                # Update existing conversation
                cursor.execute(
                    """
                    UPDATE conversations 
                    SET messages = %s, last_updated = %s
                    WHERE id = %s AND user_id = %s
                    """,
                    (json.dumps(messages), now, st.session_state.chat_id, username)
                )
            else:
                # Insert new conversation
                cursor.execute(
                    """
                    INSERT INTO conversations 
                    (user_id, model, timestamp, last_updated, messages) 
                    VALUES (%s, %s, %s, %s, %s) 
                    RETURNING id
                    """,
                    (username, model, now, now, json.dumps(messages))
                )
                
                # Get the new conversation ID and store it in session state
                chat_id = cursor.fetchone()[0]
                st.session_state.chat_id = chat_id
            
            conn.commit()
            conn.close()
        except Exception as e:
            # If PostgreSQL fails, fall back to JSON
            _save_to_json(username, model, messages)
    else:
        # Save to JSON file
        _save_to_json(username, model, messages)

def _save_to_json(username: str, model: str, messages: List[Dict[str, str]]) -> None:
    """
    Save conversation to a JSON file.
    
    Args:
        username: The user's username
        model: The AI model used
        messages: The list of messages
    """
    # Create a unique filename for this user
    filename = f"data/{username}_conversations.json"
    
    # Current time as formatted string
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Read existing conversations or create new list
    try:
        conversations = []
        if os.path.exists(filename):
            with open(filename, "r") as f:
                conversations = json.load(f)
        
        # Check if we're updating an existing conversation or creating a new one
        if st.session_state.chat_id:
            # Find and update existing conversation
            for convo in conversations:
                if convo.get("id") == st.session_state.chat_id:
                    convo["messages"] = messages
                    convo["last_updated"] = timestamp
                    break
        else:
            # Create a new conversation object
            new_id = str(uuid.uuid4())
            conversation = {
                "id": new_id,
                "user": username,
                "model": model,
                "timestamp": timestamp,
                "last_updated": timestamp,
                "messages": messages
            }
            
            # Add new conversation
            conversations.append(conversation)
            
            # Store the new ID in session state
            st.session_state.chat_id = new_id
        
        # Write back to file
        with open(filename, "w") as f:
            json.dump(conversations, f, indent=2)
    except Exception as e:
        # Silent fail - logging would be better in production
        pass

def load_conversations(username: str) -> List[Dict[str, Any]]:
    """
    Load all conversations for a specific user.
    
    Args:
        username: The user's username
        
    Returns:
        A list of conversation objects
    """
    if st.session_state.db_type == "postgresql":
        try:
            # Connect to PostgreSQL using helper function
            db_url = get_db_url()
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Query for user's conversations
            cursor.execute(
                """
                SELECT id, model, timestamp, last_updated, messages 
                FROM conversations 
                WHERE user_id = %s 
                ORDER BY last_updated DESC 
                LIMIT 10
                """,
                (username,)
            )
            
            # Format results
            conversations = []
            for chat_id, model, timestamp, last_updated, messages in cursor.fetchall():
                conversations.append({
                    "id": chat_id,
                    "model": model,
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_updated": last_updated.strftime("%Y-%m-%d %H:%M:%S") if last_updated else timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "messages": json.loads(messages)
                })
            
            conn.close()
            return conversations
        except Exception as e:
            # If PostgreSQL fails, fall back to JSON
            return _load_from_json(username)
    else:
        # Load from JSON file
        return _load_from_json(username)

def _load_from_json(username: str) -> List[Dict[str, Any]]:
    """
    Load conversations from a JSON file.
    
    Args:
        username: The user's username
        
    Returns:
        A list of conversation objects
    """
    filename = f"data/{username}_conversations.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                conversations = json.load(f)
            
            # Sort by last_updated (or timestamp if last_updated doesn't exist) in descending order
            conversations.sort(
                key=lambda x: x.get("last_updated", x.get("timestamp", "")), 
                reverse=True
            )
            
            # Return the 10 most recent conversations
            return conversations[:10]
        else:
            return []
    except Exception as e:
        # If reading fails, return empty list
        return []

def get_most_recent_chat(username: str, model: str) -> Tuple[Optional[str], Optional[List[Dict[str, str]]]]:
    """
    Get the most recent chat for a specific user and model.
    
    Args:
        username: The user's username
        model: The model to get the most recent chat for
        
    Returns:
        A tuple with (chat_id, messages) or (None, None) if no chat exists
    """
    if st.session_state.db_type == "postgresql":
        try:
            # Connect to PostgreSQL using helper function
            db_url = get_db_url()
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Query for the most recent chat with this model
            cursor.execute(
                """
                SELECT id, messages 
                FROM conversations 
                WHERE user_id = %s AND model = %s 
                ORDER BY last_updated DESC 
                LIMIT 1
                """,
                (username, model)
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                chat_id, messages = result
                return chat_id, json.loads(messages)
            else:
                return None, None
        except Exception as e:
            # If PostgreSQL fails, fall back to JSON
            return _get_most_recent_chat_json(username, model)
    else:
        # Use JSON file
        return _get_most_recent_chat_json(username, model)

def _get_most_recent_chat_json(username: str, model: str) -> Tuple[Optional[str], Optional[List[Dict[str, str]]]]:
    """
    Get the most recent chat from JSON for a specific user and model.
    
    Args:
        username: The user's username
        model: The model to get the most recent chat for
        
    Returns:
        A tuple with (chat_id, messages) or (None, None) if no chat exists
    """
    filename = f"data/{username}_conversations.json"
    
    try:
        if os.path.exists(filename):
            with open(filename, "r") as f:
                conversations = json.load(f)
            
            # Filter conversations by model
            model_conversations = [c for c in conversations if c.get("model") == model]
            
            if model_conversations:
                # Sort by last_updated (or timestamp if last_updated doesn't exist)
                model_conversations.sort(
                    key=lambda x: x.get("last_updated", x.get("timestamp", "")), 
                    reverse=True
                )
                
                # Return the most recent conversation
                most_recent = model_conversations[0]
                return most_recent.get("id"), most_recent.get("messages", [])
            else:
                return None, None
        else:
            return None, None
    except Exception as e:
        # If reading fails, return None
        return None, None

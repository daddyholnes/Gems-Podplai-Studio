import streamlit as st
import os
import json
import datetime
import secrets
import hashlib
import base64
from typing import Optional, Dict, Tuple
import psycopg2
from urllib.parse import urlparse

# Secret key for session tokens - auto-generated on first run
if "auth_secret_key" not in st.session_state:
    st.session_state.auth_secret_key = secrets.token_hex(32)

# Define admin user
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("adminpassword123".encode()).hexdigest()  # Default admin password

def get_db_connection():
    """Get a connection to the PostgreSQL database."""
    try:
        # Get DATABASE_URL from environment
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return None
            
        # Parse the URL and create a connection
        parsed_url = urlparse(db_url)
        connection = psycopg2.connect(
            dbname=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port
        )
        return connection
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

def init_auth_tables():
    """Initialize authentication tables in the database."""
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Create users table if it doesn't exist
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin BOOLEAN DEFAULT FALSE
        )
        """)
        
        # Create sessions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            session_token VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
        """)
        
        # Check if admin user exists, if not create it
        cursor.execute("SELECT * FROM users WHERE username = %s", (ADMIN_USERNAME,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, %s)",
                (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, True)
            )
            
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error initializing auth tables: {str(e)}")
        return False
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash

def create_user(username: str, password: str, email: str = None, is_admin: bool = False) -> bool:
    """Create a new user in the database."""
    if not username or not password:
        return False
        
    conn = get_db_connection()
    if not conn:
        return False
        
    try:
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone() is not None:
            return False
            
        # Hash the password
        password_hash = hash_password(password)
        
        # Insert the new user
        cursor.execute(
            "INSERT INTO users (username, password_hash, email, is_admin) VALUES (%s, %s, %s, %s)",
            (username, password_hash, email, is_admin)
        )
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")
        return False
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[Dict]]:
    """Authenticate a user by username and password."""
    if not username or not password:
        return False, None
        
    conn = get_db_connection()
    if not conn:
        # Fallback to check if it's the admin user with default credentials
        if username == ADMIN_USERNAME and verify_password(password, ADMIN_PASSWORD_HASH):
            return True, {"id": 0, "username": ADMIN_USERNAME, "is_admin": True}
        return False, None
        
    try:
        cursor = conn.cursor()
        
        # Get the user
        cursor.execute("SELECT id, username, password_hash, is_admin FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        
        if not user:
            return False, None
            
        # Verify password
        if verify_password(password, user[2]):
            return True, {"id": user[0], "username": user[1], "is_admin": user[3]}
        
        return False, None
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return False, None
    finally:
        conn.close()

def create_session(user_id: int, username: str) -> Optional[str]:
    """Create a new session for a user."""
    # Generate a session token
    session_token = secrets.token_hex(32)
    
    # For admin user with fallback auth, just return the token
    if user_id == 0:
        return session_token
        
    conn = get_db_connection()
    if not conn:
        return None
        
    try:
        cursor = conn.cursor()
        
        # Set expiration to 30 days from now
        expires_at = datetime.datetime.now() + datetime.timedelta(days=30)
        
        # Insert the session
        cursor.execute(
            "INSERT INTO sessions (user_id, session_token, expires_at) VALUES (%s, %s, %s)",
            (user_id, session_token, expires_at)
        )
        
        conn.commit()
        return session_token
    except Exception as e:
        st.error(f"Error creating session: {str(e)}")
        return None
    finally:
        conn.close()

def validate_session(session_token: str) -> Tuple[bool, Optional[Dict]]:
    """Validate a session token."""
    if not session_token:
        return False, None
        
    conn = get_db_connection()
    if not conn:
        # For admin fallback, check if it's in session state
        if hasattr(st.session_state, "admin_session") and st.session_state.admin_session == session_token:
            return True, {"id": 0, "username": ADMIN_USERNAME, "is_admin": True}
        return False, None
        
    try:
        cursor = conn.cursor()
        
        # Get the session
        cursor.execute("""
        SELECT s.id, s.user_id, s.expires_at, u.username, u.is_admin
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.session_token = %s
        """, (session_token,))
        
        session = cursor.fetchone()
        
        if not session:
            return False, None
            
        # Check if session is expired
        if session[2] < datetime.datetime.now():
            # Delete expired session
            cursor.execute("DELETE FROM sessions WHERE id = %s", (session[0],))
            conn.commit()
            return False, None
            
        return True, {"id": session[1], "username": session[3], "is_admin": session[4]}
    except Exception as e:
        st.error(f"Session validation error: {str(e)}")
        return False, None
    finally:
        conn.close()

def end_session(session_token: str) -> bool:
    """End a session."""
    if not session_token:
        return False
        
    conn = get_db_connection()
    if not conn:
        # For admin fallback
        if hasattr(st.session_state, "admin_session") and st.session_state.admin_session == session_token:
            st.session_state.admin_session = None
            return True
        return False
        
    try:
        cursor = conn.cursor()
        
        # Delete the session
        cursor.execute("DELETE FROM sessions WHERE session_token = %s", (session_token,))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error ending session: {str(e)}")
        return False
    finally:
        conn.close()

def check_login() -> None:
    """
    Checks if a user is logged in and handles the login process if not.
    Updates session state with user information.
    """
    # Initialize auth tables on first run
    if "auth_initialized" not in st.session_state:
        init_auth_tables()
        st.session_state.auth_initialized = True
    
    # Check if session token exists in cookies
    session_token = st.session_state.get("session_token")
    
    # Validate session if token exists
    if session_token:
        is_valid, user_data = validate_session(session_token)
        if is_valid and user_data:
            st.session_state.user = user_data["username"]
            st.session_state.user_id = user_data["id"]
            st.session_state.is_admin = user_data["is_admin"]
            return
    
    # If we get here, user is not logged in, show login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("AI Chat Studio")
        st.subheader("Welcome to Dartopia.uk AI")
        
        # Create tabs for login and register
        login_tab, register_tab = st.tabs(["Login", "Register"])
        
        with login_tab:
            st.subheader("Sign In")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            
            if st.button("Login", key="login_button"):
                if username.strip() and password:
                    authenticated, user_data = authenticate_user(username, password)
                    
                    if authenticated:
                        # Create a session
                        session_token = create_session(user_data["id"], user_data["username"])
                        
                        if session_token:
                            # Store in session state
                            st.session_state.session_token = session_token
                            st.session_state.user = user_data["username"]
                            st.session_state.user_id = user_data["id"]
                            st.session_state.is_admin = user_data["is_admin"]
                            
                            # For admin fallback
                            if user_data["id"] == 0:
                                st.session_state.admin_session = session_token
                                
                            st.success(f"Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("Failed to create session. Please try again.")
                    else:
                        st.error("Invalid username or password")
                else:
                    st.error("Please enter both username and password")
        
        with register_tab:
            st.subheader("Create Account")
            reg_username = st.text_input("Username", key="reg_username")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm_password")
            reg_email = st.text_input("Email (Optional)", key="reg_email")
            
            if st.button("Register", key="register_button"):
                if reg_username.strip() and reg_password:
                    if reg_password != reg_confirm_password:
                        st.error("Passwords do not match")
                    else:
                        # Create the user
                        success = create_user(reg_username, reg_password, reg_email)
                        
                        if success:
                            st.success("Account created successfully! You can now log in.")
                            st.session_state.show_login = True
                            st.rerun()
                        else:
                            st.error("Username already exists or there was an error creating your account")
                else:
                    st.error("Please enter username and password")
        
        # Admin login link
        st.markdown("---")
        if st.button("Administrator Login", key="admin_login_button"):
            st.session_state.show_admin_login = True
            st.rerun()
            
        if st.session_state.get("show_admin_login", False):
            st.subheader("Administrator Login")
            admin_username = st.text_input("Admin Username", key="admin_username")
            admin_password = st.text_input("Admin Password", type="password", key="admin_password")
            
            if st.button("Login as Admin", key="admin_login_submit"):
                if admin_username == ADMIN_USERNAME and verify_password(admin_password, ADMIN_PASSWORD_HASH):
                    # Create admin session
                    session_token = create_session(0, ADMIN_USERNAME)
                    
                    if session_token:
                        st.session_state.session_token = session_token
                        st.session_state.user = ADMIN_USERNAME
                        st.session_state.user_id = 0
                        st.session_state.is_admin = True
                        st.session_state.admin_session = session_token
                        
                        st.success("Welcome, Administrator!")
                        st.rerun()
                else:
                    st.error("Invalid administrator credentials")
    
    # Prevent rest of app from loading
    st.stop()

def logout_user() -> None:
    """
    Logs out the current user by clearing the session state and ending the session.
    """
    # End the session in the database
    if "session_token" in st.session_state:
        end_session(st.session_state.session_token)
    
    # Clear session state
    st.session_state.session_token = None
    st.session_state.user = None
    st.session_state.user_id = None
    st.session_state.is_admin = None
    st.session_state.messages = []
    st.session_state.current_model = "Gemini"
    
    # Rerun to show login screen
    st.rerun()

def get_current_user() -> Optional[str]:
    """
    Returns the currently logged in username or None.
    
    Returns:
        The current username or None if not logged in
    """
    return st.session_state.get("user")

def is_admin() -> bool:
    """
    Check if the current user is an admin.
    
    Returns:
        True if the user is an admin, False otherwise
    """
    return st.session_state.get("is_admin", False)

import streamlit as st
import os
import sys
import secrets
import json

st.set_page_config(
    page_title="Debug OAuth",
    page_icon="🔧",
    layout="wide"
)

st.title("OAuth Debug Info & Tools")
st.markdown("""
This page provides diagnostics and tools to help debug OAuth issues.
""")

# Show environment variables related to OAuth
st.header("1. Environment Variables")
with st.expander("View OAuth-related environment variables", expanded=True):
    oauth_vars = {k: v for k, v in os.environ.items() if 'OAUTH' in k or 'GOOGLE' in k or 'CLIENT' in k}
    # Don't show actual secrets, just indicate they exist
    for key, value in oauth_vars.items():
        if "SECRET" in key or "KEY" in key or "TOKEN" in key:
            oauth_vars[key] = f"[HIDDEN] (length: {len(value)})"
    
    st.json(oauth_vars)

# Let user try a custom redirect URI
st.header("2. Redirect URI Tester")
with st.expander("Test different redirect URIs", expanded=True):
    st.markdown("""
    Use this tool to test if a redirect URI is properly configured in both:
    1. Your Google Cloud OAuth consent screen
    2. The application code
    """)
    
    uris_to_test = [
        "https://dartopia.uk",
        "https://podplay.replit.app",
        "http://localhost:5000", 
        "https://dartopia.uk/oauth_callback",
        "https://podplay.replit.app/oauth_callback"
    ]
    
    uri_col1, uri_col2 = st.columns(2)
    with uri_col1:
        selected_uri = st.selectbox("Select a redirect URI to test:", uris_to_test)
    with uri_col2:
        custom_uri = st.text_input("Or enter a custom URI:", "")
    
    redirect_uri = custom_uri if custom_uri else selected_uri
    
    if st.button("Test URI"):
        # Import the necessary modules
        try:
            from google_auth_oauthlib.flow import Flow
            st.success("✅ Successfully imported google_auth_oauthlib.flow")
            
            # Create a very basic OAuth flow
            client_config = {
                "web": {
                    "client_id": os.environ.get("GOOGLE_CLIENT_ID", "test-client-id"),
                    "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "test-client-secret"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            }
            
            try:
                # Create a flow
                flow = Flow.from_client_config(
                    client_config,
                    scopes=["https://www.googleapis.com/auth/userinfo.email", 
                            "https://www.googleapis.com/auth/userinfo.profile"],
                    redirect_uri=redirect_uri
                )
                
                # Generate a test state token
                test_state = secrets.token_urlsafe(16)
                
                # Get the authorization URL
                auth_url, _ = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                    state=test_state,
                    prompt="consent"
                )
                
                st.success(f"✅ Successfully created authorization URL")
                
                uri_result1, uri_result2 = st.columns(2)
                with uri_result1:
                    st.markdown("### Auth URL")
                    st.markdown(f"[Click to test auth URL]({auth_url})")
                    with st.expander("View full auth URL", expanded=False):
                        st.code(auth_url)
                
                with uri_result2:
                    st.markdown("### Redirect URI Check")
                    # Check if the redirect URI in the flow matches what we set
                    st.info(f"Flow redirect URI: {flow.redirect_uri}")
                    if flow.redirect_uri != redirect_uri:
                        st.error(f"❌ Redirect URI mismatch! Flow has {flow.redirect_uri} but we set {redirect_uri}")
                    else:
                        st.success("✅ Redirect URIs match")
                    
                # Add the test state to session state for later verification
                st.session_state["debug_oauth_test_state"] = test_state
                    
            except Exception as e:
                st.error(f"❌ Error creating flow: {type(e).__name__}: {str(e)}")
                
        except ImportError as e:
            st.error(f"❌ Failed to import: {str(e)}")
            st.info("Make sure google-auth-oauthlib is installed")

# Callback URL simulator
st.header("3. Callback URL Simulator")
with st.expander("Simulate OAuth Callback Processing", expanded=True):
    st.markdown("""
    This tool simulates receiving and processing an OAuth callback.
    Use this to test if our callback handling code works properly.
    """)
    
    callback_url = st.text_input(
        "Callback URL (with code and state):", 
        value="https://podplay.replit.app?code=EXAMPLE_CODE&state=EXAMPLE_STATE"
    )
    
    if st.button("Process Callback"):
        try:
            # Try to extract code and state from the URL
            import urllib.parse
            parsed_url = urllib.parse.urlparse(callback_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            code = query_params.get("code", [""])[0]
            state = query_params.get("state", [""])[0]
            
            if not code or not state:
                st.error("❌ Could not extract code or state from URL")
            else:
                st.success(f"✅ Successfully extracted code and state")
                st.json({
                    "code": f"{code[:5]}...{code[-5:] if len(code) > 10 else ''}",
                    "code_length": len(code),
                    "state": state,
                    "state_length": len(state),
                    "full_url": callback_url
                })
                
                # Check if this matches our test state from the previous step
                test_state = st.session_state.get("debug_oauth_test_state", "")
                if test_state and test_state == state:
                    st.success("✅ State token matches the test token generated earlier")
                elif test_state:
                    st.warning("⚠️ State token does not match the test token")
                
        except Exception as e:
            st.error(f"❌ Error processing callback: {type(e).__name__}: {str(e)}")

# System info
st.header("4. System Information")
with st.expander("View System Details", expanded=False):
    sys_col1, sys_col2 = st.columns(2)
    
    with sys_col1:
        st.subheader("Python Version")
        st.code(sys.version)
        
        st.subheader("Installed Packages")
        try:
            import pkg_resources
            packages = [
                str(pkg) for pkg in pkg_resources.working_set 
                if 'google' in str(pkg).lower() or 'auth' in str(pkg).lower() or 'oauth' in str(pkg).lower()
            ]
            st.code("\n".join(packages))
        except:
            st.error("Could not retrieve package information")
    
    with sys_col2:
        st.subheader("Path Information")
        st.code("\n".join(sys.path))

# Session state
st.header("5. Session State")
with st.expander("View Session State", expanded=False):
    auth_keys = {k: v for k, v in st.session_state.items() 
                 if 'oauth' in k.lower() or 'google' in k.lower() or 'auth' in k.lower() or 'token' in k.lower()}
    
    if auth_keys:
        st.json(auth_keys)
    else:
        st.info("No OAuth-related session state variables found")

# Developer tools
st.header("6. Developer Tools")
with st.expander("Developer Utilities", expanded=True):
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear OAuth Session State"):
            for key in list(st.session_state.keys()):
                if 'oauth' in key.lower() or 'google' in key.lower() or 'auth' in key.lower() or 'token' in key.lower():
                    del st.session_state[key]
            st.success("✅ OAuth session state cleared")
            st.rerun()
    
    with col2:
        if st.button("Generate New State Token"):
            new_state = secrets.token_urlsafe(32)
            st.session_state["oauth_state"] = new_state
            os.environ["OAUTH_STATE_TOKEN"] = new_state
            st.success(f"✅ New state token generated and stored")
            st.code(new_state)

# Bypass controls
st.header("7. Authentication Bypass")
with st.expander("Developer Bypass Controls", expanded=True):
    st.warning("⚠️ SECURITY WARNING: These options bypass security checks and should only be used during development!")
    
    bypass_col1, bypass_col2 = st.columns(2)
    
    with bypass_col1:
        auth_bypass = os.environ.get("BYPASS_AUTH", "").lower() == "true"
        new_auth_bypass = st.checkbox("Bypass Authentication", value=auth_bypass)
        
        if new_auth_bypass != auth_bypass:
            os.environ["BYPASS_AUTH"] = "true" if new_auth_bypass else "false"
            st.success(f"{'Enabled' if new_auth_bypass else 'Disabled'} authentication bypass")
    
    with bypass_col2:
        state_bypass = os.environ.get("BYPASS_STATE_CHECK", "").lower() == "true"
        new_state_bypass = st.checkbox("Bypass State Validation", value=state_bypass)
        
        if new_state_bypass != state_bypass:
            os.environ["BYPASS_STATE_CHECK"] = "true" if new_state_bypass else "false"
            st.success(f"{'Enabled' if new_state_bypass else 'Disabled'} state validation bypass")
    
    if new_auth_bypass or new_state_bypass:
        st.markdown("**To apply these changes, you need to restart the application.**")
        if st.button("Restart Application"):
            # This will cause Streamlit to rerun the entire app
            st.rerun()

# Help and documentation
st.markdown("---")
st.markdown("""
### Common OAuth Issues

1. **Redirect URI Mismatch**: The redirect URI in your code must exactly match one of the URIs configured in Google Cloud Console, including the protocol (http/https) and trailing slashes.

2. **State Token Problems**: If you see "Invalid state parameter" errors, it usually means the session expired between authorization and callback.

3. **Missing Scopes**: Ensure you're requesting the right scopes for the data you need.

4. **Consent Screen Configuration**: Make sure your OAuth consent screen is properly configured in Google Cloud Console.
""")
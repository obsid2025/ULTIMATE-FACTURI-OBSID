"""
Sistem de autentificare pentru dashboard
"""

import streamlit as st
import os
import hashlib
import secrets
from typing import Optional, Dict


def clean_env_value(value: str) -> str:
    """Clean environment variable value from escape artifacts."""
    if not value:
        return value
    # Remove trailing backslashes added by shell escaping
    cleaned = value.rstrip('\\')
    return cleaned


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hashed


def get_credentials() -> Dict:
    """Get credentials from environment variables."""
    credentials = {
        'usernames': {}
    }

    # Admin user from env (clean values from shell escape artifacts)
    admin_user = clean_env_value(os.getenv('ADMIN_USERNAME', 'admin'))
    admin_pass = clean_env_value(os.getenv('ADMIN_PASSWORD', 'admin123'))
    admin_name = clean_env_value(os.getenv('ADMIN_NAME', 'Administrator'))

    credentials['usernames'][admin_user] = {
        'name': admin_name,
        'password': hash_password(admin_pass)
    }

    # Additional users from env (format: user1,pass1,name1;user2,pass2,name2)
    additional = os.getenv('ADDITIONAL_USERS', '')
    if additional:
        for user_data in additional.split(';'):
            parts = user_data.strip().split(',')
            if len(parts) >= 3:
                username, password, name = parts[0], parts[1], parts[2]
                credentials['usernames'][username] = {
                    'name': name,
                    'password': hash_password(password)
                }

    return credentials


def login_form() -> Optional[str]:
    """
    Display login form and return username if authenticated.
    Returns None if not authenticated.
    """
    # Check if already logged in
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return st.session_state.get('username')

    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None

    credentials = get_credentials()

    # Premium CSS for login page - GitHub Dark style with Inter font
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-card: #1c2128;
        --border-subtle: #30363d;
        --border-accent: #484f58;
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --text-muted: #6e7681;
        --accent-primary: #8b949e;
        --accent-emerald: #3fb950;
        --accent-rose: #f85149;
    }

    .stApp {
        background-color: var(--bg-primary);
    }

    .login-wrapper {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
    }

    .login-card {
        width: 100%;
        max-width: 400px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 2.5rem 2rem;
        box-shadow: 0 16px 32px rgba(0, 0, 0, 0.4);
    }

    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .login-logo {
        width: 64px;
        height: 64px;
        margin-bottom: 1.25rem;
        filter: grayscale(100%) brightness(1.2);
    }

    .login-title {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.01em;
    }

    .login-subtitle {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.75rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 0;
    }

    /* Form styling */
    [data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }

    .stTextInput > div > div > input {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        padding: 0.75rem 1rem !important;
        font-size: 0.9rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--text-secondary) !important;
        box-shadow: none !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
    }

    .stTextInput > label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    /* Login button */
    .stButton > button {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0 !important;
        background: var(--border-accent) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-accent) !important;
        border-radius: 6px !important;
        padding: 0.75rem 1.5rem !important;
        margin-top: 0.5rem !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }

    .stButton > button:hover {
        background: var(--text-muted) !important;
        border-color: var(--text-muted) !important;
    }

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Alert styling */
    .stAlert {
        background: rgba(248, 81, 73, 0.1) !important;
        border: 1px solid var(--accent-rose) !important;
        border-radius: 6px !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        st.markdown("""
        <div class="login-header">
            <img src="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg"
                 class="login-logo" alt="OBSID Logo">
            <h1 class="login-title">Ultimate Facturi</h1>
            <p class="login-subtitle">OBSID Dashboard</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Utilizator", placeholder="Introdu utilizatorul")
            password = st.text_input("Parola", type="password", placeholder="Introdu parola")
            submitted = st.form_submit_button("Autentificare", use_container_width=True)

            if submitted:
                if username in credentials['usernames']:
                    stored_password = credentials['usernames'][username]['password']
                    if verify_password(password, stored_password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.session_state.name = credentials['usernames'][username]['name']
                        st.rerun()
                    else:
                        st.error("Parola incorecta")
                else:
                    st.error("Utilizator inexistent")

    return None


def logout():
    """Logout current user."""
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.name = None
    st.rerun()


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)


def get_user_name() -> str:
    """Get current user's display name or 'Vizitator' if not logged in."""
    if is_authenticated():
        return st.session_state.get('name', 'User')
    return 'Vizitator'


def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            login_form()
            st.stop()
        return func(*args, **kwargs)
    return wrapper


@st.dialog("Autentificare necesara")
def login_dialog():
    """Show login dialog for actions that require authentication."""
    credentials = get_credentials()

    st.markdown("""
    <style>
    .auth-notice {
        font-family: 'VCR OSD Mono', monospace;
        font-size: 0.875rem;
        color: #8b949e;
        margin-bottom: 1rem;
    }
    </style>
    <p class="auth-notice">Aceasta actiune necesita autentificare.</p>
    """, unsafe_allow_html=True)

    username = st.text_input("Utilizator", placeholder="Introdu utilizatorul", key="dialog_user")
    password = st.text_input("Parola", type="password", placeholder="Introdu parola", key="dialog_pass")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Autentificare", use_container_width=True, type="primary"):
            if username in credentials['usernames']:
                stored_password = credentials['usernames'][username]['password']
                if verify_password(password, stored_password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.name = credentials['usernames'][username]['name']
                    st.session_state.auth_action_approved = True
                    st.rerun()
                else:
                    st.error("Parola incorecta")
            else:
                st.error("Utilizator inexistent")
    with col2:
        if st.button("Anuleaza", use_container_width=True):
            st.rerun()


def check_auth_for_action(action_name: str = "aceasta actiune") -> bool:
    """
    Check if user is authenticated for an action.
    If not, shows login dialog.
    Returns True if authenticated, False otherwise.
    """
    if is_authenticated():
        return True

    # Show login dialog
    login_dialog()
    return False

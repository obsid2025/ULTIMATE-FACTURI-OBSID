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

    # Premium CSS for login page - Luxury Fintech style
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-primary: #0a0a0b;
        --bg-secondary: #111113;
        --bg-card: #1c1c1f;
        --border-subtle: #27272a;
        --border-accent: #3f3f46;
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #71717a;
        --accent-gold: #d4a853;
        --accent-gold-light: #e8c97a;
        --accent-gold-dark: #b8923f;
        --shadow-gold: rgba(212, 168, 83, 0.15);
    }

    .stApp {
        background-color: var(--bg-primary);
        background-image:
            radial-gradient(ellipse at 50% 0%, rgba(212, 168, 83, 0.08) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 100%, rgba(212, 168, 83, 0.03) 0%, transparent 50%);
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
        max-width: 420px;
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 3rem 2.5rem;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        position: relative;
        overflow: hidden;
    }

    .login-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--accent-gold) 0%, var(--accent-gold-dark) 100%);
    }

    .login-header {
        text-align: center;
        margin-bottom: 2.5rem;
    }

    .login-logo {
        width: 80px;
        height: 80px;
        margin-bottom: 1.5rem;
        filter: drop-shadow(0 0 30px var(--shadow-gold));
    }

    .login-title {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.75rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }

    .login-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: var(--accent-gold);
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 500;
        margin: 0;
    }

    /* Form styling */
    [data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }

    .stTextInput > div > div > input {
        font-family: 'DM Sans', sans-serif !important;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        padding: 0.875rem 1rem !important;
        font-size: 0.9375rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 0 1px var(--accent-gold) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: var(--text-muted) !important;
    }

    .stTextInput > label {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    /* Login button */
    .stButton > button {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9375rem !important;
        letter-spacing: 0.02em !important;
        background: linear-gradient(135deg, var(--accent-gold) 0%, var(--accent-gold-dark) 100%) !important;
        color: var(--bg-primary) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.875rem 1.5rem !important;
        margin-top: 0.5rem !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px var(--shadow-gold) !important;
    }

    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px var(--shadow-gold) !important;
        background: linear-gradient(135deg, var(--accent-gold-light) 0%, var(--accent-gold) 100%) !important;
    }

    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Alert styling */
    .stAlert {
        background: rgba(244, 63, 94, 0.1) !important;
        border: 1px solid #f43f5e !important;
        border-radius: 8px !important;
        font-family: 'DM Sans', sans-serif !important;
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


def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authenticated', False):
            login_form()
            st.stop()
        return func(*args, **kwargs)
    return wrapper

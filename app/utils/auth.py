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

    # Custom CSS for login page
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 0 auto;
        padding: 2rem;
        background: #1e293b;
        border-radius: 16px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    .login-logo {
        width: 120px;
        height: auto;
        margin-bottom: 1rem;
    }
    .login-title {
        color: #e2e8f0;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    .login-subtitle {
        color: #94a3b8;
        font-size: 0.875rem;
        margin-top: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-header">
            <img src="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg"
                 class="login-logo" alt="OBSID Logo">
            <h1 class="login-title">Ultimate Facturi</h1>
            <p class="login-subtitle">Dashboard OBSID</p>
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
                        st.error("Parola incorectă!")
                else:
                    st.error("Utilizator inexistent!")

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

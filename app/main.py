"""
Ultimate Facturi OBSID - Dashboard Web
Aplicatie Streamlit pentru procesarea si gruparea facturilor
"""

import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import utils
from utils.auth import login_form, logout, is_authenticated, get_user_name
from utils.mt940_parser import get_sursa_incasare
from utils.data_sync import (
    import_mt940_to_supabase,
    sync_oblio_invoices,
    get_profit_data,
    get_recent_sync_logs
)
from utils.supabase_client import test_connection as test_supabase
from utils.oblio_api import test_connection as test_oblio
import plotly.graph_objects as go

# Page config
st.set_page_config(
    page_title="Ultimate Facturi OBSID",
    page_icon="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS - GitHub Dark Aesthetic
st.markdown("""
<style>
    /* Import Inter font - clean, modern, highly readable */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* CRITICAL: Hide Streamlit's automatic multipage navigation */
    /* This prevents pages from showing before authentication */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }

    /* CSS Variables - GitHub Dark Theme */
    :root {
        --bg-primary: #0d1117;
        --bg-secondary: #161b22;
        --bg-tertiary: #21262d;
        --bg-card: #1c2128;
        --border-subtle: #30363d;
        --border-accent: #484f58;
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
        --text-muted: #6e7681;
        --accent-primary: #8b949e;
        --accent-light: #c9d1d9;
        --accent-dark: #6e7681;
        --accent-emerald: #3fb950;
        --accent-rose: #f85149;
        --accent-blue: #58a6ff;
        --shadow-primary: rgba(139, 148, 158, 0.1);
        --shadow-dark: rgba(0, 0, 0, 0.5);
    }

    /* Global resets */
    .main {
        background-color: var(--bg-primary);
    }

    .stApp {
        background-color: var(--bg-primary);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-subtle);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
    }

    /* Sidebar collapse/expand button - always visible */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"],
    .st-emotion-cache-1dp5vir,
    [data-testid="baseButton-header"] {
        visibility: visible !important;
        opacity: 1 !important;
        background-color: var(--bg-tertiary) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-primary) !important;
    }

    /* Ensure expand button is visible when sidebar is collapsed */
    [data-testid="stSidebarCollapsedControl"],
    .st-emotion-cache-16txtl3 {
        background-color: var(--bg-secondary) !important;
        border: 1px solid var(--border-subtle) !important;
    }

    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] svg {
        color: var(--text-primary) !important;
        fill: var(--text-primary) !important;
    }

    /* Typography - Inter for clean readability */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.01em;
    }

    h1 {
        font-size: 1.75rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem !important;
    }

    h2 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
    }

    h3 {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    p, span, div, label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        color: var(--text-secondary);
    }

    /* Brand header in sidebar */
    .brand-header {
        padding: 1.5rem 1rem;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 1rem;
    }

    .brand-logo {
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .brand-logo img {
        width: 48px;
        height: 48px;
        filter: grayscale(100%) brightness(1.2);
    }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.125rem;
        font-weight: 400;
        color: var(--text-primary);
        letter-spacing: 0.05em;
        line-height: 1.2;
    }

    .brand-tagline {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.625rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }

    /* User profile section */
    .user-profile {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        margin: 0 0.5rem 1rem 0.5rem;
    }

    .user-avatar {
        width: 36px;
        height: 36px;
        background: var(--border-accent);
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 400;
        font-size: 1rem;
        color: var(--text-primary);
    }

    .user-details {
        flex: 1;
    }

    .user-name {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 400;
        font-size: 0.875rem;
        color: var(--text-primary);
        line-height: 1.3;
    }

    .user-role {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.625rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Navigation section */
    .nav-section {
        padding: 0 0.5rem;
    }

    .nav-label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.625rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        padding: 0.5rem 0.75rem;
        margin-bottom: 0.25rem;
    }

    /* Navigation buttons - refined */
    [data-testid="stSidebar"] .stButton > button {
        background: transparent;
        color: var(--text-secondary);
        border: none;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        margin-bottom: 2px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.875rem;
        font-weight: 400;
        text-align: left;
        justify-content: flex-start;
        transition: all 0.15s ease;
        position: relative;
        overflow: hidden;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
        transform: none;
        box-shadow: none;
    }

    [data-testid="stSidebar"] .stButton > button:active {
        background: var(--bg-card);
    }

    /* Active navigation state */
    [data-testid="stSidebar"] .nav-active > button {
        background: var(--bg-tertiary) !important;
        color: var(--text-primary) !important;
        border-left: 2px solid var(--text-secondary) !important;
        border-radius: 0 4px 4px 0 !important;
    }

    /* Logout button special styling */
    .logout-section {
        margin-top: auto;
        padding: 1rem 0.5rem;
        border-top: 1px solid var(--border-subtle);
    }

    .logout-section .stButton > button {
        background: transparent !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-muted) !important;
    }

    .logout-section .stButton > button:hover {
        border-color: var(--accent-rose) !important;
        color: var(--accent-rose) !important;
        background: rgba(248, 81, 73, 0.1) !important;
    }

    /* Main content area */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 1400px;
    }

    /* Page header */
    .page-header {
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border-subtle);
    }

    .page-title {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.5rem;
        font-weight: 400;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
        letter-spacing: 0.05em;
    }

    .page-subtitle {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.875rem;
        color: var(--text-muted);
        margin: 0;
    }

    /* Metric cards - GitHub style */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 1.25rem;
        position: relative;
        overflow: hidden;
        transition: border-color 0.15s ease;
    }

    .metric-card:hover {
        border-color: var(--border-accent);
    }

    .metric-label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.625rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.5rem;
        font-weight: 400;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 0.25rem;
    }

    .metric-value.gold {
        color: var(--accent-emerald);
    }

    .metric-change {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.75rem;
        color: var(--accent-emerald);
    }

    .metric-change.negative {
        color: var(--accent-rose);
    }

    /* Section headers */
    .section-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 2rem 0 1rem 0;
    }

    .section-title {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.75rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    .section-line {
        flex: 1;
        height: 1px;
        background: var(--border-subtle);
    }

    /* File upload areas */
    [data-testid="stFileUploader"] {
        background: var(--bg-secondary);
        border: 1px dashed var(--border-accent);
        border-radius: 6px;
        padding: 1.25rem;
        transition: all 0.15s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--text-secondary);
        background: var(--bg-tertiary);
    }

    [data-testid="stFileUploader"] label {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
    }

    /* Primary action buttons - GitHub style */
    .stButton > button {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 400;
        font-size: 0.875rem;
        letter-spacing: 0.02em;
        background: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid var(--border-accent);
        border-radius: 6px;
        padding: 0.625rem 1rem;
        transition: all 0.15s ease;
        box-shadow: none;
    }

    .stButton > button:hover {
        background: var(--border-accent);
        border-color: var(--text-muted);
    }

    .stButton > button:active {
        background: var(--bg-card);
    }

    .stButton > button:disabled {
        background: var(--bg-secondary);
        color: var(--text-muted);
        border-color: var(--border-subtle);
        cursor: not-allowed;
    }

    /* Download button special */
    .stDownloadButton > button {
        background: transparent;
        border: 1px solid var(--accent-emerald);
        color: var(--accent-emerald);
    }

    .stDownloadButton > button:hover {
        background: rgba(63, 185, 80, 0.1);
        border-color: var(--accent-emerald);
    }

    /* Data tables */
    .stDataFrame {
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        overflow: hidden;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: var(--bg-secondary);
    }

    /* Alerts and messages */
    .stAlert {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .stAlert [data-testid="stMarkdownContainer"] p {
        color: var(--text-secondary);
    }

    /* Success state */
    .stSuccess {
        background: rgba(63, 185, 80, 0.1);
        border-color: var(--accent-emerald);
    }

    /* Warning state */
    .stWarning {
        background: rgba(139, 148, 158, 0.1);
        border-color: var(--accent-primary);
    }

    /* Error state */
    .stError {
        background: rgba(248, 81, 73, 0.1);
        border-color: var(--accent-rose);
    }

    /* Progress bar */
    .stProgress > div > div {
        background: var(--text-secondary);
        border-radius: 3px;
    }

    .stProgress > div {
        background: var(--bg-tertiary);
        border-radius: 3px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 400;
        color: var(--text-secondary);
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
    }

    .streamlit-expanderHeader:hover {
        color: var(--text-primary);
        border-color: var(--border-accent);
    }

    /* Multiselect */
    .stMultiSelect [data-baseweb="select"] {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
    }

    .stMultiSelect [data-baseweb="select"]:hover {
        border-color: var(--text-secondary);
    }

    /* Metrics from Streamlit */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 1.5rem;
        color: var(--text-primary);
    }

    [data-testid="stMetricLabel"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.625rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Info box styling */
    .info-box {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 1.25rem;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    .info-box strong {
        color: var(--text-primary);
    }

    /* Dividers */
    hr {
        border: none;
        height: 1px;
        background: var(--border-subtle);
        margin: 1.5rem 0;
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--border-accent);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    /* Quick action cards */
    .action-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 6px;
        padding: 1.25rem;
        text-align: center;
        transition: border-color 0.15s ease;
        cursor: pointer;
    }

    .action-card:hover {
        border-color: var(--border-accent);
    }

    .action-icon {
        width: 40px;
        height: 40px;
        margin: 0 auto 0.75rem auto;
        background: var(--bg-tertiary);
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .action-title {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 400;
        font-size: 0.875rem;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .action-desc {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    /* Hide Streamlit branding - but keep header for sidebar toggle */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Style the header to be minimal but keep sidebar toggle visible */
    header[data-testid="stHeader"] {
        background: transparent !important;
        border: none !important;
    }

    /* Make sure sidebar toggle button is visible and styled */
    button[data-testid="stSidebarNavCollapseButton"],
    button[data-testid="stBaseButton-headerNoPadding"],
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        padding: 8px !important;
        margin: 8px !important;
    }

    button[data-testid="stSidebarNavCollapseButton"]:hover,
    button[data-testid="stBaseButton-headerNoPadding"]:hover {
        background: var(--bg-card) !important;
        border-color: var(--border-accent) !important;
    }

    button[data-testid="stSidebarNavCollapseButton"] svg,
    button[data-testid="stBaseButton-headerNoPadding"] svg {
        color: var(--text-primary) !important;
        width: 20px !important;
        height: 20px !important;
    }
</style>
""", unsafe_allow_html=True)


def get_page_slug(page_name: str) -> str:
    """Convert page name to URL slug."""
    slugs = {
        "Dashboard": "dashboard",
        "Profit Dashboard": "profit",
        "Tracking Colete": "tracking",
        "Export OP-uri": "export-opuri",
        "Incasari MT940": "incasari",
        "Sincronizare Date": "sincronizare",
        "Setari": "setari"
    }
    return slugs.get(page_name, "dashboard")


def get_page_from_slug(slug: str) -> str:
    """Convert URL slug to page name."""
    pages = {
        "dashboard": "Dashboard",
        "profit": "Profit Dashboard",
        "tracking": "Tracking Colete",
        "export-opuri": "Export OP-uri",
        "incasari": "Incasari MT940",
        "sincronizare": "Sincronizare Date",
        "setari": "Setari"
    }
    return pages.get(slug, "Export OP-uri")


def navigate_to(page_name: str):
    """Navigate to a page and update URL."""
    st.session_state.current_page = page_name
    slug = get_page_slug(page_name)
    st.query_params["page"] = slug


def main():
    # Initialize session state for auth
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None

    # Check authentication FIRST - block all access without login
    authenticated = is_authenticated()

    if not authenticated:
        # Show login form - no access without authentication
        login_form()
        return

    # All pages (only accessible after authentication)
    all_pages = [
        "Dashboard",
        "Profit Dashboard",
        "Tracking Colete",
        "Export OP-uri",
        "Incasari MT940",
        "Sincronizare Date",
        "Setari"
    ]

    # Get page from URL query params
    url_page = st.query_params.get("page", None)

    # Initialize or sync current page from URL
    if url_page:
        page_from_url = get_page_from_slug(url_page)
        if page_from_url in all_pages:
            st.session_state.current_page = page_from_url
        else:
            st.session_state.current_page = "Dashboard"
            st.query_params["page"] = "dashboard"
    elif 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
        st.query_params["page"] = "dashboard"

    # Sidebar - always visible
    with st.sidebar:
        # Brand header
        st.markdown("""
        <div class="brand-header">
            <div class="brand-logo">
                <img src="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg" alt="OBSID">
                <div class="brand-text">
                    <span class="brand-name">Ultimate Facturi</span>
                    <span class="brand-tagline">OBSID Dashboard</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # User profile - authenticated user
        user_name = get_user_name()
        user_initial = user_name[0].upper() if user_name else 'A'
        user_role = "Administrator"
        st.markdown(f"""
        <div class="user-profile">
            <div class="user-avatar">{user_initial}</div>
            <div class="user-details">
                <div class="user-name">{user_name}</div>
                <div class="user-role">{user_role}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Navigation
        st.markdown('<div class="nav-section">', unsafe_allow_html=True)
        st.markdown('<div class="nav-label">Meniu Principal</div>', unsafe_allow_html=True)

        # Navigation items
        nav_items = [
            ("Dashboard", "Vedere generala"),
            ("Profit Dashboard", "Profit zilnic/lunar/anual"),
            ("Tracking Colete", "Status AWB si alerte"),
            ("Export OP-uri", "Export contabilitate"),
            ("Incasari MT940", "Extrase bancare"),
            ("Sincronizare Date", "Oblio si MT940"),
            ("Setari", "Configurare")
        ]

        for page_name, _ in nav_items:
            is_active = st.session_state.current_page == page_name

            if is_active:
                st.markdown('<div class="nav-active">', unsafe_allow_html=True)

            if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                navigate_to(page_name)
                st.rerun()

            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Logout at bottom
        st.markdown("---")
        st.markdown('<div class="logout-section">', unsafe_allow_html=True)
        if st.button("Deconectare", key="logout_btn", use_container_width=True):
            logout()
        st.markdown('</div>', unsafe_allow_html=True)

    # Main content
    page = st.session_state.get('current_page', 'Raport OP-uri')

    # Ensure URL is in sync with current page
    current_slug = st.query_params.get("page", "")
    expected_slug = get_page_slug(page)
    if current_slug != expected_slug:
        st.query_params["page"] = expected_slug

    if page == "Dashboard":
        show_dashboard()
    elif page == "Profit Dashboard":
        show_profit_dashboard()
    elif page == "Tracking Colete":
        show_tracking_colete()
    elif page == "Export OP-uri":
        show_export_opuri()
    elif page == "Incasari MT940":
        show_incasari()
    elif page == "Sincronizare Date":
        show_data_sync()
    elif page == "Setari":
        show_setari()


def show_dashboard():
    """Pagina principala cu sumar."""
    from datetime import datetime, date

    # Page header
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Vedere generala asupra facturilor si cifrei de afaceri</p>
    </div>
    """, unsafe_allow_html=True)

    # Sync section - prominent at top
    sync_col1, sync_col2, sync_col3 = st.columns([2, 1, 1])

    with sync_col2:
        if st.button("Sync Facturi Noi", type="primary", key="dashboard_smart_sync"):
            with st.spinner("Se sincronizeaza facturile noi..."):
                try:
                    from utils.data_sync import sync_oblio_invoices
                    from utils.supabase_client import get_supabase_client
                    from datetime import timedelta

                    # Get last invoice date from Supabase
                    supabase = get_supabase_client()
                    last_inv = supabase.table('invoices').select('issue_date').order('issue_date', desc=True).limit(1).execute()

                    if last_inv.data:
                        # Start from last invoice date (minus 1 day for safety)
                        last_date = datetime.strptime(last_inv.data[0]['issue_date'], '%Y-%m-%d').date()
                        start_date = last_date - timedelta(days=1)
                    else:
                        # No invoices yet - sync last 30 days
                        start_date = date.today() - timedelta(days=30)

                    stats = sync_oblio_invoices(issued_after=start_date)
                    st.success(f"Sincronizat! De la {start_date.strftime('%d.%m.%Y')}: {stats['processed']} procesate, {stats['inserted']} actualizate")
                    st.rerun()
                except Exception as e:
                    st.error(f"Eroare la sincronizare: {e}")

    with sync_col3:
        if st.button("Resync 12 luni", type="secondary", key="dashboard_full_sync"):
            with st.spinner("Se re-sincronizeaza ultimele 12 luni..."):
                try:
                    from utils.data_sync import sync_oblio_invoices
                    from datetime import timedelta

                    start_date = date.today() - timedelta(days=365)
                    stats = sync_oblio_invoices(issued_after=start_date)
                    st.success(f"Resync complet! {stats['processed']} procesate, {stats['inserted']} actualizate")
                    st.rerun()
                except Exception as e:
                    st.error(f"Eroare la sincronizare: {e}")

    # Get invoice data from Supabase (synced from Oblio)
    try:
        from utils.supabase_client import get_supabase_client
        supabase = get_supabase_client()

        # Get all non-canceled invoices
        response = supabase.table('invoices').select('total, invoice_type, issue_date, series_name, invoice_number').eq('is_canceled', False).execute()
        all_invoices = response.data if response.data else []

        # Get last sync time
        sync_response = supabase.table('sync_logs').select('finished_at').eq('sync_type', 'oblio_sync').eq('status', 'completed').order('finished_at', desc=True).limit(1).execute()
        last_sync = sync_response.data[0]['finished_at'] if sync_response.data else None

        # Extract available months
        months_set = set()
        for inv in all_invoices:
            if inv.get('issue_date'):
                month = inv['issue_date'][:7]  # YYYY-MM
                months_set.add(month)

        available_months = sorted(months_set, reverse=True)

    except Exception as e:
        st.error(f"Eroare la incarcarea datelor: {e}")
        all_invoices = []
        available_months = []
        last_sync = None

    # Show last sync time
    with sync_col1:
        if last_sync:
            try:
                sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
                st.caption(f"Ultima sincronizare Oblio: {sync_time.strftime('%d.%m.%Y %H:%M')}")
            except:
                st.caption(f"Ultima sincronizare: {last_sync}")
        else:
            st.warning("Nu s-a facut inca sincronizare. Apasa 'Resync COMPLET Oblio'.")

    st.markdown("---")

    # Period filter
    filter_options = ["Tot timpul"] + available_months
    col_filter1, col_filter2 = st.columns([1, 3])

    with col_filter1:
        selected_period = st.selectbox("Perioada:", filter_options, key="dashboard_period")

    # Filter invoices by selected period
    if selected_period == "Tot timpul":
        invoices = all_invoices
        period_label = "toate datele"
    else:
        invoices = [i for i in all_invoices if i.get('issue_date', '').startswith(selected_period)]
        # Format month name
        try:
            month_date = datetime.strptime(selected_period, "%Y-%m")
            month_names = ['Ianuarie', 'Februarie', 'Martie', 'Aprilie', 'Mai', 'Iunie',
                          'Iulie', 'August', 'Septembrie', 'Octombrie', 'Noiembrie', 'Decembrie']
            period_label = f"{month_names[month_date.month - 1]} {month_date.year}"
        except:
            period_label = selected_period

    # Calculate totals for filtered period
    facturi_normale = [i for i in invoices if i.get('invoice_type') == 'Normala']
    facturi_storno = [i for i in invoices if i.get('invoice_type') == 'Storno']
    facturi_stornate = [i for i in invoices if i.get('invoice_type') == 'Stornata']

    total_facturi = len(facturi_normale)
    total_stornari = len(facturi_storno)
    total_stornate = len(facturi_stornate)

    # Total TOATE facturile (ce arata Oblio ca total)
    total_toate = sum(float(i.get('total', 0)) for i in invoices)

    # Facturi active = Normale (fara stornate)
    cifra_normale = sum(float(i.get('total', 0)) for i in facturi_normale)

    # Stornari (valori negative)
    stornari_total = sum(float(i.get('total', 0)) for i in facturi_storno)

    # Stornate (facturi care au fost anulate)
    stornate_total = sum(float(i.get('total', 0)) for i in facturi_stornate)

    # Show period info
    with col_filter2:
        st.markdown(f"<p style='padding-top: 8px; color: var(--text-secondary);'>Afisare pentru: <strong>{period_label}</strong> | Normale: {total_facturi} | Stornate: {total_stornate} | Stornouri: {total_stornari}</p>", unsafe_allow_html=True)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Oblio</div>
            <div class="metric-value">{total_toate:,.2f} RON</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Facturi Active</div>
            <div class="metric-value gold">{cifra_normale:,.2f} RON</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Stornate</div>
            <div class="metric-value">{stornate_total:,.2f} RON</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Stornouri</div>
            <div class="metric-value">{stornari_total:,.2f} RON</div>
        </div>
        """, unsafe_allow_html=True)

    # Invoice list expander
    if invoices:
        with st.expander(f"Vezi lista facturilor ({len(invoices)} documente)"):
            # Create dataframe
            df_data = []
            for inv in sorted(invoices, key=lambda x: x.get('issue_date', ''), reverse=True):
                df_data.append({
                    'Data': inv.get('issue_date', ''),
                    'Serie/Nr': f"{inv.get('series_name', '')}{inv.get('invoice_number', '')}",
                    'Total': float(inv.get('total', 0)),
                    'Tip': inv.get('invoice_type', '')
                })

            df = pd.DataFrame(df_data)
            df['Total'] = df['Total'].apply(lambda x: f"{x:,.2f} RON")
            st.dataframe(df, use_container_width=True, hide_index=True)

    # Section header
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Actiuni Rapide</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # Quick actions
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Sincronizare Oblio", use_container_width=True, key="dash_sync"):
            navigate_to('Sincronizare Date')
            st.rerun()

    with col2:
        if st.button("Analiza Profit", use_container_width=True, key="dash_profit"):
            navigate_to('Profit Dashboard')
            st.rerun()

    with col3:
        if st.button("Export OP-uri", use_container_width=True, key="dash_export"):
            navigate_to('Export OP-uri')
            st.rerun()


def show_export_opuri():
    """Pagina de export OP-uri pentru contabilitate."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Export OP-uri</h1>
        <p class="page-subtitle">Genereaza raportul de facturi grupate pe OP-uri bancare</p>
    </div>
    """, unsafe_allow_html=True)

    # Import processor
    try:
        from utils.opuri_processor import generate_opuri_export
    except ImportError as e:
        st.error(f"Eroare la import: {e}")
        return

    # Show data availability from Supabase
    from utils.supabase_client import get_supabase_client
    client = get_supabase_client()

    if client:
        try:
            gls_count = len(client.table("gls_parcels").select("id", count="exact").execute().data)
            sameday_count = len(client.table("sameday_parcels").select("id", count="exact").execute().data)
            netopia_count = len(client.table("netopia_transactions").select("id", count="exact").execute().data)
            invoices_count = len(client.table("invoices").select("id", count="exact").execute().data)
            mt940_count = len(client.table("bank_transactions").select("id", count="exact").execute().data)

            # Borderouri GLS din email
            try:
                borderouri_count = len(client.table("gls_borderouri").select("id", count="exact").execute().data)
                borderouri_matched = len(client.table("gls_borderouri").select("id", count="exact").eq("op_matched", True).execute().data)
            except:
                borderouri_count = 0
                borderouri_matched = 0

            st.markdown("""
            <div class="section-header">
                <span class="section-title">Date Disponibile in Supabase</span>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("GLS Colete", gls_count)
            with col2:
                st.metric("GLS Borderouri", borderouri_count, f"{borderouri_matched} potrivite" if borderouri_count > 0 else None)
            with col3:
                st.metric("Sameday", sameday_count)
            with col4:
                st.metric("Netopia", netopia_count)
            with col5:
                st.metric("Facturi Oblio", invoices_count)
            with col6:
                st.metric("Tranzactii MT940", mt940_count)

            if gls_count == 0 and sameday_count == 0:
                st.warning("Nu exista date in Supabase. Mergi la **Sincronizare Date** pentru a descarca datele.")

            if borderouri_count == 0:
                st.info("**TIP**: Sincronizeaza borderourile GLS din email pentru matching precis cu OP-urile bancare. Mergi la **Sincronizare Date** -> **Borderouri GLS din Email**.")
        except Exception as e:
            st.warning(f"Nu s-a putut verifica baza de date: {e}")

    st.markdown("---")

    # Period selection - by month
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Selecteaza Luna</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    from datetime import date, timedelta
    import calendar
    today = date.today()

    # Generate list of months (last 24 months)
    months_list = []
    for i in range(24):
        month_date = today.replace(day=1) - timedelta(days=i*30)
        month_date = month_date.replace(day=1)
        month_name = month_date.strftime("%B %Y")  # e.g., "December 2024"
        months_list.append((month_name, month_date))

    # Remove duplicates and sort
    seen = set()
    unique_months = []
    for name, dt in months_list:
        key = dt.strftime("%Y-%m")
        if key not in seen:
            seen.add(key)
            unique_months.append((name, dt))

    month_names = [m[0] for m in unique_months]
    month_dates = {m[0]: m[1] for m in unique_months}

    selected_month = st.selectbox(
        "Luna pentru export",
        options=month_names,
        index=0,
        key="proc_month"
    )

    # Calculate start and end date for selected month
    selected_date = month_dates[selected_month]
    start_date = selected_date.replace(day=1)
    last_day = calendar.monthrange(selected_date.year, selected_date.month)[1]
    end_date = selected_date.replace(day=last_day)

    st.markdown("---")

    # Optional Gomag file
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Fisier Gomag (Optional)</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("Fisierul Gomag este folosit pentru a potrivi AWB-urile cu Order ID-urile. Daca nu il incarci, Order ID-urile vor fi goale.")

    gomag_file = st.file_uploader(
        "Fisier Gomag (XLSX)",
        type=['xlsx'],
        key="gomag",
        help="Exportul comenzilor din Gomag"
    )

    st.markdown("---")

    # Generate button
    if st.button("GENEREAZA EXPORT OP-URI", use_container_width=True, type="primary"):
        with st.spinner("Se genereaza raportul..."):
            try:
                # Read Gomag if provided
                gomag_df = None
                if gomag_file:
                    gomag_df = pd.read_excel(gomag_file, dtype=str)
                    st.info(f"Gomag incarcat: {len(gomag_df)} randuri")

                # Generate export
                excel_buffer = generate_opuri_export(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    gomag_df
                )

                st.success("Export generat cu succes!")

                # Download button
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="DESCARCA RAPORT EXCEL",
                    data=excel_buffer,
                    file_name=f"opuri_export_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"Eroare la generare: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


# NOTE: process_files function removed - now using opuri_processor.generate_opuri_export()


def show_incasari():
    """Pagina cu incasarile MT940."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Incasari MT940</h1>
        <p class="page-subtitle">Vizualizare extrase bancare procesate</p>
    </div>
    """, unsafe_allow_html=True)

    if 'incasari_mt940' not in st.session_state or not st.session_state['incasari_mt940']:
        st.info("Nu exista incasari procesate. Mergi la 'Procesare Facturi' pentru a incarca fisierele MT940.")
        return

    incasari = st.session_state['incasari_mt940']

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Incasari", len(incasari))
    with col2:
        total_suma = sum(i[1] for i in incasari)
        st.metric("Suma Totala", f"{total_suma:,.2f} RON")
    with col3:
        surse = {}
        for i in incasari:
            sursa = get_sursa_incasare(i[4])
            surse[sursa] = surse.get(sursa, 0) + 1
        st.metric("Surse", len(surse))

    st.markdown("---")

    # Filter
    surse_disponibile = list(set(get_sursa_incasare(i[4]) for i in incasari))
    sursa_filter = st.multiselect("Filtreaza dupa sursa", surse_disponibile, default=surse_disponibile)

    # Table
    data = []
    for op_ref, suma, data_op, batchid, details in incasari:
        sursa = get_sursa_incasare(details)
        if sursa in sursa_filter:
            data.append({
                'Data': data_op,
                'Referinta OP': op_ref,
                'Sursa': sursa,
                'Suma': f"{suma:,.2f} RON",
                'BatchID': batchid or '-'
            })

    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nu exista incasari pentru filtrele selectate.")


def show_setari():
    """Pagina de setari."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Setari</h1>
        <p class="page-subtitle">Configurare si informatii despre aplicatie</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="section-header">
        <span class="section-title">Informatii Aplicatie</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    **Ultimate Facturi OBSID**
    Versiune: 2.0.0

    Aplicatie pentru procesarea si gruparea facturilor cu sincronizare automata:
    - **GLS**: Colete cu ramburs din API MyGLS
    - **Sameday**: Colete cu ramburs din API Sameday
    - **Netopia**: Rapoarte decontare din email
    - **Oblio**: Facturi sincronizate din API
    - **MT940**: Extrase bancare Banca Transilvania
    """)

    st.markdown("""
    <div class="section-header">
        <span class="section-title">Despre</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    Aceasta aplicatie automatizeaza procesul de reconciliere a facturilor cu incasarile bancare.

    **Functionalitati:**
    - Parsare automata fisiere MT940 de la Banca Transilvania
    - Sincronizare automata colete GLS si Sameday din API
    - Sincronizare automata rapoarte Netopia din email
    - Sincronizare facturi Oblio din API
    - Grupare facturi pe OP-uri bancare
    - Export Excel cu toate datele procesate
    """)


def show_profit_dashboard():
    """Pagina cu profit pe zile/luni/ani + Top Produse."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Profit Dashboard</h1>
        <p class="page-subtitle">Vizualizare profit pe perioade de timp</p>
    </div>
    """, unsafe_allow_html=True)

    # Tabs pentru diferite vizualizari
    tab1, tab2 = st.tabs(["Evolutie Profit", "Top Produse"])

    with tab1:
        show_profit_evolution_tab()

    with tab2:
        show_top_products_tab()


def show_profit_evolution_tab():
    """Tab cu evolutia profitului pe perioade."""
    # Period selector
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        period = st.selectbox("Perioada", ["Lunar", "Zilnic", "Anual"], key="profit_period")
    with col2:
        from datetime import date, timedelta
        default_start = date.today() - timedelta(days=365)
        start_date = st.date_input("De la", value=default_start, key="profit_start")
    with col3:
        end_date = st.date_input("Pana la", value=date.today(), key="profit_end")

    # Map period to group_by
    group_map = {"Zilnic": "day", "Lunar": "month", "Anual": "year"}
    group_by = group_map[period]

    try:
        # Get profit data from Supabase
        profit_data = get_profit_data(start_date, end_date, group_by)

        if not profit_data:
            st.info("Nu exista date in baza de date. Sincronizeaza datele MT940 din pagina 'Sincronizare Date'.")
            return

        # Prepare data for chart
        dates = [d['date'] for d in profit_data]
        totals = [d['total'] for d in profit_data]

        # Summary metrics
        total_sum = sum(totals)
        avg_sum = total_sum / len(totals) if totals else 0
        max_sum = max(totals) if totals else 0
        min_sum = min(totals) if totals else 0

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Perioada</div>
                <div class="metric-value gold">{total_sum:,.2f} RON</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Medie {period.lower()}</div>
                <div class="metric-value">{avg_sum:,.2f} RON</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Maxim</div>
                <div class="metric-value">{max_sum:,.2f} RON</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Minim</div>
                <div class="metric-value">{min_sum:,.2f} RON</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Main chart
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Evolutie Profit</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dates,
            y=totals,
            marker_color='#3fb950',
            name='Profit'
        ))
        fig.update_layout(
            plot_bgcolor='#0d1117',
            paper_bgcolor='#0d1117',
            font=dict(family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', color='#8b949e'),
            xaxis=dict(
                gridcolor='#30363d',
                tickfont=dict(color='#8b949e', size=11),
                tickangle=-45,  # Rotire etichete pentru spațiu mai bun
                automargin=True  # Margin automat pentru etichete
            ),
            yaxis=dict(
                gridcolor='#30363d',
                tickfont=dict(color='#8b949e', size=11),
                title='RON',
                tickformat=',.0f',  # Format numeric complet, fără K/M
                automargin=True
            ),
            margin=dict(l=60, r=40, t=40, b=80),  # Margini mai mari pentru etichete
            showlegend=False,
            hoverlabel=dict(
                bgcolor='#21262d',
                font_size=12,
                font_family='Inter, sans-serif'
            )
        )
        st.plotly_chart(fig, use_container_width=True)

        # Breakdown by source
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Distributie pe Surse</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        # Aggregate by source
        source_totals = {}
        for d in profit_data:
            for source, amount in d.get('by_source', {}).items():
                source_totals[source] = source_totals.get(source, 0) + amount

        if source_totals:
            col1, col2 = st.columns([1, 1])

            with col1:
                # Pie chart
                fig_pie = go.Figure(data=[go.Pie(
                    labels=list(source_totals.keys()),
                    values=list(source_totals.values()),
                    hole=0.4,
                    marker=dict(colors=['#3fb950', '#58a6ff', '#8b949e', '#f85149', '#c9d1d9'])
                )])
                fig_pie.update_layout(
                    plot_bgcolor='#0d1117',
                    paper_bgcolor='#0d1117',
                    font=dict(family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', color='#8b949e'),
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=True,
                    legend=dict(font=dict(color='#8b949e', size=11)),
                    hoverlabel=dict(
                        bgcolor='#21262d',
                        font_size=12,
                        font_family='Inter, sans-serif'
                    )
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                # Table
                source_data = [
                    {"Sursa": k, "Total": f"{v:,.2f} RON", "Procent": f"{v/total_sum*100:.1f}%"}
                    for k, v in sorted(source_totals.items(), key=lambda x: x[1], reverse=True)
                ]
                st.dataframe(pd.DataFrame(source_data), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Eroare la incarcarea datelor: {str(e)}")
        st.info("Asigura-te ca conexiunea la Supabase este configurata corect.")


def show_top_products_tab():
    """Tab cu Top Produse Vandute si Marja de Profit."""
    import plotly.express as px
    from utils.supabase_client import get_supabase_client

    supabase = get_supabase_client()

    # Verificam daca exista date in tabela products
    products_check = supabase.table('products').select('id').limit(1).execute()
    sales_check = supabase.table('product_sales').select('id').limit(1).execute()

    if not products_check.data and not sales_check.data:
        st.info("""
        **Nu exista date despre produse.**

        Pentru a vedea Top Produse, trebuie sa sincronizezi produsele din facturile Oblio.

        Apasa butonul de mai jos pentru a sincroniza.
        """)

        if st.button("Sincronizeaza Produsele Acum", type="primary", key="sync_products_btn"):
            try:
                from utils.product_sync import sync_product_sales

                with st.spinner("Se sincronizeaza produsele din Oblio..."):
                    progress_placeholder = st.empty()

                    def update_progress(msg):
                        progress_placeholder.info(msg)

                    stats = sync_product_sales(progress_callback=update_progress)

                progress_placeholder.empty()
                st.success(f"""
                Sincronizare completa:
                - Facturi procesate: {stats['invoices_processed']}
                - Produse sincronizate: {stats['products_synced']}
                - Vanzari inregistrate: {stats['sales_inserted']}
                """)

                if stats['errors']:
                    with st.expander(f"⚠️ {len(stats['errors'])} erori"):
                        for err in stats['errors'][:20]:
                            st.caption(err)

                st.rerun()
            except Exception as e:
                st.error(f"Eroare la sincronizare: {e}")
        return

    # Filtre
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        period = st.selectbox(
            "Perioada",
            ["Tot timpul", "Luna curenta", "Trimestru", "An"],
            key="products_period"
        )

    with col2:
        sort_by = st.selectbox(
            "Sortare dupa",
            ["Valoare", "Cantitate", "Marja %"],
            key="products_sort"
        )

    with col3:
        if st.button("Resincronizeaza Produse", key="resync_products"):
            try:
                from utils.product_sync import sync_product_sales
                with st.spinner("Se sincronizeaza..."):
                    stats = sync_product_sales()
                st.success(f"Sincronizate {stats['sales_inserted']} vanzari din {stats['invoices_processed']} facturi")
                st.rerun()
            except Exception as e:
                st.error(f"Eroare: {e}")

    # Incarca datele
    products_df = load_top_products_data(period, sort_by)

    if products_df.empty:
        st.warning("Nu exista vanzari pentru perioada selectata.")
        return

    # Top 3 Produse - Metrici
    st.subheader("Top 3 Produse")
    cols = st.columns(3)

    for i, col in enumerate(cols):
        if i < len(products_df):
            prod = products_df.iloc[i]
            with col:
                medal = ["🥇", "🥈", "🥉"][i]
                name = prod.get('name', 'N/A')
                if len(str(name)) > 25:
                    name = str(name)[:25] + "..."

                qty = prod.get('total_quantity_sold', 0) or 0
                rev = prod.get('total_revenue', 0) or 0

                st.metric(
                    f"{medal} {name}",
                    f"{qty:,.0f} buc",
                    f"{rev:,.2f} RON"
                )

    st.markdown("---")

    # Grafic Top 10
    st.subheader("Top 10 dupa Vanzari")

    top_10 = products_df.head(10).copy()

    if not top_10.empty:
        top_10['display_name'] = top_10['name'].apply(
            lambda x: str(x)[:20] + '...' if len(str(x)) > 20 else str(x)
        )

        has_margin = 'profit_margin' in top_10.columns and top_10['profit_margin'].notna().any()

        if has_margin:
            fig = px.bar(
                top_10,
                x='display_name',
                y='total_revenue',
                color='profit_margin',
                color_continuous_scale='RdYlGn',
                labels={
                    'display_name': 'Produs',
                    'total_revenue': 'Venituri (RON)',
                    'profit_margin': 'Marja %'
                }
            )
        else:
            fig = px.bar(
                top_10,
                x='display_name',
                y='total_revenue',
                labels={
                    'display_name': 'Produs',
                    'total_revenue': 'Venituri (RON)'
                }
            )
            fig.update_traces(marker_color='#3fb950')

        fig.update_layout(
            plot_bgcolor='#0d1117',
            paper_bgcolor='#0d1117',
            font=dict(family='Inter, sans-serif', color='#8b949e'),
            xaxis_tickangle=-45,
            margin=dict(l=40, r=40, t=40, b=80)
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tabel complet
    st.subheader("Toate Produsele")

    display_cols = ['sku', 'name', 'total_quantity_sold', 'total_revenue']
    if 'avg_selling_price' in products_df.columns:
        display_cols.append('avg_selling_price')
    if 'purchase_price' in products_df.columns:
        display_cols.append('purchase_price')
    if 'profit_margin' in products_df.columns:
        display_cols.append('profit_margin')

    display_df = products_df[[c for c in display_cols if c in products_df.columns]].copy()

    column_names = {
        'sku': 'SKU',
        'name': 'Produs',
        'total_quantity_sold': 'Cantitate',
        'total_revenue': 'Venituri (RON)',
        'avg_selling_price': 'Pret Mediu',
        'purchase_price': 'Pret Achizitie',
        'profit_margin': 'Marja %'
    }
    display_df = display_df.rename(columns=column_names)

    for col in ['Venituri (RON)', 'Pret Mediu', 'Pret Achizitie']:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) else "-"
            )

    if 'Cantitate' in display_df.columns:
        display_df['Cantitate'] = display_df['Cantitate'].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "-"
        )

    if 'Marja %' in display_df.columns:
        display_df['Marja %'] = display_df['Marja %'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "⚠️ Lipsa"
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Warning pentru produse fara pret achizitie
    if 'purchase_price' in products_df.columns:
        no_price = products_df[products_df['purchase_price'].isna()]
        if not no_price.empty:
            st.warning(f"""
            ⚠️ **{len(no_price)} produse** nu au pret de achizitie setat.
            Fara pretul de achizitie nu se poate calcula marja de profit.
            """)


def load_top_products_data(period: str, sort_by: str) -> pd.DataFrame:
    """Incarca produsele din Supabase cu filtre si sortare."""
    from utils.supabase_client import get_supabase_client
    from datetime import datetime

    supabase = get_supabase_client()

    try:
        sort_column = {
            'Cantitate': 'total_quantity_sold',
            'Valoare': 'total_revenue',
            'Marja %': 'profit_margin'
        }.get(sort_by, 'total_revenue')

        response = supabase.table('products').select(
            'sku, name, category, purchase_price, avg_selling_price, '
            'total_quantity_sold, total_revenue, profit_margin, last_sale_date'
        ).order(sort_column, desc=True).execute()

        if not response.data:
            return pd.DataFrame()

        df = pd.DataFrame(response.data)

        # Filtrare pe perioada
        if period != 'Tot timpul' and 'last_sale_date' in df.columns:
            df['last_sale_date'] = pd.to_datetime(df['last_sale_date'])
            now = datetime.now()

            if period == 'Luna curenta':
                start_date = now.replace(day=1)
            elif period == 'Trimestru':
                quarter_start_month = ((now.month - 1) // 3) * 3 + 1
                start_date = now.replace(month=quarter_start_month, day=1)
            elif period == 'An':
                start_date = now.replace(month=1, day=1)
            else:
                start_date = None

            if start_date:
                df = df[df['last_sale_date'] >= start_date]

        return df

    except Exception as e:
        st.error(f"Eroare la incarcarea produselor: {e}")
        return pd.DataFrame()


def show_tracking_colete():
    """Pagina pentru tracking colete AWB - GLS si Sameday."""
    from datetime import datetime, timedelta
    from utils.supabase_client import get_supabase_client

    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Tracking Colete</h1>
        <p class="page-subtitle">Monitorizare status AWB-uri GLS si Sameday</p>
    </div>
    """, unsafe_allow_html=True)

    supabase = get_supabase_client()

    # Tabs pentru diferite vizualizari
    tab1, tab2, tab3, tab4 = st.tabs(["Colete Nelivrate", "Toate Coletele", "Verificare AWB", "Matching AWB-Facturi"])

    with tab1:
        show_undelivered_parcels_tab(supabase)

    with tab2:
        show_all_parcels_tab(supabase)

    with tab3:
        show_awb_check_tab()

    with tab4:
        show_awb_invoice_matching_tab(supabase)


def show_undelivered_parcels_tab(supabase):
    """Tab cu coletele nelivrate - verificare directa din API curieri."""
    from datetime import datetime, timedelta, date

    st.subheader("Colete Nelivrate - Verificare din API")

    st.info("""
    Aceasta functionalitate verifica statusul coletelor **direct din API-ul GLS**.
    Sunt afisate coletele expediate care **nu au fost inca livrate**.
    """)

    # Selectoare pentru interval - dropdown cu perioade predefinite
    col1, col2 = st.columns(2)
    with col1:
        period_options = {
            "Ultimele 7 zile": 7,
            "Ultimele 14 zile": 14,
            "Ultimele 30 zile": 30,
            "Ultimele 60 zile": 60,
            "Ultimele 90 zile": 90,
            "Ultimele 120 zile": 120
        }
        selected_period = st.selectbox(
            "Perioada (data expediere)",
            options=list(period_options.keys()),
            index=3,  # Default: Ultimele 60 zile
            key="period_select",
            help="GLS returneaza colete dupa data printarii etichetei"
        )
        days_back = period_options[selected_period]

    with col2:
        min_days_waiting = st.selectbox(
            "Filtru zile asteptare",
            options=[
                ("Toate coletele nelivrate", 0),
                ("Peste 1 zi", 1),
                ("Peste 3 zile", 3),
                ("Peste 5 zile", 5),
                ("Peste 7 zile", 7),
                ("Peste 14 zile", 14)
            ],
            format_func=lambda x: x[0],
            index=0,  # Default: Toate
            key="min_days_select"
        )[1]

    # Buton pentru verificare
    if st.button("Verifica Colete din API GLS", type="primary", key="check_undelivered"):
        try:
            from utils.gls_api import get_all_parcels_with_status, is_gls_configured

            if not is_gls_configured():
                st.error("GLS API nu este configurat. Verifica credentialele in Setari.")
                return

            # Progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()

            def update_progress(current, total):
                progress_bar.progress(current / total)
                status_text.text(f"Verificare colet {current}/{total}...")

            with st.spinner("Se incarca coletele din GLS..."):
                all_parcels = get_all_parcels_with_status(
                    days_back=days_back,
                    progress_callback=update_progress
                )

            progress_bar.empty()
            status_text.empty()

            # Separate delivered and undelivered
            today = datetime.now()
            undelivered = []
            delivered_count = 0

            for p in all_parcels:
                if p.get("is_delivered"):
                    delivered_count += 1
                else:
                    # Calculate days waiting
                    last_date = p.get("last_status_date")
                    if last_date:
                        days_waiting = (today - last_date).days
                    else:
                        days_waiting = days_back  # Assume max if no date

                    if days_waiting >= min_days_waiting:
                        undelivered.append({
                            'awb': p.get('parcel_number', ''),
                            'recipient': p.get('recipient_name', '-'),
                            'city': p.get('recipient_city', '-'),
                            'cod': float(p.get('cod_amount', 0) or 0),
                            'last_status': p.get('last_status', 'Necunoscut'),
                            'last_date': last_date.strftime('%Y-%m-%d %H:%M') if last_date else '-',
                            'days_waiting': days_waiting,
                            'client_ref': p.get('client_reference', '')
                        })

            # Statistics
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Colete Verificate", len(all_parcels))
            with col2:
                st.metric("Livrate", delivered_count)
            with col3:
                st.metric("NELIVRATE", len(undelivered), delta=f"-{len(undelivered)}" if undelivered else None, delta_color="inverse")
            with col4:
                total_cod_blocked = sum(p['cod'] for p in undelivered)
                st.metric("COD Blocat", f"{total_cod_blocked:,.2f} RON")

            st.markdown("---")

            if undelivered:
                # Sort by days waiting descending
                undelivered.sort(key=lambda x: x['days_waiting'], reverse=True)

                st.error(f"**{len(undelivered)} colete** nu au fost livrate!")

                # Create dataframe
                df = pd.DataFrame(undelivered)
                df.columns = ['AWB', 'Destinatar', 'Oras', 'COD (RON)', 'Ultim Status', 'Data Status', 'Zile Asteptare', 'Ref. Client']

                # Highlight urgent rows
                def highlight_urgent(row):
                    days = row['Zile Asteptare']
                    if days >= 7:
                        return ['background-color: #ff4444; color: white'] * len(row)
                    elif days >= 5:
                        return ['background-color: #ff8800; color: white'] * len(row)
                    elif days >= 3:
                        return ['background-color: #ffcc00'] * len(row)
                    return [''] * len(row)

                st.dataframe(
                    df.style.apply(highlight_urgent, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

                # Recommended actions
                st.markdown("---")
                st.subheader("Actiuni Recomandate")
                st.markdown("""
                1. **Rosu (>7 zile)**: Contacteaza URGENT curierul - posibil colet pierdut sau refuzat
                2. **Portocaliu (5-7 zile)**: Verifica adresa si contacteaza destinatarul
                3. **Galben (3-5 zile)**: Monitorizare - posibil in curs de livrare
                """)

                # Export button
                if st.button("Exporta Lista Nelivrate", key="export_undelivered"):
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='Colete Nelivrate', index=False)
                    st.download_button(
                        "Descarca Excel",
                        buffer.getvalue(),
                        f"colete_nelivrate_{datetime.now().strftime('%Y%m%d')}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.success(f"Toate coletele din ultimele {days_back} zile au fost livrate!")

        except Exception as e:
            st.error(f"Eroare la verificare: {str(e)}")

    # Show cached results info
    st.markdown("---")
    st.caption("Nota: Verificarea se face in timp real din API-ul GLS. Poate dura cateva minute pentru multe colete.")


def show_all_parcels_tab(supabase):
    """Tab cu toate coletele."""
    from datetime import datetime

    st.subheader("Toate Coletele")

    # Filtre
    col1, col2, col3 = st.columns(3)
    with col1:
        courier_filter = st.selectbox("Curier", ["Toate", "GLS", "Sameday"], key="courier_filter")
    with col2:
        status_filter = st.selectbox("Status", ["Toate", "Livrate", "Nelivrate"], key="status_filter")
    with col3:
        month_filter = st.selectbox("Luna", ["Toate"] + [f"2025-{str(i).zfill(2)}" for i in range(12, 0, -1)], key="month_filter")

    # Query GLS
    gls_query = supabase.table('gls_parcels').select('*')
    if status_filter == "Livrate":
        gls_query = gls_query.eq('is_delivered', True)
    elif status_filter == "Nelivrate":
        gls_query = gls_query.eq('is_delivered', False)
    if month_filter != "Toate":
        gls_query = gls_query.eq('sync_month', month_filter)

    gls_data = gls_query.order('delivery_date', desc=True).limit(200).execute() if courier_filter in ["Toate", "GLS"] else None

    # Query Sameday
    sameday_query = supabase.table('sameday_parcels').select('*')
    if status_filter == "Livrate":
        sameday_query = sameday_query.eq('is_delivered', True)
    elif status_filter == "Nelivrate":
        sameday_query = sameday_query.eq('is_delivered', False)
    if month_filter != "Toate":
        sameday_query = sameday_query.eq('sync_month', month_filter)

    sameday_data = sameday_query.order('delivery_date', desc=True).limit(200).execute() if courier_filter in ["Toate", "Sameday"] else None

    # Combina datele
    all_parcels = []

    if gls_data and gls_data.data:
        for p in gls_data.data:
            all_parcels.append({
                'Curier': 'GLS',
                'AWB': p.get('parcel_number', ''),
                'Destinatar': p.get('recipient_name', '-'),
                'Oras': p.get('recipient_city', '-'),
                'COD': float(p.get('cod_amount', 0) or 0),
                'Data': p.get('delivery_date', ''),
                'Status': 'Livrat' if p.get('is_delivered') else 'In tranzit',
                'Luna': p.get('sync_month', '')
            })

    if sameday_data and sameday_data.data:
        for p in sameday_data.data:
            all_parcels.append({
                'Curier': 'Sameday',
                'AWB': p.get('awb_number', ''),
                'Destinatar': '-',
                'Oras': p.get('county', '-'),
                'COD': float(p.get('cod_amount', 0) or 0),
                'Data': p.get('delivery_date', ''),
                'Status': 'Livrat' if p.get('is_delivered') else p.get('status', 'In tranzit'),
                'Luna': p.get('sync_month', '')
            })

    if not all_parcels:
        st.info("Nu exista colete pentru filtrele selectate.")
    else:
        # Statistici
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Colete", len(all_parcels))
        with col2:
            delivered = len([p for p in all_parcels if p['Status'] == 'Livrat'])
            st.metric("Livrate", delivered)
        with col3:
            not_delivered = len([p for p in all_parcels if p['Status'] != 'Livrat'])
            st.metric("Nelivrate", not_delivered)
        with col4:
            total_cod = sum(p['COD'] for p in all_parcels)
            st.metric("Total COD", f"{total_cod:,.2f} RON")

        st.markdown("---")

        # Tabel
        df = pd.DataFrame(all_parcels)
        st.dataframe(df, use_container_width=True, hide_index=True)


def show_awb_check_tab():
    """Tab pentru verificare status AWB individual."""
    st.subheader("Verificare Status AWB")

    st.info("Introdu un numar AWB pentru a vedea statusul detaliat de la curier.")

    col1, col2 = st.columns([2, 1])
    with col1:
        awb_number = st.text_input("Numar AWB", placeholder="Ex: 1234567890", key="check_awb")
    with col2:
        courier = st.selectbox("Curier", ["GLS", "Sameday"], key="check_courier")

    if st.button("Verifica Status", type="primary", key="check_btn"):
        if not awb_number:
            st.warning("Introdu un numar AWB.")
        else:
            with st.spinner("Se verifica statusul..."):
                try:
                    if courier == "GLS":
                        from utils.gls_api import get_parcel_status, is_gls_configured

                        if not is_gls_configured():
                            st.error("GLS API nu este configurat. Verifica credentialele in Setari.")
                        else:
                            status = get_parcel_status(awb_number.strip())

                            if 'error' in status:
                                st.error(f"Eroare: {status['error']}")
                            else:
                                # Afiseaza informatii
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("AWB", status.get('parcel_number', awb_number))
                                with col2:
                                    if status.get('is_delivered'):
                                        st.success("LIVRAT")
                                    else:
                                        st.warning("IN TRANZIT")

                                if status.get('delivery_date'):
                                    st.write(f"**Data livrare:** {status['delivery_date']}")

                                if status.get('client_reference'):
                                    st.write(f"**Referinta client:** {status['client_reference']}")

                                # Istoric statusuri
                                if status.get('statuses'):
                                    st.markdown("---")
                                    st.subheader("Istoric Statusuri")
                                    for s in status['statuses']:
                                        with st.container():
                                            st.write(f"**{s.get('date', '')}** - {s.get('description', '')}")
                                            if s.get('info'):
                                                st.caption(s['info'])
                                            if s.get('depot'):
                                                st.caption(f"Depozit: {s['depot']}")
                                            st.divider()

                    else:  # Sameday
                        st.info("Verificarea pentru Sameday va fi disponibila in curand.")
                        # TODO: Implement Sameday status check

                except Exception as e:
                    st.error(f"Eroare la verificare: {str(e)}")


def show_awb_invoice_matching_tab(supabase):
    """Tab pentru matching AWB-uri cu facturi din Oblio."""
    from datetime import datetime
    from difflib import SequenceMatcher

    st.subheader("Matching AWB cu Facturi")
    st.info("Aceasta functionalitate identifica legatura dintre coletele trimise (AWB) si facturile din Oblio.")

    # Filtre
    col1, col2, col3 = st.columns(3)
    with col1:
        match_month = st.selectbox(
            "Luna",
            ["2025-12", "2025-11", "2025-10", "2025-09"],
            key="match_month"
        )
    with col2:
        match_status = st.selectbox(
            "Status Matching",
            ["Toate", "Matched", "Unmatched"],
            key="match_status"
        )
    with col3:
        match_tolerance = st.slider(
            "Toleranta suma (RON)",
            min_value=0.0,
            max_value=5.0,
            value=0.5,
            step=0.1,
            help="Diferenta maxima acceptata intre COD si valoare factura"
        )

    if st.button("Ruleaza Matching", type="primary", key="run_matching"):
        with st.spinner("Se proceseaza matching-ul..."):
            # Fetch parcels for the month
            gls_parcels = supabase.table('gls_parcels').select(
                'parcel_number, recipient_name, recipient_city, cod_amount, client_reference, delivery_date, is_delivered'
            ).eq('sync_month', match_month).execute()

            sameday_parcels = supabase.table('sameday_parcels').select(
                'awb_number, county, cod_amount, delivery_date, is_delivered'
            ).eq('sync_month', match_month).execute()

            # Fetch invoices for the same period (based on issue_date)
            year, month = match_month.split('-')
            start_date = f"{year}-{month}-01"
            if int(month) == 12:
                end_date = f"{int(year)+1}-01-01"
            else:
                end_date = f"{year}-{str(int(month)+1).zfill(2)}-01"

            invoices = supabase.table('invoices').select(
                'oblio_id, series_name, invoice_number, issue_date, total, client_name, client_city, is_canceled'
            ).gte('issue_date', start_date).lt('issue_date', end_date).eq('is_canceled', False).execute()

            # Convert to lists
            all_parcels = []
            for p in (gls_parcels.data or []):
                all_parcels.append({
                    'awb': p.get('parcel_number', ''),
                    'courier': 'GLS',
                    'recipient': p.get('recipient_name', ''),
                    'city': p.get('recipient_city', ''),
                    'cod': float(p.get('cod_amount', 0) or 0),
                    'reference': p.get('client_reference', ''),
                    'delivered': p.get('is_delivered', False),
                    'date': p.get('delivery_date', '')
                })

            for p in (sameday_parcels.data or []):
                all_parcels.append({
                    'awb': p.get('awb_number', ''),
                    'courier': 'Sameday',
                    'recipient': '',
                    'city': p.get('county', ''),
                    'cod': float(p.get('cod_amount', 0) or 0),
                    'reference': '',
                    'delivered': p.get('is_delivered', False),
                    'date': p.get('delivery_date', '')
                })

            all_invoices = []
            for inv in (invoices.data or []):
                all_invoices.append({
                    'invoice_id': inv.get('oblio_id', ''),
                    'series': inv.get('series_name', ''),
                    'number': inv.get('invoice_number', ''),
                    'date': inv.get('issue_date', ''),
                    'total': float(inv.get('total', 0) or 0),
                    'client': inv.get('client_name', ''),
                    'city': inv.get('client_city', '')
                })

            # Matching algorithm
            def normalize_name(name):
                """Normalizeaza numele pentru comparatie."""
                if not name:
                    return ""
                name = name.lower().strip()
                # Remove common prefixes/suffixes
                for word in ['s.r.l.', 'srl', 's.r.l', 'pfa', 'ii', 'i.i.']:
                    name = name.replace(word, '')
                return ' '.join(name.split())

            def name_similarity(name1, name2):
                """Calculeaza similaritatea intre doua nume."""
                return SequenceMatcher(None, normalize_name(name1), normalize_name(name2)).ratio()

            def match_parcels_to_invoices(parcels, invoices, tolerance):
                """Matching algoritm bazat pe suma COD si nume client."""
                matches = []
                used_invoices = set()

                for parcel in parcels:
                    best_match = None
                    best_score = 0

                    for inv in invoices:
                        if inv['invoice_id'] in used_invoices:
                            continue

                        score = 0

                        # Check COD amount match (within tolerance)
                        if abs(parcel['cod'] - inv['total']) <= tolerance:
                            score += 50  # 50 points for amount match

                            # Bonus for exact match
                            if abs(parcel['cod'] - inv['total']) < 0.01:
                                score += 20

                        # Check city match
                        if parcel['city'] and inv['city']:
                            if parcel['city'].lower().strip() == inv['city'].lower().strip():
                                score += 20

                        # Check name similarity
                        if parcel['recipient'] and inv['client']:
                            similarity = name_similarity(parcel['recipient'], inv['client'])
                            score += similarity * 30  # Up to 30 points for name match

                        # Check if reference contains invoice number
                        if parcel['reference'] and inv['number']:
                            if inv['number'] in parcel['reference']:
                                score += 40

                        if score > best_score and score >= 50:  # Minimum 50 to consider a match
                            best_score = score
                            best_match = inv

                    if best_match:
                        used_invoices.add(best_match['invoice_id'])
                        matches.append({
                            'awb': parcel['awb'],
                            'courier': parcel['courier'],
                            'cod': parcel['cod'],
                            'recipient': parcel['recipient'],
                            'city': parcel['city'],
                            'delivered': parcel['delivered'],
                            'invoice_series': best_match['series'],
                            'invoice_number': best_match['number'],
                            'invoice_total': best_match['total'],
                            'invoice_client': best_match['client'],
                            'match_score': best_score,
                            'matched': True
                        })
                    else:
                        matches.append({
                            'awb': parcel['awb'],
                            'courier': parcel['courier'],
                            'cod': parcel['cod'],
                            'recipient': parcel['recipient'],
                            'city': parcel['city'],
                            'delivered': parcel['delivered'],
                            'invoice_series': '-',
                            'invoice_number': '-',
                            'invoice_total': 0,
                            'invoice_client': '-',
                            'match_score': 0,
                            'matched': False
                        })

                return matches

            # Run matching
            results = match_parcels_to_invoices(all_parcels, all_invoices, match_tolerance)

            # Filter based on status
            if match_status == "Matched":
                results = [r for r in results if r['matched']]
            elif match_status == "Unmatched":
                results = [r for r in results if not r['matched']]

            # Display results
            st.markdown("---")

            # Statistics
            total_parcels = len(all_parcels)
            matched_count = len([r for r in results if r['matched']])
            unmatched_count = len([r for r in results if not r['matched']])
            match_rate = (matched_count / total_parcels * 100) if total_parcels > 0 else 0

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Colete", total_parcels)
            with col2:
                st.metric("Matched", matched_count, delta=f"{match_rate:.1f}%")
            with col3:
                st.metric("Unmatched", unmatched_count)
            with col4:
                total_cod = sum(r['cod'] for r in results if r['matched'])
                st.metric("COD Matched", f"{total_cod:,.2f} RON")

            if results:
                st.markdown("---")
                st.subheader("Rezultate Matching")

                # Create display dataframe
                display_data = []
                for r in results:
                    display_data.append({
                        'AWB': r['awb'],
                        'Curier': r['courier'],
                        'COD': r['cod'],
                        'Destinatar': r['recipient'][:30] if r['recipient'] else '-',
                        'Oras': r['city'],
                        'Livrat': 'Da' if r['delivered'] else 'Nu',
                        'Factura': f"{r['invoice_series']}{r['invoice_number']}" if r['matched'] else '-',
                        'Total Factura': r['invoice_total'] if r['matched'] else 0,
                        'Client Factura': r['invoice_client'][:30] if r['invoice_client'] and r['invoice_client'] != '-' else '-',
                        'Scor': r['match_score'],
                        'Status': 'Matched' if r['matched'] else 'Unmatched'
                    })

                df = pd.DataFrame(display_data)

                # Color code by match status
                def highlight_status(row):
                    if row['Status'] == 'Matched':
                        return ['background-color: #c8e6c9'] * len(row)
                    else:
                        return ['background-color: #ffcdd2'] * len(row)

                st.dataframe(
                    df.style.apply(highlight_status, axis=1),
                    use_container_width=True,
                    hide_index=True
                )

                # Export option
                if st.button("Exporta Rezultate Excel", key="export_matching"):
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name='AWB-Invoice Matching', index=False)

                    st.download_button(
                        label="Descarca Excel",
                        data=buffer.getvalue(),
                        file_name=f"matching_{match_month}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

            else:
                st.info("Nu exista date pentru luna selectata.")

    # Help section
    with st.expander("Cum functioneaza matching-ul?"):
        st.markdown("""
        **Algoritmul de matching foloseste urmatoarele criterii:**

        1. **Suma COD vs Total Factura** (pondere: 50 puncte)
           - Coletele sunt potrivite cu facturi care au valoare similara
           - Toleranta configurabila (implicit 0.50 RON)

        2. **Oras livrare vs Oras client** (pondere: 20 puncte)
           - Match daca orasul din colet corespunde cu orasul din factura

        3. **Nume destinatar vs Nume client** (pondere: 30 puncte)
           - Similaritate fuzzy intre numele destinatarului si clientul din factura

        4. **Referinta client contine numar factura** (pondere: 40 puncte)
           - Daca referinta GLS contine numarul facturii

        **Scor minim pentru match:** 50 puncte
        """)


def show_data_sync():
    """Pagina pentru sincronizare date cu Supabase."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Sincronizare Date</h1>
        <p class="page-subtitle">Sincronizare automata GLS, Sameday, Netopia, Oblio din API-uri</p>
    </div>
    """, unsafe_allow_html=True)

    # Import all required modules
    imap_available = False
    gls_available = False
    sameday_available = False

    try:
        from utils.email_imap import is_imap_configured, test_imap_connection, get_all_netopia_batch_ids
        from utils.netopia_api import (
            sync_netopia_batch,
            test_netopia_connection,
            save_netopia_transactions_to_supabase,
            save_netopia_batch_to_supabase,
            is_batch_already_synced,
            get_synced_batches_for_month
        )
        imap_available = True
    except ImportError as e:
        pass

    try:
        from utils.gls_api import (
            is_gls_configured,
            test_gls_connection,
            get_delivered_parcels_with_cod,
            save_gls_parcels_to_supabase,
            get_existing_gls_parcels
        )
        gls_available = True
    except ImportError as e:
        pass

    try:
        from utils.sameday_api import (
            is_sameday_configured,
            test_sameday_connection,
            get_sameday_deliveries_with_cod as get_sameday_parcels,
            save_sameday_parcels_to_supabase,
            get_existing_sameday_parcels
        )
        sameday_available = True
    except ImportError as e:
        pass

    # Connection status
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Status Conexiuni</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        supabase_ok = test_supabase()
        if supabase_ok:
            st.success("Supabase: Conectat")
        else:
            st.error("Supabase: Deconectat")

    with col2:
        oblio_ok = test_oblio()
        if oblio_ok:
            st.success("Oblio API: Conectat")
        else:
            st.error("Oblio API: Deconectat")

    with col3:
        if imap_available:
            if is_imap_configured():
                imap_ok = test_imap_connection()
                if imap_ok:
                    st.success("Email IMAP: Conectat")
                else:
                    st.error("Email IMAP: Eroare conectare")
            else:
                st.warning("Email IMAP: Neconfigurat")
        else:
            st.error("Email IMAP: Indisponibil")

    with col4:
        if imap_available:
            netopia_ok = test_netopia_connection()
            if netopia_ok:
                st.success("Netopia API: Configurat")
            else:
                st.warning("Netopia API: Neconfigurat")
        else:
            st.error("Netopia API: Indisponibil")

    with col5:
        if gls_available:
            if is_gls_configured():
                st.success("GLS API: Configurat")
            else:
                st.warning("GLS API: Neconfigurat")
        else:
            st.error("GLS API: Indisponibil")

    with col6:
        if sameday_available:
            if is_sameday_configured():
                st.success("Sameday API: Configurat")
            else:
                st.warning("Sameday API: Neconfigurat")
        else:
            st.error("Sameday API: Indisponibil")

    st.markdown("---")

    # ============================================
    # SINCRONIZARE TOTALA - Un singur buton pentru tot
    # ============================================
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Sincronizare Totala (Recomandat)</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    **Un singur click sincronizeaza toate sursele de date:**
    - **GLS**: Colete livrate cu ramburs (ultimele 60 zile)
    - **Sameday**: Colete livrate cu ramburs (ultimele 30 zile)
    - **Netopia**: Rapoarte de decontare din email (ultimele 60 zile)
    - **Oblio**: Facturi emise (ultimele 60 zile)

    **Duplicatele sunt ignorate automat** - datele existente nu se suprascriu.
    """)

    # Show existing data counts
    from utils.supabase_client import get_supabase_client
    client = get_supabase_client()
    if client:
        try:
            gls_count = len(client.table("gls_parcels").select("id", count="exact").execute().data)
            sameday_count = len(client.table("sameday_parcels").select("id", count="exact").execute().data)
            netopia_count = len(client.table("netopia_transactions").select("id", count="exact").execute().data)
            invoices_count = len(client.table("invoices").select("id", count="exact").execute().data)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Colete GLS", gls_count)
            with col2:
                st.metric("Colete Sameday", sameday_count)
            with col3:
                st.metric("Tranzactii Netopia", netopia_count)
            with col4:
                st.metric("Facturi Oblio", invoices_count)
        except:
            pass

    from datetime import date, timedelta

    if st.button("SINCRONIZARE TOTALA", key="btn_sync_all", use_container_width=True, type="primary"):
        progress = st.progress(0)
        status = st.empty()
        results = st.container()

        total_stats = {
            'gls_inserted': 0, 'gls_skipped': 0,
            'sameday_inserted': 0, 'sameday_skipped': 0,
            'netopia_inserted': 0, 'netopia_skipped': 0,
            'oblio_inserted': 0,
            'errors': []
        }

        # 1. Sincronizare GLS (25%)
        if gls_available and is_gls_configured():
            status.text("Sincronizare GLS...")
            try:
                parcels = get_delivered_parcels_with_cod(days_back=60)
                if parcels:
                    stats = save_gls_parcels_to_supabase(parcels)
                    total_stats['gls_inserted'] = stats.get('inserted', 0)
                    total_stats['gls_skipped'] = stats.get('skipped', 0)
                    total_stats['errors'].extend(stats.get('errors', []))
            except Exception as e:
                total_stats['errors'].append(f"GLS: {str(e)}")
        progress.progress(25)

        # 2. Sincronizare Sameday (50%)
        if sameday_available and is_sameday_configured():
            status.text("Sincronizare Sameday (poate dura cateva minute)...")
            try:
                parcels = get_sameday_parcels(days_back=30)
                if parcels:
                    stats = save_sameday_parcels_to_supabase(parcels)
                    total_stats['sameday_inserted'] = stats.get('inserted', 0)
                    total_stats['sameday_skipped'] = stats.get('skipped', 0)
                    total_stats['errors'].extend(stats.get('errors', []))
            except Exception as e:
                total_stats['errors'].append(f"Sameday: {str(e)}")
        progress.progress(50)

        # 3. Sincronizare Netopia (75%)
        if imap_available and is_imap_configured():
            status.text("Sincronizare Netopia din email...")
            try:
                batch_ids = get_all_netopia_batch_ids(days_back=60)
                netopia_key = os.getenv('NETOPIA_API_KEY', '')
                if batch_ids and netopia_key:
                    for batch in batch_ids:
                        batch_id = batch['batch_id']
                        if is_batch_already_synced(batch_id):
                            total_stats['netopia_skipped'] += 1
                            continue

                        result = sync_netopia_batch(batch.get('report_id', batch_id), netopia_key)
                        if result['success']:
                            save_netopia_transactions_to_supabase(
                                result['transactions'],
                                batch_id,
                                batch.get('report_month', '')
                            )
                            save_netopia_batch_to_supabase({
                                'batch_id': batch_id,
                                'report_id': batch.get('report_id', batch_id),
                                'date': batch.get('date', ''),
                                'subject': batch.get('subject', ''),
                                'report_month': batch.get('report_month', ''),
                                'count': result['count'],
                                'total_amount': result['total_amount'],
                                'total_fees': result['total_fees'],
                                'net_amount': result['net_amount']
                            })
                            total_stats['netopia_inserted'] += 1
            except Exception as e:
                total_stats['errors'].append(f"Netopia: {str(e)}")
        progress.progress(75)

        # 4. Sincronizare Oblio (100%)
        if oblio_ok:
            status.text("Sincronizare Oblio...")
            try:
                oblio_start = date.today() - timedelta(days=60)
                oblio_end = date.today()
                stats = sync_oblio_invoices(oblio_start, oblio_end)
                total_stats['oblio_inserted'] = stats.get('inserted', 0)
                total_stats['errors'].extend(stats.get('errors', []))
            except Exception as e:
                total_stats['errors'].append(f"Oblio: {str(e)}")
        progress.progress(100)

        status.text("Sincronizare completa!")

        # Display results
        with results:
            st.success("Sincronizare finalizata!")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("GLS", f"+{total_stats['gls_inserted']}", f"{total_stats['gls_skipped']} existente")
            with col2:
                st.metric("Sameday", f"+{total_stats['sameday_inserted']}", f"{total_stats['sameday_skipped']} existente")
            with col3:
                st.metric("Netopia", f"+{total_stats['netopia_inserted']}", f"{total_stats['netopia_skipped']} existente")
            with col4:
                st.metric("Oblio", f"+{total_stats['oblio_inserted']}")

            if total_stats['errors']:
                with st.expander(f"Erori ({len(total_stats['errors'])})"):
                    for err in total_stats['errors'][:20]:
                        st.warning(err)

    st.markdown("---")

    # ============================================
    # Sincronizare Produse din Facturi
    # ============================================
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Sincronizare Produse din Facturi</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    **Extrage produsele din facturile Oblio pentru analiza Top Produse.**
    - Extrage toate produsele din facturile existente
    - Calculeaza cantitatea vanduta si veniturile per produs
    - Permite setarea preturilor de achizitie pentru calculul marjei
    """)

    # Afișează statistici curente
    try:
        from utils.data_sync import get_product_stats
        prod_stats = get_product_stats()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Produse", prod_stats['total_products'])
        with col2:
            st.metric("Cu pret achizitie", prod_stats['products_with_price'])
        with col3:
            st.metric("Vanzari inregistrate", prod_stats['total_sales'])

        if prod_stats['last_sync']:
            st.caption(f"Ultima sincronizare: {prod_stats['last_sync']}")
    except Exception:
        st.caption("Nu exista date de sincronizare")

    if st.button("Sincronizare Produse din Oblio", key="btn_sync_products", use_container_width=True, disabled=not supabase_ok):
        try:
            from utils.product_sync import sync_product_sales

            progress = st.progress(0)
            status = st.empty()

            def update_progress(msg):
                status.info(msg)

            with st.spinner("Se sincronizeaza produsele..."):
                stats = sync_product_sales(progress_callback=update_progress)

            progress.progress(100)
            status.empty()

            st.success(f"""
            Sincronizare completa:
            - Facturi procesate: {stats['invoices_processed']}
            - Produse sincronizate: {stats['products_synced']}
            - Vanzari inregistrate: {stats['sales_inserted']}
            """)

            if stats['errors']:
                with st.expander(f"Erori ({len(stats['errors'])})"):
                    for err in stats['errors'][:20]:
                        st.warning(err)
        except Exception as e:
            st.error(f"Eroare la sincronizare: {e}")

    # Import prețuri achiziție din Excel
    st.markdown("---")
    with st.expander("Import Preturi Achizitie din Excel"):
        st.markdown("""
        **Importa preturile de achizitie pentru calculul marjei de profit.**

        Formatul Excel necesar:
        | SKU | Pret Achizitie |
        |-----|----------------|
        | ABC123 | 45.50 |

        Coloanele acceptate: `SKU`, `Cod`, `Code` pentru cod produs si `Pret Achizitie`, `Pret`, `Price`, `Cost` pentru pret.
        """)

        prices_file = st.file_uploader(
            "Incarca Excel cu preturi",
            type=['xlsx', 'xls'],
            key="prices_excel_upload"
        )

        if prices_file:
            try:
                df_prices = pd.read_excel(prices_file)
                st.write("Preview date:")
                st.dataframe(df_prices.head(10), use_container_width=True, hide_index=True)

                if st.button("Importa Preturile", key="btn_import_prices", type="primary"):
                    from utils.product_sync import import_purchase_prices_from_excel

                    with st.spinner("Se importa preturile..."):
                        result = import_purchase_prices_from_excel(df_prices)

                    if result['updated'] > 0:
                        st.success(f"Actualizate {result['updated']} produse cu preturi de achizitie")

                    if result.get('not_found', 0) > 0:
                        st.warning(f"{result['not_found']} SKU-uri nu au fost gasite in nomenclator. Sincronizeaza mai intai produsele din Oblio.")

                    if result['errors']:
                        with st.expander(f"Erori ({len(result['errors'])})"):
                            for err in result['errors'][:20]:
                                st.caption(err)
            except Exception as e:
                st.error(f"Eroare la citirea fisierului: {e}")

    st.markdown("---")

    # ============================================
    # Import Extrase Bancare (MT940 sau PDF)
    # ============================================
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Import Extrase Bancare (MT940 sau PDF)</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    Importa tranzactiile bancare din extrase Banca Transilvania. Poti incarca:
    - **Fisiere CSV** (.csv) - extras descarcat din BT24 (recomandat)
    - **Fisiere MT940** (.txt) - format standard bancar
    - **Extrase PDF** (.pdf) - extras de cont descarcat din BT24

    **Duplicatele sunt ignorate automat** - tranzactiile cu aceeasi referinta nu se vor dubla, indiferent de sursa (CSV, MT940 sau PDF).
    """)

    bank_files_upload = st.file_uploader(
        "Incarca extrase bancare (CSV, MT940 sau PDF)",
        type=['csv', 'txt', 'pdf'],
        accept_multiple_files=True,
        key="sync_bank_files"
    )

    if st.button("Import Extrase Bancare", key="btn_import_bank", use_container_width=True, disabled=not supabase_ok):
        if bank_files_upload:
            with st.spinner("Se importa tranzactiile..."):
                total_stats = {
                    'processed': 0,
                    'inserted': 0,
                    'skipped': 0,
                    'errors': []
                }

                for bank_file in bank_files_upload:
                    file_name = bank_file.name
                    file_ext = file_name.lower().split('.')[-1]

                    try:
                        if file_ext == 'csv':
                            # Import CSV
                            from utils.bank_statement_parser import BankStatementParser
                            from utils.supabase_client import get_supabase_client
                            import hashlib

                            parser = BankStatementParser()
                            content = bank_file.read()
                            result = parser.parse_file(content, file_name)

                            if 'error' in result and result['error']:
                                total_stats['errors'].append(f"{file_name}: {result['error']}")
                                continue

                            transactions = result.get('transactions', [])
                            supabase = get_supabase_client()

                            for trans in transactions:
                                total_stats['processed'] += 1

                                # Generate unique hash for deduplication
                                referinta = trans.get('referinta', '')
                                trans_data = trans.get('data')
                                suma = trans.get('suma', 0)

                                if trans_data:
                                    date_str = trans_data.strftime('%Y-%m-%d')
                                else:
                                    date_str = ''

                                hash_data = f"{date_str}|{referinta}|{suma}"
                                trans_hash = hashlib.md5(hash_data.encode()).hexdigest()

                                # Check if exists by hash (safe, no special char issues)
                                existing = supabase.table('bank_transactions').select('id').eq(
                                    'transaction_hash', trans_hash
                                ).execute()

                                if existing.data:
                                    total_stats['skipped'] += 1
                                    continue

                                # Insert transaction
                                record = {
                                    'op_reference': referinta,
                                    'transaction_date': date_str,
                                    'amount': suma,
                                    'source': trans.get('category', ''),
                                    'details': trans.get('descriere', ''),
                                    'file_name': file_name,
                                    'transaction_hash': trans_hash,
                                    'is_income': trans.get('is_income', False),
                                    'is_capital_transfer': trans.get('is_capital_transfer', False),
                                }

                                try:
                                    supabase.table('bank_transactions').insert(record).execute()
                                    total_stats['inserted'] += 1
                                except Exception as insert_err:
                                    if 'duplicate' in str(insert_err).lower():
                                        total_stats['skipped'] += 1
                                    else:
                                        total_stats['errors'].append(f"{trans['referinta']}: {str(insert_err)}")

                        elif file_ext == 'pdf':
                            # Import PDF
                            from utils.pdf_parser import parse_bt_pdf_from_bytes, save_pdf_transactions_to_supabase

                            transactions = parse_bt_pdf_from_bytes(bank_file)
                            stats = save_pdf_transactions_to_supabase(transactions, file_name)

                            total_stats['processed'] += stats.get('processed', 0)
                            total_stats['inserted'] += stats.get('inserted', 0)
                            total_stats['skipped'] += stats.get('skipped', 0)
                            total_stats['errors'].extend(stats.get('errors', []))

                        elif file_ext == 'txt':
                            # Import MT940
                            with tempfile.TemporaryDirectory() as tmpdir:
                                file_path = os.path.join(tmpdir, file_name)
                                with open(file_path, 'wb') as f:
                                    f.write(bank_file.getbuffer())

                                stats = import_mt940_to_supabase(tmpdir, [file_name])

                                total_stats['processed'] += stats.get('processed', 0)
                                total_stats['inserted'] += stats.get('inserted', 0)
                                total_stats['skipped'] += stats.get('skipped', 0)
                                total_stats['errors'].extend(stats.get('errors', []))

                    except Exception as e:
                        total_stats['errors'].append(f"Eroare la {file_name}: {str(e)}")

                st.success("Import finalizat!")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Procesate", total_stats['processed'])
                with col_b:
                    st.metric("Inserate", total_stats['inserted'])
                with col_c:
                    st.metric("Ignorate (duplicate)", total_stats['skipped'])

                if total_stats['errors']:
                    with st.expander(f"Erori ({len(total_stats['errors'])})"):
                        for err in total_stats['errors'][:10]:
                            st.warning(err)
        else:
            st.warning("Incarca fisiere CSV, MT940 sau PDF pentru import")

    # ============================================
    # Sincronizare Borderouri GLS din Email
    # ============================================
    st.markdown("---")
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Borderouri GLS din Email</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    st.info("""
    **Sincronizeaza borderourile GLS (desfasuratoare de ramburs) din email.**
    - Cauta email-uri de la GLS cu subiect "Lista Colete cu Ramburs COD list"
    - Descarca fisierele XLSX atasate
    - Extrage coletele si sumele din borderou
    - Potriveste automat cu OP-urile bancare existente
    """)

    # Import GLS borderou module
    gls_borderou_available = False
    try:
        from utils.gls_borderou_imap import (
            sync_gls_borderouri_from_email,
            match_borderouri_with_bank_transactions,
            get_borderouri_status
        )
        gls_borderou_available = True
    except ImportError as e:
        st.warning(f"Modul GLS Borderou indisponibil: {e}")

    if gls_borderou_available:
        # Show current status
        try:
            status = get_borderouri_status()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Borderouri", status['total'])
            with col2:
                st.metric("Potrivite cu OP", status['matched'], f"{status['matched_amount']:.2f} RON")
            with col3:
                st.metric("Nepotrivite", status['unmatched'], f"{status['unmatched_amount']:.2f} RON")
        except Exception as e:
            st.warning(f"Nu s-a putut obtine statusul borderourilor: {e}")

        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            if st.button("Sincronizare Borderouri din Email", key="btn_sync_gls_borderou", use_container_width=True):
                with st.spinner("Se cauta email-uri GLS si se descarca borderouri..."):
                    try:
                        stats = sync_gls_borderouri_from_email(days_back=60)
                        st.success("Sincronizare completa!")
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Email-uri gasite", stats['emails_found'])
                        with col_b:
                            st.metric("Borderouri noi", stats['borderouri_inserted'])
                        with col_c:
                            st.metric("Ignorate (duplicate)", stats['borderouri_skipped'])

                        if stats['errors']:
                            with st.expander(f"Erori ({len(stats['errors'])})"):
                                for err in stats['errors'][:10]:
                                    st.warning(err)
                    except Exception as e:
                        st.error(f"Eroare la sincronizare: {e}")

        with col_btn2:
            if st.button("Potrivire Borderouri cu OP-uri", key="btn_match_gls_borderou", use_container_width=True):
                with st.spinner("Se potrivesc borderourile cu tranzactiile bancare..."):
                    try:
                        match_stats = match_borderouri_with_bank_transactions()
                        st.success("Matching complet!")
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Potrivite", match_stats['borderouri_matched'])
                        with col_b:
                            st.metric("Nepotrivite", match_stats['borderouri_unmatched'])

                        if match_stats['matches']:
                            with st.expander("Borderouri potrivite"):
                                for m in match_stats['matches']:
                                    st.write(f"- {m['borderou_date']}: {m['amount']:.2f} RON -> OP {m['op_reference']} ({m['op_date']})")

                        if match_stats['unmatched']:
                            with st.expander("Borderouri nepotrivite (necesita OP)"):
                                for u in match_stats['unmatched']:
                                    st.write(f"- {u['borderou_date']}: {u['amount']:.2f} RON ({u['parcels_count']} colete)")
                    except Exception as e:
                        st.error(f"Eroare la matching: {e}")

    # Sync logs
    st.markdown("---")
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Istoric Sincronizari</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    try:
        logs = get_recent_sync_logs(10)
        if logs:
            log_data = []
            for log in logs:
                log_data.append({
                    'Data': log.get('started_at', '-')[:19].replace('T', ' ') if log.get('started_at') else '-',
                    'Tip': log.get('sync_type', '-'),
                    'Status': log.get('status', '-'),
                    'Procesate': log.get('records_processed', 0),
                    'Inserate': log.get('records_inserted', 0),
                    'Ignorate': log.get('records_skipped', 0)
                })
            st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
        else:
            st.info("Nu exista sincronizari anterioare.")
    except Exception as e:
        st.warning(f"Nu s-a putut incarca istoricul: {str(e)}")

    # ============================================
    # Vizualizare Date Sincronizate
    # ============================================
    st.markdown("---")
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Vizualizare Date Sincronizate</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    view_tab = st.selectbox(
        "Alege ce vrei sa vezi:",
        ["Colete GLS", "Colete Sameday", "Tranzactii Netopia", "Facturi Oblio", "Tranzactii MT940", "Borderouri GLS"],
        key="view_data_tab"
    )

    try:
        if view_tab == "Colete GLS":
            result = client.table("gls_parcels").select("*").order("delivery_date", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                # Selecteaza coloanele relevante
                display_cols = ['parcel_number', 'cod_amount', 'recipient_name', 'recipient_city', 'delivery_date', 'is_delivered']
                display_cols = [c for c in display_cols if c in df.columns]
                df_display = df[display_cols] if display_cols else df
                df_display.columns = ['Nr. Colet', 'Suma COD', 'Destinatar', 'Oras', 'Data Livrare', 'Livrat'] if len(display_cols) == 6 else df_display.columns
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Afisate ultimele {len(df)} colete (din total {len(result.data)})")
            else:
                st.info("Nu exista colete GLS sincronizate.")

        elif view_tab == "Colete Sameday":
            result = client.table("sameday_parcels").select("*").order("delivery_date", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                display_cols = ['awb_number', 'cod_amount', 'county', 'delivery_date', 'is_delivered', 'status']
                display_cols = [c for c in display_cols if c in df.columns]
                df_display = df[display_cols] if display_cols else df
                df_display.columns = ['AWB', 'Suma COD', 'Judet', 'Data Livrare', 'Livrat', 'Status'] if len(display_cols) == 6 else df_display.columns
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Afisate ultimele {len(df)} colete")
            else:
                st.info("Nu exista colete Sameday sincronizate.")

        elif view_tab == "Tranzactii Netopia":
            result = client.table("netopia_transactions").select("*").order("synced_at", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                display_cols = ['order_id', 'amount', 'fee', 'net_amount', 'payment_date', 'batch_id']
                display_cols = [c for c in display_cols if c in df.columns]
                df_display = df[display_cols] if display_cols else df
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Afisate ultimele {len(df)} tranzactii")
            else:
                st.info("Nu exista tranzactii Netopia sincronizate.")

        elif view_tab == "Facturi Oblio":
            result = client.table("invoices").select("*").order("synced_at", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"Afisate ultimele {len(df)} facturi")
            else:
                st.info("Nu exista facturi Oblio sincronizate.")

        elif view_tab == "Tranzactii MT940":
            result = client.table("bank_transactions").select("*").order("date", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                display_cols = ['date', 'reference', 'amount', 'description', 'transaction_type']
                display_cols = [c for c in display_cols if c in df.columns]
                df_display = df[display_cols] if display_cols else df
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Afisate ultimele {len(df)} tranzactii bancare")
            else:
                st.info("Nu exista tranzactii MT940 importate.")

        elif view_tab == "Borderouri GLS":
            result = client.table("gls_borderouri").select("*").order("borderou_date", desc=True).limit(100).execute()
            if result.data:
                df = pd.DataFrame(result.data)
                # Format display columns
                df_display = df[['borderou_date', 'total_amount', 'parcels_count', 'op_matched', 'op_reference', 'op_date']].copy()
                df_display.columns = ['Data Borderou', 'Total (RON)', 'Nr. Colete', 'Potrivit', 'Referinta OP', 'Data OP']
                df_display['Potrivit'] = df_display['Potrivit'].apply(lambda x: 'Da' if x else 'Nu')
                df_display['Referinta OP'] = df_display['Referinta OP'].fillna('-')
                df_display['Data OP'] = df_display['Data OP'].fillna('-')
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                st.caption(f"Afisate {len(df)} borderouri")

                # Show parcels for selected borderou
                with st.expander("Detalii colete din borderouri"):
                    borderou_options = {f"{row['borderou_date']} - {row['total_amount']:.2f} RON": row['id'] for _, row in df.iterrows()}
                    selected_borderou = st.selectbox("Selecteaza borderou:", list(borderou_options.keys()))
                    if selected_borderou:
                        borderou_id = borderou_options[selected_borderou]
                        parcels_result = client.table("gls_borderou_parcels").select("*").eq("borderou_id", borderou_id).execute()
                        if parcels_result.data:
                            parcels_df = pd.DataFrame(parcels_result.data)
                            parcels_display = parcels_df[['parcel_number', 'cod_amount', 'recipient_name']].copy()
                            parcels_display.columns = ['Nr. Colet', 'Suma COD', 'Destinatar']
                            st.dataframe(parcels_display, use_container_width=True, hide_index=True)
                        else:
                            st.info("Nu sunt colete pentru acest borderou.")
            else:
                st.info("Nu exista borderouri GLS sincronizate.")

    except Exception as e:
        st.warning(f"Nu s-au putut incarca datele: {str(e)}")


if __name__ == "__main__":
    main()

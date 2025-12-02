"""
Ultimate Facturi OBSID - Dashboard Web
Aplicatie Streamlit pentru procesarea si gruparea facturilor
"""

import streamlit as st
import pandas as pd
import os
import tempfile
import shutil
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import utils
from utils.auth import login_form, logout, is_authenticated, get_user_name, check_auth_for_action
from utils.mt940_parser import extrage_referinte_op_din_mt940_folder, get_sursa_incasare
from utils.processors import proceseaza_borderouri_gls, proceseaza_borderouri_sameday, proceseaza_netopia
from utils.export import genereaza_export_excel
from utils.data_sync import (
    import_mt940_to_supabase,
    sync_oblio_invoices,
    get_profit_data,
    get_dashboard_stats,
    get_recent_sync_logs,
    get_transactions_for_period,
    get_invoices_for_period
)
from utils.supabase_client import test_connection as test_supabase
from utils.oblio_api import test_connection as test_oblio
import plotly.express as px
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
    /* Import VCR OSD Mono font */
    @import url('https://db.onlinewebfonts.com/c/2545d122b16126676225a5b52283ae23?family=VCR+OSD+Mono');

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

    /* Typography - VCR OSD Mono for everything */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'VCR OSD Mono', monospace !important;
        color: var(--text-primary) !important;
        letter-spacing: 0.05em;
    }

    h1 {
        font-size: 1.75rem !important;
        font-weight: 400 !important;
        color: var(--text-primary) !important;
        margin-bottom: 0.5rem !important;
    }

    h2 {
        font-size: 1.25rem !important;
        font-weight: 400 !important;
        color: var(--text-primary) !important;
    }

    h3 {
        font-size: 1rem !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    p, span, div, label {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-size: 1.125rem;
        font-weight: 400;
        color: var(--text-primary);
        letter-spacing: 0.05em;
        line-height: 1.2;
    }

    .brand-tagline {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-weight: 400;
        font-size: 1rem;
        color: var(--text-primary);
    }

    .user-details {
        flex: 1;
    }

    .user-name {
        font-family: 'VCR OSD Mono', monospace;
        font-weight: 400;
        font-size: 0.875rem;
        color: var(--text-primary);
        line-height: 1.3;
    }

    .user-role {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-size: 1.5rem;
        font-weight: 400;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
        letter-spacing: 0.05em;
    }

    .page-subtitle {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-size: 0.625rem;
        font-weight: 400;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace !important;
        font-weight: 400 !important;
        color: var(--text-secondary) !important;
    }

    /* Primary action buttons - GitHub style */
    .stButton > button {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-size: 1.5rem;
        color: var(--text-primary);
    }

    [data-testid="stMetricLabel"] {
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
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
        font-family: 'VCR OSD Mono', monospace;
        font-weight: 400;
        font-size: 0.875rem;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .action-desc {
        font-family: 'VCR OSD Mono', monospace;
        font-size: 0.75rem;
        color: var(--text-muted);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def main():
    # Initialize session state for auth
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.name = None

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

        # User profile - show visitor or logged in user
        user_name = get_user_name()
        user_initial = user_name[0].upper() if user_name else 'V'
        user_role = "Administrator" if is_authenticated() else "Vizualizare"
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

        # Initialize current page
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"

        # Navigation items without emojis
        nav_items = [
            ("Dashboard", "Vedere generala"),
            ("Profit Dashboard", "Profit zilnic/lunar/anual"),
            ("Raport OP-uri", "Export contabilitate"),
            ("Procesare Facturi", "Incarca si proceseaza"),
            ("Incasari MT940", "Extrase bancare"),
            ("Sincronizare Date", "Oblio si MT940"),
            ("Setari", "Configurare")
        ]

        for page_name, _ in nav_items:
            is_active = st.session_state.current_page == page_name

            if is_active:
                st.markdown('<div class="nav-active">', unsafe_allow_html=True)

            if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                st.session_state.current_page = page_name
                st.rerun()

            if is_active:
                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        # Login/Logout at bottom
        st.markdown("---")
        st.markdown('<div class="logout-section">', unsafe_allow_html=True)
        if is_authenticated():
            if st.button("Deconectare", key="logout_btn", use_container_width=True):
                logout()
        else:
            if st.button("Autentificare", key="login_btn", use_container_width=True):
                st.session_state.show_login = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Show login form if requested
    if st.session_state.get('show_login', False) and not is_authenticated():
        login_form()
        st.session_state.show_login = False
        return

    # Main content
    page = st.session_state.get('current_page', 'Dashboard')

    if page == "Dashboard":
        show_dashboard()
    elif page == "Profit Dashboard":
        show_profit_dashboard()
    elif page == "Raport OP-uri":
        show_raport_opuri()
    elif page == "Procesare Facturi":
        show_procesare()
    elif page == "Incasari MT940":
        show_incasari()
    elif page == "Sincronizare Date":
        show_data_sync()
    elif page == "Setari":
        show_setari()


def show_dashboard():
    """Pagina principala cu sumar."""
    # Page header
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Vedere generala asupra procesarii facturilor si incasarilor</p>
    </div>
    """, unsafe_allow_html=True)

    # Get stored data
    incasari = st.session_state.get('incasari_mt940', [])
    rezultate_gls = st.session_state.get('rezultate_gls', [])
    rezultate_sameday = st.session_state.get('rezultate_sameday', [])

    total_facturi = len(rezultate_gls) + len(rezultate_sameday)
    total_incasari = len(incasari)
    total_suma = sum(i[1] for i in incasari) if incasari else 0

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Facturi Procesate</div>
            <div class="metric-value">{total_facturi}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Incasari MT940</div>
            <div class="metric-value">{total_incasari}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Incasari</div>
            <div class="metric-value gold">{total_suma:,.2f} RON</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        erori = len(st.session_state.get('erori', []))
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Erori</div>
            <div class="metric-value">{erori}</div>
        </div>
        """, unsafe_allow_html=True)

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
        if st.button("Procesare Noua", use_container_width=True, key="dash_process"):
            st.session_state.current_page = 'Procesare Facturi'
            st.rerun()

    with col2:
        if st.button("Vizualizeaza Incasari", use_container_width=True, key="dash_incasari"):
            st.session_state.current_page = 'Incasari MT940'
            st.rerun()

    with col3:
        if st.button("Export Raport", use_container_width=True, key="dash_export"):
            if not incasari:
                st.warning("Incarca mai intai fisierele pentru procesare")


def show_procesare():
    """Pagina de procesare facturi."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Procesare Facturi</h1>
        <p class="page-subtitle">Incarca fisierele necesare pentru reconcilierea facturilor</p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}

    # File uploads in columns
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Fisiere Obligatorii</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        gomag_file = st.file_uploader(
            "Fisier Gomag (XLSX)",
            type=['xlsx'],
            key="gomag",
            help="Exportul comenzilor din Gomag"
        )

        gls_files = st.file_uploader(
            "Borderouri GLS (XLSX)",
            type=['xlsx'],
            accept_multiple_files=True,
            key="gls",
            help="Borderourile GLS cu colete"
        )

        sameday_files = st.file_uploader(
            "Borderouri Sameday (XLSX)",
            type=['xlsx'],
            accept_multiple_files=True,
            key="sameday",
            help="Borderourile Sameday"
        )

    with col2:
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Extras Bancar</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        mt940_files = st.file_uploader(
            "Fisiere MT940 (TXT)",
            type=['txt'],
            accept_multiple_files=True,
            key="mt940",
            help="Extrasele bancare MT940 de la Banca Transilvania"
        )

        st.markdown("""
        <div class="section-header">
            <span class="section-title">Fisiere Optionale</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        netopia_files = st.file_uploader(
            "Fisiere Netopia (CSV)",
            type=['csv'],
            accept_multiple_files=True,
            key="netopia",
            help="Exporturile tranzactii Netopia"
        )

        oblio_file = st.file_uploader(
            "Fisier Oblio (XLS/XLSX)",
            type=['xls', 'xlsx'],
            key="oblio",
            help="Export facturi din Oblio"
        )

    st.markdown("---")

    # Process button
    can_process = gomag_file is not None and len(gls_files) > 0 and len(mt940_files) > 0

    if not can_process:
        st.warning("Incarca cel putin: Fisier Gomag, Borderouri GLS si Fisiere MT940")

    if st.button("Proceseaza Facturile", disabled=not can_process, use_container_width=True):
        with st.spinner("Se proceseaza..."):
            process_files(gomag_file, gls_files, sameday_files, mt940_files, netopia_files, oblio_file)


def process_files(gomag_file, gls_files, sameday_files, mt940_files, netopia_files, oblio_file):
    """Proceseaza toate fisierele incarcate."""
    progress = st.progress(0)
    status = st.empty()

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            status.text("Salvez fisierele temporar...")
            progress.progress(10)

            # Gomag
            gomag_path = os.path.join(tmpdir, "gomag.xlsx")
            with open(gomag_path, 'wb') as f:
                f.write(gomag_file.getbuffer())
            gomag_df = pd.read_excel(gomag_path, dtype=str)

            # GLS folder
            gls_folder = os.path.join(tmpdir, "gls")
            os.makedirs(gls_folder, exist_ok=True)
            for gls_file in gls_files:
                with open(os.path.join(gls_folder, gls_file.name), 'wb') as f:
                    f.write(gls_file.getbuffer())

            # Sameday folder
            sameday_folder = os.path.join(tmpdir, "sameday")
            os.makedirs(sameday_folder, exist_ok=True)
            for sd_file in sameday_files:
                with open(os.path.join(sameday_folder, sd_file.name), 'wb') as f:
                    f.write(sd_file.getbuffer())

            # MT940 folder
            mt940_folder = os.path.join(tmpdir, "mt940")
            os.makedirs(mt940_folder, exist_ok=True)
            for mt_file in mt940_files:
                with open(os.path.join(mt940_folder, mt_file.name), 'wb') as f:
                    f.write(mt_file.getbuffer())

            # Netopia folder
            netopia_folder = os.path.join(tmpdir, "netopia")
            os.makedirs(netopia_folder, exist_ok=True)
            if netopia_files:
                for np_file in netopia_files:
                    with open(os.path.join(netopia_folder, np_file.name), 'wb') as f:
                        f.write(np_file.getbuffer())

            progress.progress(30)
            status.text("Procesez incasarile MT940...")

            incasari_mt940 = extrage_referinte_op_din_mt940_folder(mt940_folder)
            st.session_state['incasari_mt940'] = incasari_mt940

            progress.progress(50)
            status.text("Procesez borderourile GLS...")

            rezultate_gls, erori_gls = proceseaza_borderouri_gls(gls_folder, gomag_df.copy())

            progress.progress(65)
            status.text("Procesez borderourile Sameday...")

            rezultate_sameday, erori_sameday = proceseaza_borderouri_sameday(sameday_folder, gomag_df.copy())

            progress.progress(80)
            status.text("Procesez Netopia...")

            rezultate_netopia, erori_netopia = proceseaza_netopia(netopia_folder, gomag_df.copy())

            progress.progress(90)
            status.text("Generez raportul Excel...")

            excel_buffer = genereaza_export_excel(
                rezultate_gls,
                rezultate_sameday,
                rezultate_netopia,
                incasari_mt940
            )

            progress.progress(100)
            status.text("Procesare finalizata!")

            st.success("Procesare finalizata cu succes!")

            # Statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Incasari MT940", len(incasari_mt940))
            with col2:
                st.metric("Borderouri GLS", len(rezultate_gls))
            with col3:
                st.metric("Borderouri Sameday", len(rezultate_sameday))
            with col4:
                total_suma = sum(i[1] for i in incasari_mt940)
                st.metric("Total Incasari", f"{total_suma:,.2f} RON")

            # Errors
            all_errors = erori_gls + erori_sameday + erori_netopia
            if all_errors:
                with st.expander(f"Erori ({len(all_errors)})", expanded=False):
                    for err in all_errors:
                        st.warning(err)

            # Download
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Descarca Raportul Excel",
                data=excel_buffer,
                file_name=f"facturi_grupate_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            st.session_state['rezultate_gls'] = rezultate_gls
            st.session_state['rezultate_sameday'] = rezultate_sameday
            st.session_state['rezultate_netopia'] = rezultate_netopia
            st.session_state['erori'] = all_errors

    except Exception as e:
        st.error(f"Eroare la procesare: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


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
    Versiune: 1.0.0

    Aplicatie pentru procesarea si gruparea facturilor din:
    - Borderouri GLS
    - Borderouri Sameday
    - Tranzactii Netopia
    - Extrase bancare MT940 (Banca Transilvania)
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
    - Potrivire AWB-uri din borderouri cu facturi din Gomag
    - Grupare facturi pe OP-uri bancare
    - Export Excel cu toate datele procesate
    """)


def show_profit_dashboard():
    """Pagina cu profit pe zile/luni/ani."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Profit Dashboard</h1>
        <p class="page-subtitle">Vizualizare profit pe perioade de timp</p>
    </div>
    """, unsafe_allow_html=True)

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
            font=dict(family='VCR OSD Mono, monospace', color='#8b949e'),
            xaxis=dict(
                gridcolor='#30363d',
                tickfont=dict(color='#8b949e')
            ),
            yaxis=dict(
                gridcolor='#30363d',
                tickfont=dict(color='#8b949e'),
                title='RON'
            ),
            margin=dict(l=40, r=40, t=40, b=40),
            showlegend=False
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
                    font=dict(family='VCR OSD Mono, monospace', color='#8b949e'),
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=True,
                    legend=dict(font=dict(color='#8b949e'))
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


def show_data_sync():
    """Pagina pentru sincronizare date cu Supabase."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Sincronizare Date</h1>
        <p class="page-subtitle">Import MT940 si sincronizare Oblio cu Supabase</p>
    </div>
    """, unsafe_allow_html=True)

    # Connection status
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Status Conexiuni</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
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

    st.markdown("---")

    # Two columns for sync options
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Import MT940</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        st.info("Importa tranzactiile bancare din fisierele MT940 in Supabase. Duplicatele sunt ignorate automat.")

        mt940_folder = st.text_input(
            "Folder MT940",
            value="",
            placeholder="C:\\path\\to\\mt940\\files",
            key="sync_mt940_folder"
        )

        mt940_files_upload = st.file_uploader(
            "Sau incarca fisiere MT940",
            type=['txt'],
            accept_multiple_files=True,
            key="sync_mt940_files"
        )

        if st.button("Import MT940", key="btn_import_mt940", use_container_width=True, disabled=not supabase_ok):
            if mt940_files_upload:
                with st.spinner("Se importa tranzactiile..."):
                    try:
                        with tempfile.TemporaryDirectory() as tmpdir:
                            file_names = []
                            for mt_file in mt940_files_upload:
                                file_path = os.path.join(tmpdir, mt_file.name)
                                with open(file_path, 'wb') as f:
                                    f.write(mt_file.getbuffer())
                                file_names.append(mt_file.name)

                            stats = import_mt940_to_supabase(tmpdir, file_names)

                        st.success(f"Import finalizat!")
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Procesate", stats['processed'])
                        with col_b:
                            st.metric("Inserate", stats['inserted'])
                        with col_c:
                            st.metric("Ignorate (duplicate)", stats['skipped'])

                        if stats['errors']:
                            with st.expander(f"Erori ({len(stats['errors'])})"):
                                for err in stats['errors'][:10]:
                                    st.warning(err)
                    except Exception as e:
                        st.error(f"Eroare la import: {str(e)}")
            elif mt940_folder:
                with st.spinner("Se importa tranzactiile..."):
                    try:
                        stats = import_mt940_to_supabase(mt940_folder)
                        st.success(f"Import finalizat!")
                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            st.metric("Procesate", stats['processed'])
                        with col_b:
                            st.metric("Inserate", stats['inserted'])
                        with col_c:
                            st.metric("Ignorate (duplicate)", stats['skipped'])
                    except Exception as e:
                        st.error(f"Eroare la import: {str(e)}")
            else:
                st.warning("Selecteaza un folder sau incarca fisiere MT940")

    with col2:
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Sincronizare Oblio</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        st.info("Sincronizeaza facturile din Oblio API in Supabase. Facturile existente sunt actualizate automat.")

        from datetime import date, timedelta
        default_start = date.today() - timedelta(days=30)

        col_date1, col_date2 = st.columns(2)
        with col_date1:
            oblio_start = st.date_input("De la data", value=default_start, key="oblio_start")
        with col_date2:
            oblio_end = st.date_input("Pana la data", value=date.today(), key="oblio_end")

        if st.button("Sincronizeaza Oblio", key="btn_sync_oblio", use_container_width=True, disabled=not (supabase_ok and oblio_ok)):
            with st.spinner("Se sincronizeaza facturile..."):
                try:
                    stats = sync_oblio_invoices(oblio_start, oblio_end)
                    st.success(f"Sincronizare finalizata!")
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("Procesate", stats['processed'])
                    with col_b:
                        st.metric("Inserate/Actualizate", stats['inserted'])
                    with col_c:
                        st.metric("Erori", stats['failed'])

                    if stats['errors']:
                        with st.expander(f"Erori ({len(stats['errors'])})"):
                            for err in stats['errors'][:10]:
                                st.warning(err)
                except Exception as e:
                    st.error(f"Eroare la sincronizare: {str(e)}")

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


def show_raport_opuri():
    """Pagina Raport OP-uri pentru contabilitate."""
    st.markdown("""
    <div class="page-header">
        <h1 class="page-title">Raport OP-uri</h1>
        <p class="page-subtitle">Raport pentru contabilitate - Export facturi grupate pe OP-uri</p>
    </div>
    """, unsafe_allow_html=True)

    # Period selector
    st.markdown("""
    <div class="section-header">
        <span class="section-title">Selecteaza Perioada</span>
        <div class="section-line"></div>
    </div>
    """, unsafe_allow_html=True)

    from datetime import date, timedelta

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        # Default to current month
        today = date.today()
        first_day_of_month = today.replace(day=1)
        start_date = st.date_input("De la", value=first_day_of_month, key="raport_start")
    with col2:
        end_date = st.date_input("Pana la", value=today, key="raport_end")
    with col3:
        # Quick period buttons
        st.write("")  # Spacing
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            if st.button("Luna curenta", key="btn_luna_curenta", use_container_width=True):
                st.session_state.raport_start = first_day_of_month
                st.session_state.raport_end = today
                st.rerun()
        with col_q2:
            if st.button("Luna trecuta", key="btn_luna_trecuta", use_container_width=True):
                last_month_end = first_day_of_month - timedelta(days=1)
                last_month_start = last_month_end.replace(day=1)
                st.session_state.raport_start = last_month_start
                st.session_state.raport_end = last_month_end
                st.rerun()
        with col_q3:
            if st.button("Tot anul", key="btn_tot_anul", use_container_width=True):
                st.session_state.raport_start = date(today.year, 1, 1)
                st.session_state.raport_end = today
                st.rerun()

    st.markdown("---")

    try:
        # Get transactions for the period
        transactions = get_transactions_for_period(start_date, end_date)
        invoices = get_invoices_for_period(start_date, end_date)

        if not transactions:
            st.info("Nu exista tranzactii bancare pentru perioada selectata. Importa date MT940 din pagina 'Sincronizare Date'.")
            return

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        total_suma = sum(float(t.get('amount', 0)) for t in transactions)
        total_tranzactii = len(transactions)
        total_facturi = len(invoices)

        # Count by source
        surse = {}
        for t in transactions:
            sursa = t.get('source', 'Altul')
            surse[sursa] = surse.get(sursa, 0) + 1

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Incasari</div>
                <div class="metric-value gold">{total_suma:,.2f} RON</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Tranzactii</div>
                <div class="metric-value">{total_tranzactii}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Facturi Oblio</div>
                <div class="metric-value">{total_facturi}</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Surse</div>
                <div class="metric-value">{len(surse)}</div>
            </div>
            """, unsafe_allow_html=True)

        # Data table section
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Tranzactii Bancare</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        # Build dataframe for display
        display_data = []
        for t in transactions:
            display_data.append({
                'Data OP': t.get('transaction_date', ''),
                'Numar OP': t.get('op_reference', ''),
                'Curier': t.get('source', ''),
                'Suma': f"{float(t.get('amount', 0)):,.2f} RON",
                'Detalii': (t.get('details', '') or '')[:50] + '...' if t.get('details') and len(t.get('details', '')) > 50 else t.get('details', '')
            })

        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Invoices section
        if invoices:
            st.markdown("""
            <div class="section-header">
                <span class="section-title">Facturi Oblio</span>
                <div class="section-line"></div>
            </div>
            """, unsafe_allow_html=True)

            inv_data = []
            for inv in invoices:
                inv_data.append({
                    'Data': inv.get('issue_date', ''),
                    'Serie': inv.get('series_name', ''),
                    'Numar': inv.get('invoice_number', ''),
                    'Client': inv.get('client_name', ''),
                    'Total': f"{float(inv.get('total', 0)):,.2f} RON",
                    'Tip': inv.get('invoice_type', ''),
                    'Incasata': 'DA' if inv.get('is_collected') else 'NU'
                })

            df_inv = pd.DataFrame(inv_data)
            st.dataframe(df_inv, use_container_width=True, hide_index=True)

        # Export section
        st.markdown("""
        <div class="section-header">
            <span class="section-title">Export</span>
            <div class="section-line"></div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            # Generate Excel for download
            from io import BytesIO
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill

            buffer = BytesIO()
            wb = Workbook()
            ws = wb.active
            ws.title = "OP-uri"

            # Headers matching opuri_export.xlsx format
            headers = ["Data OP", "Numar OP", "Nume Borderou", "Curier", "Order ID", "Numar Factura", "Suma", "Erori", "Diferenta eMag", "Facturi Comision eMag"]
            ws.append(headers)

            # Style header
            header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF")
            for col in range(1, len(headers) + 1):
                ws.cell(row=1, column=col).fill = header_fill
                ws.cell(row=1, column=col).font = header_font

            # Add transaction data
            for t in transactions:
                ws.append([
                    t.get('transaction_date', ''),
                    t.get('op_reference', ''),
                    t.get('file_name', ''),
                    t.get('source', ''),
                    '',  # Order ID - TODO: from matching
                    '',  # Numar Factura - TODO: from matching
                    float(t.get('amount', 0)),
                    'NU',
                    '',
                    ''
                ])

            wb.save(buffer)
            buffer.seek(0)

            timestamp = datetime.now().strftime("%Y%m%d")
            st.download_button(
                label="Descarca Raport Excel",
                data=buffer,
                file_name=f"opuri_export_{start_date}_{end_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        with col2:
            st.info("Raportul contine tranzactiile bancare din perioada selectata. Pentru matching complet cu facturi, proceseaza mai intai datele din pagina 'Procesare Facturi'.")

    except Exception as e:
        st.error(f"Eroare la incarcarea datelor: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()

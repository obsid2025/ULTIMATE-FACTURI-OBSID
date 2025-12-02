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
from utils.auth import login_form, logout
from utils.mt940_parser import extrage_referinte_op_din_mt940_folder, get_sursa_incasare
from utils.processors import proceseaza_borderouri_gls, proceseaza_borderouri_sameday, proceseaza_netopia
from utils.export import genereaza_export_excel

# Page config
st.set_page_config(
    page_title="Ultimate Facturi OBSID",
    page_icon="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS - Luxury Fintech Aesthetic
st.markdown("""
<style>
    /* Import premium fonts */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=DM+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* CSS Variables */
    :root {
        --bg-primary: #0a0a0b;
        --bg-secondary: #111113;
        --bg-tertiary: #18181b;
        --bg-card: #1c1c1f;
        --border-subtle: #27272a;
        --border-accent: #3f3f46;
        --text-primary: #fafafa;
        --text-secondary: #a1a1aa;
        --text-muted: #71717a;
        --accent-gold: #d4a853;
        --accent-gold-light: #e8c97a;
        --accent-gold-dark: #b8923f;
        --accent-emerald: #34d399;
        --accent-rose: #f43f5e;
        --accent-blue: #60a5fa;
        --shadow-gold: rgba(212, 168, 83, 0.15);
        --shadow-dark: rgba(0, 0, 0, 0.5);
    }

    /* Global resets */
    .main {
        background-color: var(--bg-primary);
        background-image:
            radial-gradient(ellipse at 20% 0%, rgba(212, 168, 83, 0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 80% 100%, rgba(212, 168, 83, 0.02) 0%, transparent 50%);
    }

    .stApp {
        background-color: var(--bg-primary);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
        border-right: 1px solid var(--border-subtle);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Playfair Display', Georgia, serif !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em;
    }

    h1 {
        font-size: 2.5rem !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, var(--text-primary) 0%, var(--accent-gold) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem !important;
    }

    h2 {
        font-size: 1.5rem !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
    }

    h3 {
        font-size: 1.125rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-family: 'DM Sans', sans-serif !important;
    }

    p, span, div, label {
        font-family: 'DM Sans', sans-serif;
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
        filter: drop-shadow(0 0 20px var(--shadow-gold));
    }

    .brand-text {
        display: flex;
        flex-direction: column;
    }

    .brand-name {
        font-family: 'Playfair Display', serif;
        font-size: 1.375rem;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .brand-tagline {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        color: var(--accent-gold);
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 500;
    }

    /* User profile section */
    .user-profile {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.875rem 1rem;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        margin: 0 0.5rem 1rem 0.5rem;
    }

    .user-avatar {
        width: 36px;
        height: 36px;
        background: linear-gradient(135deg, var(--accent-gold) 0%, var(--accent-gold-dark) 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'Playfair Display', serif;
        font-weight: 600;
        font-size: 1rem;
        color: var(--bg-primary);
    }

    .user-details {
        flex: 1;
    }

    .user-name {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        font-size: 0.875rem;
        color: var(--text-primary);
        line-height: 1.3;
    }

    .user-role {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.6875rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Navigation section */
    .nav-section {
        padding: 0 0.5rem;
    }

    .nav-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.6875rem;
        font-weight: 600;
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
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 2px;
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9375rem;
        font-weight: 500;
        text-align: left;
        justify-content: flex-start;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
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
        background: linear-gradient(90deg, var(--bg-card) 0%, transparent 100%) !important;
        color: var(--accent-gold) !important;
        border-left: 2px solid var(--accent-gold) !important;
        border-radius: 0 8px 8px 0 !important;
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
        background: rgba(244, 63, 94, 0.1) !important;
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
        font-family: 'Playfair Display', serif;
        font-size: 2.25rem;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }

    .page-subtitle {
        font-family: 'DM Sans', sans-serif;
        font-size: 1rem;
        color: var(--text-muted);
        margin: 0;
    }

    /* Metric cards - premium style */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--accent-gold) 0%, transparent 100%);
        opacity: 0;
        transition: opacity 0.3s ease;
    }

    .metric-card:hover {
        border-color: var(--border-accent);
        transform: translateY(-2px);
        box-shadow: 0 8px 24px var(--shadow-dark);
    }

    .metric-card:hover::before {
        opacity: 1;
    }

    .metric-label {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.75rem;
    }

    .metric-value {
        font-family: 'Playfair Display', serif;
        font-size: 2rem;
        font-weight: 600;
        color: var(--text-primary);
        line-height: 1;
        margin-bottom: 0.5rem;
    }

    .metric-value.gold {
        color: var(--accent-gold);
    }

    .metric-change {
        font-family: 'JetBrains Mono', monospace;
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
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8125rem;
        font-weight: 600;
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
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.2s ease;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--accent-gold);
        background: var(--bg-tertiary);
    }

    [data-testid="stFileUploader"] label {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
    }

    /* Primary action buttons */
    .stButton > button {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        font-size: 0.9375rem;
        letter-spacing: 0.02em;
        background: linear-gradient(135deg, var(--accent-gold) 0%, var(--accent-gold-dark) 100%);
        color: var(--bg-primary);
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 8px var(--shadow-gold);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 16px var(--shadow-gold);
        background: linear-gradient(135deg, var(--accent-gold-light) 0%, var(--accent-gold) 100%);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    .stButton > button:disabled {
        background: var(--bg-tertiary);
        color: var(--text-muted);
        box-shadow: none;
        cursor: not-allowed;
    }

    /* Download button special */
    .stDownloadButton > button {
        background: transparent;
        border: 1px solid var(--accent-gold);
        color: var(--accent-gold);
        box-shadow: none;
    }

    .stDownloadButton > button:hover {
        background: var(--accent-gold);
        color: var(--bg-primary);
    }

    /* Data tables */
    .stDataFrame {
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        overflow: hidden;
    }

    .stDataFrame [data-testid="stDataFrameResizable"] {
        background: var(--bg-secondary);
    }

    /* Alerts and messages */
    .stAlert {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        font-family: 'DM Sans', sans-serif;
    }

    .stAlert [data-testid="stMarkdownContainer"] p {
        color: var(--text-secondary);
    }

    /* Success state */
    .stSuccess {
        background: rgba(52, 211, 153, 0.1);
        border-color: var(--accent-emerald);
    }

    /* Warning state */
    .stWarning {
        background: rgba(212, 168, 83, 0.1);
        border-color: var(--accent-gold);
    }

    /* Error state */
    .stError {
        background: rgba(244, 63, 94, 0.1);
        border-color: var(--accent-rose);
    }

    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(90deg, var(--accent-gold) 0%, var(--accent-gold-light) 100%);
        border-radius: 4px;
    }

    .stProgress > div {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'DM Sans', sans-serif;
        font-weight: 500;
        color: var(--text-secondary);
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
    }

    .streamlit-expanderHeader:hover {
        color: var(--text-primary);
        border-color: var(--border-accent);
    }

    /* Multiselect */
    .stMultiSelect [data-baseweb="select"] {
        background: var(--bg-secondary);
        border: 1px solid var(--border-subtle);
        border-radius: 8px;
    }

    .stMultiSelect [data-baseweb="select"]:hover {
        border-color: var(--accent-gold);
    }

    /* Metrics from Streamlit */
    [data-testid="stMetricValue"] {
        font-family: 'Playfair Display', serif;
        font-size: 1.75rem;
        color: var(--text-primary);
    }

    [data-testid="stMetricLabel"] {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Info box styling */
    .info-box {
        background: var(--bg-card);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 1.5rem;
        font-family: 'DM Sans', sans-serif;
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
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    .action-card:hover {
        border-color: var(--accent-gold);
        background: var(--bg-tertiary);
    }

    .action-icon {
        width: 48px;
        height: 48px;
        margin: 0 auto 1rem auto;
        background: var(--bg-tertiary);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .action-title {
        font-family: 'DM Sans', sans-serif;
        font-weight: 600;
        font-size: 0.9375rem;
        color: var(--text-primary);
        margin-bottom: 0.25rem;
    }

    .action-desc {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.8125rem;
        color: var(--text-muted);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        login_form()
        return

    # Sidebar
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

        # User profile
        user_name = st.session_state.get('name', 'User')
        user_initial = user_name[0].upper() if user_name else 'U'
        st.markdown(f"""
        <div class="user-profile">
            <div class="user-avatar">{user_initial}</div>
            <div class="user-details">
                <div class="user-name">{user_name}</div>
                <div class="user-role">Administrator</div>
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
            ("Procesare Facturi", "Incarca si proceseaza"),
            ("Incasari MT940", "Extrase bancare"),
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

        # Logout at bottom
        st.markdown("---")
        st.markdown('<div class="logout-section">', unsafe_allow_html=True)
        if st.button("Deconectare", key="logout_btn", use_container_width=True):
            logout()
        st.markdown('</div>', unsafe_allow_html=True)

    # Main content
    page = st.session_state.get('current_page', 'Dashboard')

    if page == "Dashboard":
        show_dashboard()
    elif page == "Procesare Facturi":
        show_procesare()
    elif page == "Incasari MT940":
        show_incasari()
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


if __name__ == "__main__":
    main()

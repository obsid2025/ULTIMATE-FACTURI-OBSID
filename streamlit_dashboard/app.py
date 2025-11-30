"""
Ultimate Dashboard - Aplicație Streamlit pentru Dashboarding
UI Futuristic și Simplist cu Autentificare
"""

import streamlit as st
import hashlib
import json
from pathlib import Path
from datetime import datetime

# Configurare pagină
st.set_page_config(
    page_title="Ultimate Dashboard",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS pentru UI Futuristic
FUTURISTIC_CSS = """
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700&family=Rajdhani:wght@300;400;500;600;700&display=swap');

    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0f0f23 100%);
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    /* Typography */
    h1, h2, h3 {
        font-family: 'Orbitron', monospace !important;
        color: #00f0ff !important;
        text-shadow: 0 0 10px rgba(0, 240, 255, 0.5);
    }

    p, span, label, .stMarkdown {
        font-family: 'Rajdhani', sans-serif !important;
        color: #e0e0e0 !important;
    }

    /* Login container */
    .login-container {
        background: linear-gradient(145deg, rgba(20, 20, 40, 0.9), rgba(10, 10, 25, 0.95));
        border: 1px solid rgba(0, 240, 255, 0.3);
        border-radius: 20px;
        padding: 3rem;
        box-shadow:
            0 0 40px rgba(0, 240, 255, 0.1),
            inset 0 0 60px rgba(0, 240, 255, 0.05);
        backdrop-filter: blur(10px);
        max-width: 450px;
        margin: 5rem auto;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        background: rgba(0, 20, 40, 0.8) !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        border-radius: 10px !important;
        color: #00f0ff !important;
        font-family: 'Rajdhani', sans-serif !important;
        font-size: 1.1rem !important;
        padding: 0.8rem 1rem !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #00f0ff !important;
        box-shadow: 0 0 20px rgba(0, 240, 255, 0.3) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: rgba(0, 240, 255, 0.5) !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.2), rgba(0, 150, 200, 0.3)) !important;
        border: 1px solid #00f0ff !important;
        border-radius: 10px !important;
        color: #00f0ff !important;
        font-family: 'Orbitron', monospace !important;
        font-weight: 500 !important;
        padding: 0.8rem 2rem !important;
        transition: all 0.3s ease !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 240, 255, 0.4), rgba(0, 150, 200, 0.5)) !important;
        box-shadow: 0 0 30px rgba(0, 240, 255, 0.4) !important;
        transform: translateY(-2px) !important;
    }

    /* Metric cards */
    .metric-card {
        background: linear-gradient(145deg, rgba(20, 20, 40, 0.8), rgba(10, 10, 25, 0.9));
        border: 1px solid rgba(0, 240, 255, 0.2);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        transition: all 0.3s ease;
    }

    .metric-card:hover {
        border-color: rgba(0, 240, 255, 0.5);
        box-shadow: 0 0 25px rgba(0, 240, 255, 0.15);
    }

    .metric-value {
        font-family: 'Orbitron', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: #00f0ff;
        text-shadow: 0 0 15px rgba(0, 240, 255, 0.5);
    }

    .metric-label {
        font-family: 'Rajdhani', sans-serif;
        font-size: 1rem;
        color: rgba(224, 224, 224, 0.7);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a15 0%, #1a1a30 100%) !important;
        border-right: 1px solid rgba(0, 240, 255, 0.2) !important;
    }

    /* Navigation items */
    .nav-item {
        background: transparent;
        border: 1px solid transparent;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        margin: 0.3rem 0;
        cursor: pointer;
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 1rem;
    }

    .nav-item:hover {
        background: rgba(0, 240, 255, 0.1);
        border-color: rgba(0, 240, 255, 0.3);
    }

    .nav-item.active {
        background: rgba(0, 240, 255, 0.15);
        border-color: #00f0ff;
    }

    /* Glow effects */
    .glow-text {
        text-shadow: 0 0 10px currentColor;
    }

    /* Logo styling */
    .logo-container {
        text-align: center;
        margin-bottom: 2rem;
    }

    .logo-symbol {
        font-size: 4rem;
        color: #00f0ff;
        text-shadow:
            0 0 20px rgba(0, 240, 255, 0.8),
            0 0 40px rgba(0, 240, 255, 0.4);
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        background: rgba(0, 20, 40, 0.8) !important;
        border-radius: 10px !important;
    }

    /* Selectbox */
    .stSelectbox > div > div {
        background: rgba(0, 20, 40, 0.8) !important;
        border: 1px solid rgba(0, 240, 255, 0.3) !important;
        border-radius: 10px !important;
    }

    /* Divider */
    .cyber-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.5), transparent);
        margin: 2rem 0;
    }

    /* Status indicator */
    .status-online {
        width: 10px;
        height: 10px;
        background: #00ff88;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #00ff88;
        animation: blink 1.5s ease-in-out infinite;
    }

    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
</style>
"""


# Funcții pentru autentificare
def hash_password(password: str) -> str:
    """Hash password folosind SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> dict:
    """Încarcă utilizatorii din fișierul JSON"""
    users_file = Path(__file__).parent / "users.json"
    if users_file.exists():
        with open(users_file, 'r') as f:
            return json.load(f)
    else:
        # Creează utilizatori impliciti
        default_users = {
            "admin": {
                "password": hash_password("admin123"),
                "role": "admin",
                "name": "Administrator"
            },
            "user": {
                "password": hash_password("user123"),
                "role": "user",
                "name": "Utilizator"
            }
        }
        with open(users_file, 'w') as f:
            json.dump(default_users, f, indent=2)
        return default_users


def verify_login(username: str, password: str) -> tuple[bool, dict]:
    """Verifică credențialele utilizatorului"""
    users = load_users()
    if username in users:
        if users[username]["password"] == hash_password(password):
            return True, users[username]
    return False, {}


def init_session_state():
    """Inițializează session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"


def login_page():
    """Pagina de login"""
    st.markdown(FUTURISTIC_CSS, unsafe_allow_html=True)

    # Container centrat pentru login
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
            <div class="login-container">
                <div class="logo-container">
                    <div class="logo-symbol">◈</div>
                    <h1 style="margin: 0; font-size: 1.8rem;">ULTIMATE DASHBOARD</h1>
                    <p style="color: rgba(0, 240, 255, 0.6); margin-top: 0.5rem;">Sistem de Management</p>
                </div>
                <div class="cyber-divider"></div>
            </div>
        """, unsafe_allow_html=True)

        # Form de login
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("", placeholder="Utilizator", key="login_user")
            password = st.text_input("", placeholder="Parolă", type="password", key="login_pass")

            st.markdown("<br>", unsafe_allow_html=True)
            submit = st.form_submit_button("◈  CONECTARE  ◈", use_container_width=True)

            if submit:
                if username and password:
                    success, user_data = verify_login(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = {
                            "username": username,
                            **user_data
                        }
                        st.rerun()
                    else:
                        st.error("◈ Credențiale invalide")
                else:
                    st.warning("◈ Completează toate câmpurile")

        st.markdown("""
            <div style="text-align: center; margin-top: 2rem; color: rgba(0, 240, 255, 0.4);">
                <small>v1.0 • Ultimate Dashboard System</small>
            </div>
        """, unsafe_allow_html=True)


def sidebar_navigation():
    """Sidebar cu navigare"""
    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 1rem; text-align: center;">
                <div class="logo-symbol" style="font-size: 2rem;">◈</div>
                <h3 style="margin: 0.5rem 0;">DASHBOARD</h3>
                <div class="cyber-divider"></div>
                <p style="font-size: 0.9rem; color: rgba(0, 240, 255, 0.7);">
                    <span class="status-online"></span>
                    {st.session_state.user['name']}
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Navigare
        pages = ["Dashboard", "Analize", "Rapoarte", "Setări"]

        for page in pages:
            if st.button(f"◈ {page}", key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()

        st.markdown("<div class='cyber-divider'></div>", unsafe_allow_html=True)

        # Logout
        if st.button("◈ Deconectare", key="logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()


def metric_card(label: str, value: str, delta: str = None):
    """Componentă pentru card metric"""
    delta_html = f"<p style='color: #00ff88; margin: 0;'>{delta}</p>" if delta else ""
    st.markdown(f"""
        <div class="metric-card">
            <p class="metric-label">{label}</p>
            <p class="metric-value">{value}</p>
            {delta_html}
        </div>
    """, unsafe_allow_html=True)


def dashboard_page():
    """Pagina principală Dashboard"""
    st.markdown(f"""
        <h1>◈ DASHBOARD</h1>
        <p style="color: rgba(0, 240, 255, 0.7);">
            Bine ai venit, {st.session_state.user['name']} • {datetime.now().strftime('%d.%m.%Y %H:%M')}
        </p>
        <div class="cyber-divider"></div>
    """, unsafe_allow_html=True)

    # Metrici principale
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("Total Facturi", "1,234", "+12%")
    with col2:
        metric_card("Venituri", "€45,678", "+8.5%")
    with col3:
        metric_card("Comenzi Noi", "89", "+23%")
    with col4:
        metric_card("Clienți Activi", "156", "+5%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Secțiuni adiționale
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="metric-card">
                <h3>◈ Activitate Recentă</h3>
                <div class="cyber-divider"></div>
            </div>
        """, unsafe_allow_html=True)

        # Placeholder pentru activitate
        activities = [
            ("10:30", "Factură #1234 emisă"),
            ("09:45", "Comandă #567 procesată"),
            ("09:15", "Client nou înregistrat"),
            ("08:30", "Raport generat"),
        ]

        for time, activity in activities:
            st.markdown(f"""
                <div style="padding: 0.5rem 1rem; border-left: 2px solid rgba(0, 240, 255, 0.3); margin: 0.5rem 0;">
                    <span style="color: #00f0ff;">{time}</span> - {activity}
                </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="metric-card">
                <h3>◈ Statistici Rapide</h3>
                <div class="cyber-divider"></div>
            </div>
        """, unsafe_allow_html=True)

        # Placeholder pentru statistici
        stats = [
            ("Rata de conversie", "78%"),
            ("Timp mediu procesare", "2.3h"),
            ("Satisfacție clienți", "94%"),
            ("Uptime sistem", "99.9%"),
        ]

        for label, value in stats:
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; padding: 0.5rem 1rem; border-bottom: 1px solid rgba(0, 240, 255, 0.1);">
                    <span>{label}</span>
                    <span style="color: #00f0ff; font-weight: bold;">{value}</span>
                </div>
            """, unsafe_allow_html=True)


def analize_page():
    """Pagina de Analize"""
    st.markdown("""
        <h1>◈ ANALIZE</h1>
        <p style="color: rgba(0, 240, 255, 0.7);">Analize și rapoarte detaliate</p>
        <div class="cyber-divider"></div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="metric-card">
            <h3>◈ Modul în dezvoltare</h3>
            <p>Această secțiune va conține analize detaliate și grafice interactive.</p>
        </div>
    """, unsafe_allow_html=True)


def rapoarte_page():
    """Pagina de Rapoarte"""
    st.markdown("""
        <h1>◈ RAPOARTE</h1>
        <p style="color: rgba(0, 240, 255, 0.7);">Generare și export rapoarte</p>
        <div class="cyber-divider"></div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="metric-card">
            <h3>◈ Modul în dezvoltare</h3>
            <p>Această secțiune va conține generare rapoarte PDF/Excel.</p>
        </div>
    """, unsafe_allow_html=True)


def setari_page():
    """Pagina de Setări"""
    st.markdown("""
        <h1>◈ SETĂRI</h1>
        <p style="color: rgba(0, 240, 255, 0.7);">Configurare sistem</p>
        <div class="cyber-divider"></div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
            <div class="metric-card">
                <h3>◈ Profil Utilizator</h3>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="padding: 1rem;">
                <p><strong>Utilizator:</strong> {st.session_state.user['username']}</p>
                <p><strong>Nume:</strong> {st.session_state.user['name']}</p>
                <p><strong>Rol:</strong> {st.session_state.user['role'].upper()}</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
            <div class="metric-card">
                <h3>◈ Informații Sistem</h3>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="padding: 1rem;">
                <p><strong>Versiune:</strong> 1.0.0</p>
                <p><strong>Status:</strong> <span class="status-online"></span> Online</p>
                <p><strong>Ultima actualizare:</strong> {datetime.now().strftime('%d.%m.%Y')}</p>
            </div>
        """, unsafe_allow_html=True)


def main():
    """Funcția principală"""
    init_session_state()

    if not st.session_state.authenticated:
        login_page()
    else:
        st.markdown(FUTURISTIC_CSS, unsafe_allow_html=True)
        sidebar_navigation()

        # Routing pagini
        page = st.session_state.current_page

        if page == "Dashboard":
            dashboard_page()
        elif page == "Analize":
            analize_page()
        elif page == "Rapoarte":
            rapoarte_page()
        elif page == "Setări":
            setari_page()


if __name__ == "__main__":
    main()

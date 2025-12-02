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

# Custom CSS for dark theme
st.markdown("""
<style>
    /* Main container */
    .main {
        background-color: #0f172a;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
    }

    /* Headers */
    h1, h2, h3 {
        color: #e2e8f0 !important;
    }

    /* Logo container */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 0;
        margin-bottom: 1rem;
        border-bottom: 1px solid #334155;
    }

    .logo-container img {
        width: 50px;
        height: auto;
    }

    .logo-title {
        color: #e2e8f0;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    .logo-subtitle {
        color: #94a3b8;
        font-size: 0.875rem;
        margin: 0;
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #334155;
        margin-bottom: 1rem;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #6366f1;
    }

    .metric-label {
        color: #94a3b8;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Status badges */
    .badge-success {
        background-color: #059669;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .badge-warning {
        background-color: #d97706;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    .badge-error {
        background-color: #dc2626;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }

    /* Upload area */
    [data-testid="stFileUploader"] {
        background-color: #1e293b;
        border: 2px dashed #334155;
        border-radius: 12px;
        padding: 1rem;
    }

    [data-testid="stFileUploader"]:hover {
        border-color: #6366f1;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
    }

    /* Tables */
    .dataframe {
        background-color: #1e293b !important;
    }

    /* Info boxes */
    .stAlert {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
    }

    /* User info */
    .user-info {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        background-color: #334155;
        border-radius: 8px;
        margin-bottom: 1rem;
    }

    .user-avatar {
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 600;
    }

    /* Divider */
    hr {
        border-color: #334155;
    }

    /* Progress */
    .stProgress > div > div {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Check authentication
    if not st.session_state.get('authenticated', False):
        login_form()
        return

    # Sidebar
    with st.sidebar:
        # Logo and title
        st.markdown("""
        <div class="logo-container">
            <img src="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg" alt="OBSID">
            <div>
                <p class="logo-title">Ultimate Facturi</p>
                <p class="logo-subtitle">Dashboard OBSID</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # User info
        user_name = st.session_state.get('name', 'User')
        user_initial = user_name[0].upper() if user_name else 'U'
        st.markdown(f"""
        <div class="user-info">
            <div class="user-avatar">{user_initial}</div>
            <span style="color: #e2e8f0;">{user_name}</span>
        </div>
        """, unsafe_allow_html=True)

        # Logout button
        if st.button("Deconectare", use_container_width=True):
            logout()

        st.markdown("---")

        # Navigation
        st.markdown("### Navigare")
        page = st.radio(
            "Selecteaza pagina",
            ["Dashboard", "Procesare Facturi", "Incasari MT940", "Setari"],
            label_visibility="collapsed"
        )

    # Main content based on selected page
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
    st.markdown("# Dashboard")
    st.markdown("Bine ai venit in panoul de control Ultimate Facturi OBSID")

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">0</div>
            <div class="metric-label">Facturi Procesate</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">0</div>
            <div class="metric-label">Incasari MT940</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">0.00 RON</div>
            <div class="metric-label">Total Incasari</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-value">0</div>
            <div class="metric-label">Erori</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Quick actions
    st.markdown("### Actiuni Rapide")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Procesare Noua", use_container_width=True):
            st.session_state['page'] = 'Procesare Facturi'
            st.rerun()

    with col2:
        if st.button("Vizualizeaza Incasari", use_container_width=True):
            st.session_state['page'] = 'Incasari MT940'
            st.rerun()

    with col3:
        if st.button("Export Raport", use_container_width=True):
            st.info("Incarca mai intai fisierele pentru procesare")


def show_procesare():
    """Pagina de procesare facturi."""
    st.markdown("# Procesare Facturi")
    st.markdown("Incarca fisierele necesare pentru procesare")

    # Initialize session state for uploaded files
    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = {}

    # File uploads in columns
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Fisiere Obligatorii")

        # Gomag
        gomag_file = st.file_uploader(
            "Fisier Gomag (XLSX)",
            type=['xlsx'],
            key="gomag",
            help="Exportul comenzilor din Gomag"
        )

        # GLS
        gls_files = st.file_uploader(
            "Borderouri GLS (XLSX)",
            type=['xlsx'],
            accept_multiple_files=True,
            key="gls",
            help="Borderourile GLS cu colete"
        )

        # Sameday
        sameday_files = st.file_uploader(
            "Borderouri Sameday (XLSX)",
            type=['xlsx'],
            accept_multiple_files=True,
            key="sameday",
            help="Borderourile Sameday"
        )

    with col2:
        st.markdown("### Extras Bancar MT940")

        # MT940
        mt940_files = st.file_uploader(
            "Fisiere MT940 (TXT)",
            type=['txt'],
            accept_multiple_files=True,
            key="mt940",
            help="Extrasele bancare MT940 de la Banca Transilvania"
        )

        st.markdown("### Fisiere Optionale")

        # Netopia
        netopia_files = st.file_uploader(
            "Fisiere Netopia (CSV)",
            type=['csv'],
            accept_multiple_files=True,
            key="netopia",
            help="Exporturile tranzactii Netopia"
        )

        # Oblio
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
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            # Save uploaded files to temp directory
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

            # Netopia folder (optional)
            netopia_folder = os.path.join(tmpdir, "netopia")
            os.makedirs(netopia_folder, exist_ok=True)
            if netopia_files:
                for np_file in netopia_files:
                    with open(os.path.join(netopia_folder, np_file.name), 'wb') as f:
                        f.write(np_file.getbuffer())

            progress.progress(30)
            status.text("Procesez incasarile MT940...")

            # Parse MT940
            incasari_mt940 = extrage_referinte_op_din_mt940_folder(mt940_folder)
            st.session_state['incasari_mt940'] = incasari_mt940

            progress.progress(50)
            status.text("Procesez borderourile GLS...")

            # Process GLS
            rezultate_gls, erori_gls = proceseaza_borderouri_gls(gls_folder, gomag_df.copy())

            progress.progress(65)
            status.text("Procesez borderourile Sameday...")

            # Process Sameday
            rezultate_sameday, erori_sameday = proceseaza_borderouri_sameday(sameday_folder, gomag_df.copy())

            progress.progress(80)
            status.text("Procesez Netopia...")

            # Process Netopia
            rezultate_netopia, erori_netopia = proceseaza_netopia(netopia_folder, gomag_df.copy())

            progress.progress(90)
            status.text("Generez raportul Excel...")

            # Generate export
            excel_buffer = genereaza_export_excel(
                rezultate_gls,
                rezultate_sameday,
                rezultate_netopia,
                incasari_mt940
            )

            progress.progress(100)
            status.text("Procesare finalizata!")

            # Show results
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

            # Show errors if any
            all_errors = erori_gls + erori_sameday + erori_netopia
            if all_errors:
                with st.expander(f"Erori ({len(all_errors)})", expanded=False):
                    for err in all_errors:
                        st.warning(err)

            # Download button
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="Descarca Raportul Excel",
                data=excel_buffer,
                file_name=f"facturi_grupate_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

            # Store results in session
            st.session_state['rezultate_gls'] = rezultate_gls
            st.session_state['rezultate_sameday'] = rezultate_sameday
            st.session_state['rezultate_netopia'] = rezultate_netopia

    except Exception as e:
        st.error(f"Eroare la procesare: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


def show_incasari():
    """Pagina cu incasarile MT940."""
    st.markdown("# Incasari MT940")

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
    st.markdown("# Setari")

    st.markdown("### Informatii Aplicatie")
    st.info("""
    **Ultimate Facturi OBSID**
    Versiune: 1.0.0

    Aplicatie pentru procesarea si gruparea facturilor din:
    - Borderouri GLS
    - Borderouri Sameday
    - Tranzactii Netopia
    - Extrase bancare MT940 (Banca Transilvania)
    """)

    st.markdown("### Despre")
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

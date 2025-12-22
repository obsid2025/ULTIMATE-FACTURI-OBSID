# -*- coding: utf-8 -*-
"""
Pregătire Decanturi - Pagină Streamlit
Procesare comenzi și generare rapoarte de producție
Migrat din aplicația Flask pregatire_decanturi
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.decanturi_processor import (
    proceseaza_comenzi,
    proceseaza_bonuri_productie,
    genereaza_tabel_raport,
    genereaza_export_excel,
    get_bonuri_procesate_pentru_comenzi,
    adauga_bon,
    get_bonuri_azi,
    get_statistici_azi,
    get_product_database
)
from utils.auth import is_authenticated, login_form

# Page config
st.set_page_config(
    page_title="Pregătire Decanturi - OBSID",
    page_icon="https://gomagcdn.ro/domains3/obsid.ro/files/company/parfumuri-arabesti8220.svg",
    layout="wide"
)

# Authentication check
if not is_authenticated():
    login_form()
    st.stop()


def main():
    st.title("Pregătire Decanturi")
    st.markdown("Procesare comenzi și generare rapoarte de producție")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["Raport Producție", "Bonuri Producție", "Statistici"])

    # ============ TAB 1: RAPORT PRODUCTIE ============
    with tab1:
        st.header("Raport Producție Decanturi")

        uploaded_file = st.file_uploader(
            "Încarcă fișier Excel cu comenzi",
            type=['xlsx', 'xls'],
            key="upload_raport"
        )

        if uploaded_file is not None:
            with st.spinner("Procesare fișier..."):
                try:
                    file_content = uploaded_file.read()
                    raport, raport_intregi, finalizate, total = proceseaza_comenzi(file_content)

                    # Statistici
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Comenzi Finalizate", finalizate)
                    with col2:
                        st.metric("Total Comenzi", total)
                    with col3:
                        st.metric("Produse Unice", len(raport) + len(raport_intregi))

                    st.divider()

                    # Tabel Decanturi
                    if raport:
                        st.subheader("Decanturi")

                        # Sortare după cantitate
                        sorted_raport = sorted(raport.items(), key=lambda x: x[1]['bucati'], reverse=True)

                        df_data = []
                        for sku, info in sorted_raport:
                            df_data.append({
                                'SKU': sku,
                                'Produs': info['nume'],
                                'ML': info['cantitate_ml'],
                                'Bucăți': info['bucati']
                            })

                        df = pd.DataFrame(df_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        # Copiere SKU-uri
                        sku_list = [item['SKU'] for item in df_data if item['SKU'] != 'N/A']
                        if sku_list:
                            sku_text = '\n'.join(sku_list)
                            st.text_area("SKU-uri pentru copiere", sku_text, height=100)

                    # Tabel Produse Întregi
                    if raport_intregi:
                        st.subheader("Produse Întregi")

                        df_intregi_data = []
                        for key, info in sorted(raport_intregi.items(), key=lambda x: x[1]['bucati'], reverse=True):
                            df_intregi_data.append({
                                'SKU': info.get('sku', 'N/A'),
                                'Produs': info['nume'],
                                'Bucăți': info['bucati']
                            })

                        df_intregi = pd.DataFrame(df_intregi_data)
                        st.dataframe(df_intregi, use_container_width=True, hide_index=True)

                    # Export Excel
                    st.divider()
                    excel_data = genereaza_export_excel(raport, raport_intregi)
                    st.download_button(
                        label="Download Raport Excel",
                        data=excel_data,
                        file_name=f"raport_productie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"Eroare la procesare: {str(e)}")

    # ============ TAB 2: BONURI PRODUCTIE ============
    with tab2:
        st.header("Bonuri de Producție")
        st.markdown("Generează bonuri individuale pentru automatizare Oblio")

        uploaded_file_bonuri = st.file_uploader(
            "Încarcă fișier Excel cu comenzi",
            type=['xlsx', 'xls'],
            key="upload_bonuri"
        )

        if uploaded_file_bonuri is not None:
            with st.spinner("Procesare fișier..."):
                try:
                    file_content = uploaded_file_bonuri.read()
                    bonuri = proceseaza_bonuri_productie(file_content)

                    if bonuri:
                        # Obține bonuri deja procesate pentru Smart Resume
                        order_numbers = list(set(b['order_number'] for b in bonuri))
                        procesate = get_bonuri_procesate_pentru_comenzi(order_numbers)

                        # Marchează bonurile deja procesate
                        for bon in bonuri:
                            bon['procesat'] = (bon['sku'], bon['order_number']) in procesate

                        # Statistici
                        total_bonuri = len(bonuri)
                        bonuri_noi = sum(1 for b in bonuri if not b['procesat'])

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Bonuri", total_bonuri)
                        with col2:
                            st.metric("Bonuri Noi", bonuri_noi)
                        with col3:
                            st.metric("Deja Procesate", total_bonuri - bonuri_noi)

                        st.divider()

                        # Filtrare
                        show_only_new = st.checkbox("Arată doar bonuri noi (neproceate)", value=True)

                        if show_only_new:
                            bonuri_display = [b for b in bonuri if not b['procesat']]
                        else:
                            bonuri_display = bonuri

                        # Sortare după cantitate
                        bonuri_display = sorted(bonuri_display, key=lambda x: x['cantitate'], reverse=True)

                        # Tabel
                        if bonuri_display:
                            df_bonuri = pd.DataFrame([{
                                'SKU': b['sku'],
                                'Produs': b['nume'],
                                'Cantitate': b['cantitate'],
                                'ML': b['cantitate_ml'],
                                'Comanda': b['order_number'],
                                'Status': 'Nou' if not b.get('procesat') else 'Procesat'
                            } for b in bonuri_display])

                            st.dataframe(df_bonuri, use_container_width=True, hide_index=True)

                            # SKU-uri pentru copiere
                            sku_list = [b['sku'] for b in bonuri_display if b['sku'] != 'N/A']
                            unique_skus = list(dict.fromkeys(sku_list))  # Păstrează ordinea

                            st.subheader("SKU-uri pentru Oblio")
                            sku_text = '\n'.join(unique_skus)
                            st.text_area("Copiază SKU-urile de mai jos:", sku_text, height=150)

                            # Buton pentru marcarea ca procesate
                            if st.button("Marchează toate ca procesate", type="primary"):
                                with st.status("Salvare în baza de date...", expanded=True) as status:
                                    saved = 0
                                    for bon in bonuri_display:
                                        if not bon.get('procesat'):
                                            st.write(f"Salvare: {bon['sku']} (comanda #{bon['order_number']})")
                                            if adauga_bon(
                                                bon['sku'],
                                                bon['nume'],
                                                bon['cantitate'],
                                                bon['order_id'],
                                                bon['order_number']
                                            ):
                                                saved += 1
                                    status.update(label=f"Salvate {saved} bonuri!", state="complete")
                                st.rerun()
                        else:
                            st.info("Nu există bonuri noi de procesat.")

                    else:
                        st.warning("Nu s-au găsit bonuri de producție în fișier.")

                except Exception as e:
                    st.error(f"Eroare la procesare: {str(e)}")

    # ============ TAB 3: STATISTICI ============
    with tab3:
        st.header("Statistici")

        # Statistici azi
        stats = get_statistici_azi()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Bonuri Azi", stats['total_bonuri'])
        with col2:
            st.metric("Comenzi Azi", stats['total_comenzi'])
        with col3:
            st.metric("Cantitate Totală", f"{stats['total_cantitate']:.0f}")

        st.divider()

        # Bonuri procesate azi
        bonuri_azi = get_bonuri_azi()
        if bonuri_azi:
            st.subheader("Bonuri procesate astăzi")

            df_azi = pd.DataFrame([{
                'SKU': b['sku'],
                'Produs': b['nume_produs'],
                'Cantitate': b['cantitate'],
                'Comanda': b['order_number']
            } for b in bonuri_azi])

            st.dataframe(df_azi, use_container_width=True, hide_index=True)
        else:
            st.info("Nu există bonuri procesate astăzi.")

        # Baza de date produse
        st.divider()
        st.subheader("Baza de Date Produse")

        if st.button("Reîncarcă Baza de Date"):
            with st.spinner("Încărcare din Google Sheets..."):
                product_db, reverse_db = get_product_database()
                st.success(f"Încărcate {len(product_db)} produse!")

        product_db, _ = get_product_database()
        st.metric("Produse în Baza de Date", len(product_db))


if __name__ == "__main__":
    main()

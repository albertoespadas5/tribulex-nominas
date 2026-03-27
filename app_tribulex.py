"""
Tribulex - Interfaz web para gestión de nóminas.
100% compatible con Streamlit Cloud (sin dependencias locales).
Ejecutar con:  streamlit run app_tribulex.py
"""

import io
import pandas as pd
import streamlit as st
from procesador_inteligente_tribulex import procesar_pdf_en_memoria
from clientes_db import (
    listar_clientes, obtener_cliente, buscar_por_empresa,
    crear_cliente, actualizar_cliente, eliminar_cliente,
)
from envio_smtp import enviar_zip_por_email, generar_cuerpo_estandar, generar_cuerpo_ia

# ── Configuración de página ────────────────────────────────────────────
st.set_page_config(
    page_title="Tribulex - Gestión de Nóminas",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS corporativo completo ───────────────────────────────────────────
st.markdown("""
<style>
    /* ── Variables globales — MODO OSCURO ────────────────── */
    :root {
        --azul-oscuro:   #0a1929;
        --azul-corp:     #132f4c;
        --azul-medio:    #1a3f6f;
        --azul-claro:    #4a90d9;
        --azul-pastel:   #1a2d42;
        --gris-fondo:    #0d1117;
        --gris-borde:    #1e2a3a;
        --gris-texto:    #8b99a8;
        --blanco:        #131c27;
        --texto-claro:   #e2e8f0;
        --texto-bright:  #f0f6fc;
        --verde-ok:      #3fb950;
        --rojo-err:      #f85149;
        --naranja-warn:  #d29922;
        --superficie:    #161b22;
        --superficie-2:  #1c2433;
    }

    /* ── Fondo general ──────────────────────────────────── */
    .stApp { background-color: var(--gris-fondo) !important; }

    /* ── Texto global oscuro ────────────────────────────── */
    .stApp, .stApp p, .stApp span, .stApp label, .stApp li,
    .stApp .stMarkdown, .stApp div {
        color: var(--texto-claro) !important;
    }
    h1, h2, h3, h4, h5, h6,
    .stApp h1, .stApp h2, .stApp h3 {
        color: var(--texto-bright) !important;
    }

    /* ── Tabs oscuros ───────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--superficie) !important;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--gris-texto) !important;
        background: transparent !important;
        border-radius: 8px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: var(--texto-bright) !important;
        background: var(--azul-corp) !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        background: transparent !important;
    }

    /* ── Inputs / selects oscuros ────────────────────────── */
    .stTextInput input, .stTextArea textarea, .stSelectbox > div > div {
        background: var(--superficie) !important;
        color: var(--texto-claro) !important;
        border: 1px solid var(--gris-borde) !important;
    }

    /* ── Tablas / dataframes oscuros ─────────────────────── */
    .stDataFrame, [data-testid="stDataFrame"] {
        background: var(--superficie) !important;
        border-radius: 8px;
    }

    /* ── Logo + cabecera hero ───────────────────────────── */
    .hero-header {
        background: linear-gradient(135deg, #0d2137 0%, var(--azul-medio) 60%, var(--azul-claro) 100%);
        padding: 2rem 2.5rem 1.8rem;
        border-radius: 14px;
        margin-bottom: 1.8rem;
        color: white;
        display: flex;
        align-items: center;
        gap: 1.5rem;
        box-shadow: 0 4px 24px rgba(0,0,0,0.5);
        border: 1px solid rgba(74,144,217,0.2);
    }
    .hero-logo {
        width: 72px; height: 72px;
        background: rgba(255,255,255,0.15);
        border-radius: 16px;
        display: flex; align-items: center; justify-content: center;
        font-size: 2.2rem;
        flex-shrink: 0;
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255,255,255,0.2);
    }
    .hero-text h1 {
        margin: 0; font-size: 1.9rem; font-weight: 700;
        letter-spacing: -0.5px;
    }
    .hero-text p {
        margin: 0.25rem 0 0; opacity: 0.8; font-size: 0.95rem;
        font-weight: 300; letter-spacing: 0.3px;
    }
    .hero-badge {
        margin-left: auto;
        background: rgba(255,255,255,0.18);
        padding: 0.4rem 1rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        white-space: nowrap;
    }

    /* ── Tarjetas métricas premium ──────────────────────── */
    .kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
    .kpi-card {
        flex: 1;
        background: var(--superficie);
        border-radius: 12px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        border: 1px solid var(--gris-borde);
        border-top: 4px solid var(--azul-claro);
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 24px rgba(0,0,0,0.4);
        border-color: var(--azul-claro);
    }
    .kpi-card.green  { border-top-color: var(--verde-ok); }
    .kpi-card.orange { border-top-color: var(--naranja-warn); }
    .kpi-icon {
        font-size: 1.5rem; margin-bottom: 0.3rem;
    }
    .kpi-number {
        font-size: 2.2rem; font-weight: 800; color: var(--texto-bright);
        line-height: 1.1;
    }
    .kpi-label {
        font-size: 0.8rem; color: var(--gris-texto);
        text-transform: uppercase; letter-spacing: 0.8px;
        font-weight: 600; margin-top: 0.2rem;
    }

    /* ── Secciones / paneles ────────────────────────────── */
    .section-panel {
        background: var(--superficie);
        border-radius: 12px;
        padding: 1.5rem 1.8rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        margin-bottom: 1.5rem;
        border: 1px solid var(--gris-borde);
    }
    .section-title {
        font-size: 1.15rem; font-weight: 700; color: var(--texto-bright) !important;
        margin: 0 0 1rem; padding-bottom: 0.6rem;
        border-bottom: 2px solid var(--azul-corp);
        display: flex; align-items: center; gap: 0.5rem;
    }

    /* ── Tarjetas ZIP ───────────────────────────────────── */
    .zip-card {
        background: linear-gradient(135deg, var(--superficie-2), var(--azul-pastel));
        border: 1px solid var(--gris-borde);
        border-radius: 10px;
        padding: 1.2rem;
        text-align: center;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .zip-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0,0,0,0.4);
    }
    .zip-icon { font-size: 2rem; margin-bottom: 0.4rem; }
    .zip-name { font-weight: 700; color: var(--azul-claro) !important; font-size: 0.85rem; word-break: break-all; }
    .zip-meta { font-size: 0.75rem; color: var(--gris-texto); margin-top: 0.3rem; }

    /* ── Botones primarios ──────────────────────────────── */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--azul-medio), var(--azul-claro)) !important;
        color: white !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        padding: 0.8rem 2rem !important;
        border-radius: 10px !important;
        border: 1px solid rgba(74,144,217,0.3) !important;
        width: 100% !important;
        box-shadow: 0 4px 18px rgba(74,144,217,0.3) !important;
        letter-spacing: 0.3px !important;
        transition: all 0.2s !important;
    }
    div.stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 28px rgba(74,144,217,0.45) !important;
        transform: translateY(-1px) !important;
    }
    /* Botones secundarios (descargas) */
    div.stDownloadButton > button {
        background: var(--superficie-2) !important;
        color: var(--texto-claro) !important;
        border: 1px solid var(--gris-borde) !important;
        border-radius: 8px !important;
    }
    div.stDownloadButton > button:hover {
        background: var(--azul-corp) !important;
        border-color: var(--azul-claro) !important;
    }

    /* ── Sidebar ────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #060d16 0%, #0a1929 100%) !important;
        border-right: 1px solid var(--gris-borde);
    }
    section[data-testid="stSidebar"] * {
        color: var(--texto-claro) !important;
    }
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stTextArea textarea {
        background: rgba(255,255,255,0.06) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: var(--texto-claro) !important;
    }

    /* ── Tablas / dataframes ─────────────────────────────── */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* ── Alertas oscuras ─────────────────────────────────── */
    .stAlert > div {
        background: var(--superficie) !important;
        color: var(--texto-claro) !important;
        border: 1px solid var(--gris-borde) !important;
    }

    /* ── Metrics de Streamlit ─────────────────────────────── */
    [data-testid="stMetric"] {
        background: var(--superficie) !important;
        border: 1px solid var(--gris-borde) !important;
        border-radius: 10px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stMetricValue"] {
        color: var(--texto-bright) !important;
    }
    [data-testid="stMetricLabel"] {
        color: var(--gris-texto) !important;
    }

    /* ── Spinners / progress ──────────────────────────────── */
    .stSpinner > div { color: var(--azul-claro) !important; }

    /* ── File uploader oscuro ──────────────────────────────── */
    [data-testid="stFileUploader"] {
        background: var(--superficie) !important;
        border: 2px dashed var(--gris-borde) !important;
        border-radius: 12px;
        padding: 1rem;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: var(--azul-claro) !important;
    }

    /* ── Footer ─────────────────────────────────────────── */
    .app-footer {
        text-align: center; padding: 1.5rem 0 0.5rem;
        color: var(--gris-texto); font-size: 0.75rem;
        border-top: 1px solid var(--gris-borde);
        margin-top: 2rem;
    }

    /* ── Cliente encontrado (info box) ────────────────── */
    .cliente-encontrado {
        background: linear-gradient(135deg, #0d2a1a 0%, #1a3f2f 100%);
        border: 1px solid var(--verde-ok);
        border-left: 4px solid var(--verde-ok);
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin: 0.5rem 0;
    }
    .cliente-encontrado .ce-titulo {
        color: var(--verde-ok) !important;
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.4rem;
    }
    .cliente-encontrado .ce-detalle {
        color: var(--texto-claro) !important;
        font-size: 0.85rem;
        line-height: 1.5;
    }
    .cliente-no-encontrado {
        background: linear-gradient(135deg, #2a1a0d 0%, #3f2f1a 100%);
        border: 1px solid var(--naranja-warn);
        border-left: 4px solid var(--naranja-warn);
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        margin: 0.5rem 0;
    }
    .cliente-no-encontrado span {
        color: var(--naranja-warn) !important;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Cabecera hero con logo ─────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <div class="hero-logo">TX</div>
    <div class="hero-text">
        <h1>Tribulex</h1>
        <p>Plataforma de Gesti&oacute;n y Distribuci&oacute;n de N&oacute;minas</p>
    </div>
    <div class="hero-badge">v3.0 &middot; Cloud</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────
st.sidebar.markdown("### 📄 Subir PDF de N\u00f3minas")
st.sidebar.info("Selecciona el PDF de n\u00f3minas desde tu ordenador para empezar.")

pdf_subido = st.sidebar.file_uploader(
    "PDF de n\u00f3minas",
    type=["pdf"],
    key="pdf_upload",
    help="Selecciona el archivo PDF que contiene todas las n\u00f3minas",
)

mes_elegido = st.sidebar.text_input("Mes", value="Marzo", key="mes_zip")

st.sidebar.markdown("---")
if st.sidebar.button("Limpiar resultados"):
    for k in ["proc_registros", "proc_zips", "proc_csv_resumen", "proc_csv_detalle"]:
        st.session_state.pop(k, None)
    st.rerun()

# ══════════════════════════════════════════════════════════════════════
#  CONTENIDO PRINCIPAL — Tabs de nivel superior
# ══════════════════════════════════════════════════════════════════════

main_tab_nominas, main_tab_clientes = st.tabs([
    "Gesti\u00f3n de N\u00f3minas",
    "Gesti\u00f3n de Clientes",
])

# ──────────────────────────────────────────────────────────────────────
#  TAB 1: GESTION DE NOMINAS
# ──────────────────────────────────────────────────────────────────────
with main_tab_nominas:

    if pdf_subido is None:
        # ── Estado inicial: instrucciones ──────────────────────────
        st.markdown('<div class="section-panel">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">C\u00f3mo usar Tribulex</div>', unsafe_allow_html=True)
        st.markdown("""
        1. **Sube tu PDF** de n\u00f3minas usando el panel de la izquierda.
        2. **Indica el mes** correspondiente.
        3. Pulsa **Procesar** y espera unos segundos.
        4. **Descarga los ZIPs** organizados por empresa y los informes CSV.

        > Todo se procesa en memoria. No se guarda ning\u00fan archivo en el servidor.
        """)
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # ── PDF cargado: mostrar info y bot\u00f3n de procesar ─────────
        size_mb = len(pdf_subido.getvalue()) / (1024 * 1024)
        st.markdown(f"""
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="kpi-icon">📄</div>
                <div class="kpi-number">1</div>
                <div class="kpi-label">PDF Cargado</div>
            </div>
            <div class="kpi-card green">
                <div class="kpi-icon">📁</div>
                <div class="kpi-number">{pdf_subido.name}</div>
                <div class="kpi-label">Archivo</div>
            </div>
            <div class="kpi-card orange">
                <div class="kpi-icon">💾</div>
                <div class="kpi-number">{size_mb:.1f} MB</div>
                <div class="kpi-label">Tama\u00f1o</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Bot\u00f3n principal
        if st.button("PROCESAR PDF Y GENERAR ZIPS", type="primary", key="btn_procesar"):
            barra = st.progress(0, text="Iniciando procesamiento...")
            barra.progress(10, text="Leyendo PDF y extrayendo datos...")

            registros, zips_dict, csv_resumen, csv_detalle = procesar_pdf_en_memoria(
                pdf_subido.getvalue(), mes=mes_elegido,
            )

            barra.progress(100, text="Completado")
            barra.empty()

            # Guardar en sesi\u00f3n
            st.session_state.proc_registros = registros
            st.session_state.proc_zips = zips_dict
            st.session_state.proc_csv_resumen = csv_resumen
            st.session_state.proc_csv_detalle = csv_detalle
            st.rerun()

        # ── Mostrar resultados si ya se proces\u00f3 ──────────────────
        if "proc_registros" in st.session_state:
            registros = st.session_state.proc_registros
            zips_dict = st.session_state.proc_zips
            csv_resumen = st.session_state.proc_csv_resumen
            csv_detalle = st.session_state.proc_csv_detalle

            total_nominas = len(registros)
            empresas_set = {r["empresa"] for r in registros}
            num_empresas = len(empresas_set)
            coste_bruto = sum(r["bruto"] for r in registros)
            coste_liquido = sum(r["liquido"] for r in registros)

            st.success(f"Procesamiento completado \u2014 {total_nominas} n\u00f3minas de {num_empresas} empresas")

            # ── Busqueda de clientes en BD ────────────────────────
            st.markdown('<div class="section-panel">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">🔍 Clientes Detectados en Base de Datos</div>', unsafe_allow_html=True)
            for empresa_nombre in sorted(empresas_set):
                cliente = buscar_por_empresa(empresa_nombre)
                if cliente:
                    notas_html = cliente["notas"].replace("\n", "<br>") if cliente["notas"] else "Sin notas"
                    st.markdown(f"""
                    <div class="cliente-encontrado">
                        <div class="ce-titulo">Cliente encontrado: {empresa_nombre}</div>
                        <div class="ce-detalle">
                            <strong>Email:</strong> {cliente["email_contacto"] or "No registrado"} &nbsp;|&nbsp;
                            <strong>Tel:</strong> {cliente["telefono"] or "No registrado"} &nbsp;|&nbsp;
                            <strong>Env\u00edo:</strong> {cliente["preferencia_envio"]}<br>
                            <strong>Notas:</strong> {notas_html}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="cliente-no-encontrado">
                        <span>⚠ {empresa_nombre} — No encontrado en la base de datos de clientes</span>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # ── 4 KPI cards premium ───────────────────────────────
            st.markdown(f"""
            <div class="kpi-row">
                <div class="kpi-card">
                    <div class="kpi-icon">📄</div>
                    <div class="kpi-number">{total_nominas}</div>
                    <div class="kpi-label">Total N\u00f3minas Procesadas</div>
                </div>
                <div class="kpi-card green">
                    <div class="kpi-icon">🏢</div>
                    <div class="kpi-number">{num_empresas}</div>
                    <div class="kpi-label">Empresas Detectadas</div>
                </div>
                <div class="kpi-card orange">
                    <div class="kpi-icon">💰</div>
                    <div class="kpi-number">{coste_bruto:,.2f} \u20ac</div>
                    <div class="kpi-label">Sueldo Bruto Total</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-icon">💵</div>
                    <div class="kpi-number">{coste_liquido:,.2f} \u20ac</div>
                    <div class="kpi-label">Total L\u00edquido a Percibir</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Tabs de resultados ────────────────────────────────
            tab_detalle, tab_resumen, tab_zips, tab_enviar = st.tabs([
                "Detalle de N\u00f3minas",
                "Resumen por Empresa",
                "Descargar ZIPs",
                "Enviar por Email",
            ])

            # ── Tab 1: Detalle ────────────────────────────────────
            with tab_detalle:
                st.markdown('<div class="section-panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">📋 Detalle de N\u00f3minas Identificadas</div>', unsafe_allow_html=True)
                df_det = pd.DataFrame([
                    {
                        "Empresa": r["empresa"],
                        "Trabajador": r["nombre"],
                        "C\u00f3digo": r["codigo"],
                        "Email": r["email"] or "\u2014",
                        "Bruto (\u20ac)": f"{r['bruto']:,.2f}",
                        "L\u00edquido (\u20ac)": f"{r['liquido']:,.2f}",
                    }
                    for r in registros
                ])
                st.dataframe(df_det, width="stretch", hide_index=True, height=400)

                st.download_button(
                    "Descargar Detalle por Trabajador (CSV)",
                    data=csv_detalle,
                    file_name=f"Detalle_Trabajadores_{mes_elegido}.csv",
                    mime="text/csv",
                    key="dl_detalle_csv",
                )
                st.markdown("</div>", unsafe_allow_html=True)

            # ── Tab 2: Resumen por empresa ────────────────────────
            with tab_resumen:
                st.markdown('<div class="section-panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">📊 Resumen por Empresa</div>', unsafe_allow_html=True)
                df_csv = pd.read_csv(io.BytesIO(csv_resumen), sep=";", encoding="utf-8")
                st.dataframe(df_csv, width="stretch", hide_index=True)

                st.download_button(
                    "Descargar Resumen por Empresa (CSV)",
                    data=csv_resumen,
                    file_name=f"Resumen_Empresas_{mes_elegido}.csv",
                    mime="text/csv",
                    key="dl_resumen_csv",
                )
                st.markdown("</div>", unsafe_allow_html=True)

            # ── Tab 3: ZIPs por empresa ───────────────────────────
            with tab_zips:
                st.markdown('<div class="section-panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">📦 Archivos ZIP Generados por Empresa</div>', unsafe_allow_html=True)

                zip_items = list(zips_dict.items())
                cols_zip = st.columns(max(len(zip_items), 1))
                for i, (nombre_zip, zip_bytes) in enumerate(zip_items):
                    with cols_zip[i]:
                        size_kb = len(zip_bytes) / 1024
                        size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                        nominas_en_zip = sum(
                            1 for r in registros
                            if nombre_zip.startswith(f"Nominas_{r['empresa'].replace(' ', '_')}")
                            or any(
                                nombre_zip.startswith(f"Nominas_{nc}")
                                for nc in [
                                    "TalleresPaco", "ConsultoriaBeta", "RestauranteElPuerto",
                                    r["empresa"].replace(" ", "_"),
                                ]
                                if r["empresa"] in nombre_zip.replace("Nominas_", "").split("_")[0:2]
                            )
                        )

                        st.markdown(f"""
                        <div class="zip-card">
                            <div class="zip-icon">📦</div>
                            <div class="zip-name">{nombre_zip}</div>
                            <div class="zip-meta">{size_str}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("")
                        st.download_button(
                            "Descargar",
                            data=zip_bytes,
                            file_name=nombre_zip,
                            mime="application/zip",
                            key=f"dl_zip_{i}",
                        )

                st.markdown("</div>", unsafe_allow_html=True)

            # ── Tab 4: Enviar por Email ───────────────────────────
            with tab_enviar:
                st.markdown('<div class="section-panel">', unsafe_allow_html=True)
                st.markdown('<div class="section-title">📧 Enviar N\u00f3minas por Email</div>', unsafe_allow_html=True)

                # Verificar credenciales SMTP
                smtp_ok = False
                gemini_ok = False
                try:
                    smtp_user = st.secrets["email_usuario"]
                    smtp_pass = st.secrets["password_app"]
                    smtp_ok = True
                except Exception:
                    st.warning(
                        "Credenciales SMTP no configuradas. A\u00f1ade `email_usuario` y "
                        "`password_app` en **Settings > Secrets** de Streamlit Cloud, "
                        "o en `.streamlit/secrets.toml` para uso local."
                    )

                try:
                    gemini_key = st.secrets["GEMINI_API_KEY"]
                    gemini_ok = True
                except Exception:
                    gemini_key = None

                if smtp_ok:
                    col_status1, col_status2 = st.columns(2)
                    with col_status1:
                        st.info(f"Remitente: **{smtp_user}** (Gmail SMTP)")
                    with col_status2:
                        if gemini_ok:
                            st.info("Redacci\u00f3n IA: **Gemini activo**")
                        else:
                            st.warning("Gemini no configurado \u2014 se usar\u00e1 texto est\u00e1ndar")

                    st.markdown("---")

                    # Helper para encontrar ZIP de una empresa
                    def _buscar_zip(emp_nombre):
                        for zn, zb in zips_dict.items():
                            emp_zip = emp_nombre.replace(" ", "_")
                            if emp_zip in zn or any(
                                nc in zn for nc in [emp_zip]
                                + [v for k, v in {
                                    "Talleres Paco SL": "TalleresPaco",
                                    "Consultor\u00eda Beta": "ConsultoriaBeta",
                                    "Restaurante El Puerto": "RestauranteElPuerto",
                                }.items() if k == emp_nombre]
                            ):
                                return zn, zb
                        return None, None

                    # ── Por cada empresa: generar borrador y mostrar editor ──
                    for empresa_nombre in sorted(empresas_set):
                        cliente = buscar_por_empresa(empresa_nombre)
                        zip_nombre_match, zip_bytes_match = _buscar_zip(empresa_nombre)

                        puede_enviar = (
                            cliente
                            and cliente["email_contacto"]
                            and zip_bytes_match
                            and cliente["preferencia_envio"] != "No enviar"
                        )

                        safe_key = empresa_nombre.replace(" ", "_").replace(".", "")

                        # Cabecera de la empresa
                        if cliente and cliente["email_contacto"]:
                            st.markdown(
                                f"**{empresa_nombre}** → `{cliente['email_contacto']}` "
                                f"| {cliente['preferencia_envio']}"
                            )
                        elif cliente:
                            st.markdown(f"**{empresa_nombre}** → Sin email registrado")
                        else:
                            st.markdown(f"**{empresa_nombre}** → No registrado en BD de clientes")

                        if not puede_enviar:
                            st.button("Sin email", key=f"btn_ne_{safe_key}", disabled=True)
                            st.markdown("---")
                            continue

                        # ── Generar borrador (IA o estandar) ─────────────
                        session_key = f"borrador_{safe_key}"
                        session_src = f"borrador_src_{safe_key}"

                        if session_key not in st.session_state:
                            notas = cliente.get("notas", "").strip()
                            if notas and gemini_ok:
                                ok_ia, texto_ia = generar_cuerpo_ia(
                                    empresa_nombre, zip_nombre_match,
                                    mes_elegido, notas, gemini_key,
                                )
                                if ok_ia:
                                    st.session_state[session_key] = texto_ia
                                    st.session_state[session_src] = "gemini"
                                else:
                                    st.session_state[session_key] = generar_cuerpo_estandar(
                                        empresa_nombre, zip_nombre_match, mes_elegido,
                                    )
                                    st.session_state[session_src] = "estandar"
                                    st.warning(f"Gemini no disponible: {texto_ia}. Usando texto est\u00e1ndar.")
                            else:
                                st.session_state[session_key] = generar_cuerpo_estandar(
                                    empresa_nombre, zip_nombre_match, mes_elegido,
                                )
                                st.session_state[session_src] = "estandar"

                        origen = st.session_state.get(session_src, "estandar")
                        if origen == "gemini":
                            st.caption("Borrador generado por Gemini IA \u2014 rev\u00edsalo antes de enviar:")
                        else:
                            st.caption("Texto est\u00e1ndar \u2014 puedes editarlo antes de enviar:")

                        cuerpo_editado = st.text_area(
                            f"Cuerpo del email para {empresa_nombre}",
                            value=st.session_state[session_key],
                            height=180,
                            key=f"ta_{safe_key}",
                            label_visibility="collapsed",
                        )

                        col_enviar, col_regen = st.columns([3, 1])

                        with col_enviar:
                            if st.button(f"Confirmar y Enviar", key=f"btn_env_{safe_key}", type="primary"):
                                with st.spinner(f"Enviando a {cliente['email_contacto']}..."):
                                    ok, msg = enviar_zip_por_email(
                                        usuario_smtp=smtp_user,
                                        password_smtp=smtp_pass,
                                        destinatario=cliente["email_contacto"],
                                        nombre_empresa=empresa_nombre,
                                        nombre_zip=zip_nombre_match,
                                        zip_bytes=zip_bytes_match,
                                        mes=mes_elegido,
                                        cuerpo_email=cuerpo_editado,
                                    )
                                if ok:
                                    st.success(f"Enviado: {msg}")
                                else:
                                    st.error(f"Fallo: {msg}")

                        with col_regen:
                            if gemini_ok and cliente.get("notas", "").strip():
                                if st.button("Regenerar IA", key=f"btn_reg_{safe_key}"):
                                    ok_ia, texto_ia = generar_cuerpo_ia(
                                        empresa_nombre, zip_nombre_match,
                                        mes_elegido, cliente["notas"], gemini_key,
                                    )
                                    if ok_ia:
                                        st.session_state[session_key] = texto_ia
                                        st.session_state[session_src] = "gemini"
                                        st.rerun()
                                    else:
                                        st.error(texto_ia)

                        st.markdown("---")

                    # ── Boton enviar todo ─────────────────────────────
                    empresas_enviables = []
                    for emp in sorted(empresas_set):
                        cli = buscar_por_empresa(emp)
                        if cli and cli["email_contacto"] and cli["preferencia_envio"] != "No enviar":
                            zn, zb = _buscar_zip(emp)
                            if zb:
                                sk = emp.replace(" ", "_").replace(".", "")
                                empresas_enviables.append((emp, cli, zn, zb, sk))

                    if len(empresas_enviables) > 1:
                        if st.button(
                            f"ENVIAR TODO ({len(empresas_enviables)} empresas)",
                            key="btn_enviar_todo",
                            type="primary",
                        ):
                            barra_envio = st.progress(0, text="Enviando...")
                            resultados = []
                            for idx, (emp, cli, zn, zb, sk) in enumerate(empresas_enviables):
                                barra_envio.progress(
                                    int((idx / len(empresas_enviables)) * 100),
                                    text=f"Enviando a {cli['email_contacto']}...",
                                )
                                # Usar el texto editado del text_area
                                cuerpo_final = st.session_state.get(
                                    f"ta_{sk}",
                                    st.session_state.get(
                                        f"borrador_{sk}",
                                        generar_cuerpo_estandar(emp, zn, mes_elegido),
                                    ),
                                )
                                ok, msg = enviar_zip_por_email(
                                    usuario_smtp=smtp_user,
                                    password_smtp=smtp_pass,
                                    destinatario=cli["email_contacto"],
                                    nombre_empresa=emp,
                                    nombre_zip=zn,
                                    zip_bytes=zb,
                                    mes=mes_elegido,
                                    cuerpo_email=cuerpo_final,
                                )
                                resultados.append((emp, cli["email_contacto"], ok, msg))

                            barra_envio.progress(100, text="Completado")
                            barra_envio.empty()

                            for emp, email, ok, msg in resultados:
                                if ok:
                                    st.success(f"{emp} → {email}: Enviado")
                                else:
                                    st.error(f"{emp} → {email}: {msg}")

                st.markdown("</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
#  TAB 2: GESTION DE CLIENTES
# ──────────────────────────────────────────────────────────────────────
with main_tab_clientes:

    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">➕ A\u00f1adir Nuevo Cliente</div>', unsafe_allow_html=True)

    with st.form("form_nuevo_cliente", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            nc_empresa = st.text_input("Nombre de la Empresa *", placeholder="Ej: Talleres Paco SL")
            nc_email = st.text_input("Email de Contacto", placeholder="Ej: admin@tallerespaco.es")
        with col_b:
            nc_telefono = st.text_input("Tel\u00e9fono", placeholder="Ej: 612 345 678")
            nc_preferencia = st.selectbox(
                "Preferencia de Env\u00edo",
                ["Enviar a jefe", "Enviar a empleados", "Enviar a ambos", "No enviar"],
            )
        nc_notas = st.text_area(
            "Notas Personalizadas",
            placeholder="Ej: A\u00f1adir texto espec\u00edfico en el cuerpo del correo...",
            height=80,
        )
        btn_crear = st.form_submit_button("Guardar Cliente", type="primary")

    if btn_crear:
        if not nc_empresa.strip():
            st.error("El nombre de la empresa es obligatorio.")
        else:
            try:
                crear_cliente(nc_empresa, nc_email, nc_telefono, nc_preferencia, nc_notas)
                st.success(f"Cliente '{nc_empresa}' guardado correctamente.")
                st.rerun()
            except Exception as e:
                if "UNIQUE" in str(e):
                    st.error(f"Ya existe un cliente con el nombre '{nc_empresa}'.")
                else:
                    st.error(f"Error al guardar: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Lista de clientes existentes ──────────────────────────────
    st.markdown('<div class="section-panel">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 Listado de Clientes</div>', unsafe_allow_html=True)

    clientes = listar_clientes()

    if not clientes:
        st.info("No hay clientes registrados. A\u00f1ade el primero usando el formulario de arriba.")
    else:
        df_clientes = pd.DataFrame([
            {
                "Empresa": c["nombre_empresa"],
                "Email": c["email_contacto"] or "\u2014",
                "Tel\u00e9fono": c["telefono"] or "\u2014",
                "Preferencia": c["preferencia_envio"],
                "Notas": (c["notas"][:60] + "...") if len(c["notas"]) > 60 else (c["notas"] or "\u2014"),
            }
            for c in clientes
        ])
        st.dataframe(df_clientes, width="stretch", hide_index=True)

        # ── Editar / Eliminar cliente ─────────────────────────────
        st.markdown("---")
        st.markdown("**Editar o eliminar un cliente:**")

        opciones_clientes = {c["nombre_empresa"]: c["id"] for c in clientes}
        cliente_seleccionado = st.selectbox(
            "Seleccionar cliente",
            options=list(opciones_clientes.keys()),
            key="sel_editar_cliente",
        )

        if cliente_seleccionado:
            cliente_id = opciones_clientes[cliente_seleccionado]
            datos_cli = obtener_cliente(cliente_id)

            if datos_cli:
                with st.form("form_editar_cliente"):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        ed_empresa = st.text_input("Nombre Empresa", value=datos_cli["nombre_empresa"])
                        ed_email = st.text_input("Email", value=datos_cli["email_contacto"])
                    with col_e2:
                        ed_telefono = st.text_input("Tel\u00e9fono", value=datos_cli["telefono"])
                        pref_opciones = ["Enviar a jefe", "Enviar a empleados", "Enviar a ambos", "No enviar"]
                        pref_idx = pref_opciones.index(datos_cli["preferencia_envio"]) if datos_cli["preferencia_envio"] in pref_opciones else 0
                        ed_preferencia = st.selectbox("Preferencia", pref_opciones, index=pref_idx)
                    ed_notas = st.text_area("Notas", value=datos_cli["notas"], height=80)

                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        btn_actualizar = st.form_submit_button("Actualizar Cliente", type="primary")
                    with col_btn2:
                        btn_eliminar = st.form_submit_button("Eliminar")

                if btn_actualizar:
                    actualizar_cliente(cliente_id, ed_empresa, ed_email, ed_telefono, ed_preferencia, ed_notas)
                    st.success(f"Cliente '{ed_empresa}' actualizado.")
                    st.rerun()

                if btn_eliminar:
                    eliminar_cliente(cliente_id)
                    st.success(f"Cliente '{datos_cli['nombre_empresa']}' eliminado.")
                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── Footer corporativo ────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
    <strong>Tribulex</strong> &middot; Plataforma de Gesti&oacute;n de N&oacute;minas v3.0 Cloud<br>
    Todo se procesa en memoria &middot; No se almacena nada en el servidor<br>
    Desarrollo interno &middot; 2026
</div>
""", unsafe_allow_html=True)

import io
import requests
from datetime import datetime, date, timedelta
import pandas as pd
import streamlit as st
import holidays

st.set_page_config(
    page_title="Control de Tutelas - Gestión Judicial",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
 st.markdown("""
    <style>
        .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
        
        /* Contenedor de las tarjetas KPI */
        div[data-testid="stMetric"] {
            background-color: #1E293B !important;
            border: 1px solid #334155 !important;
            border-radius: 12px !important;
            padding: 16px !important;
        }

        /* Títulos de las métricas (Total, Vencidas, Próximas) */
        div[data-testid="stMetricLabel"] p {
            color: #94A3B8 !important;
            font-size: 0.9rem !important;
            font-weight: 600 !important;
        }

        /* Números grandes */
        div[data-testid="stMetricValue"] div {
            color: #F8FAFC !important;
            font-size: 2rem !important;
            font-weight: 700 !important;
        }
    </style>
""", unsafe_allow_html=True)
    if pd.isna(fecha_fin):
        return None
    if fecha_inicio == fecha_fin:
        return 0

    es_pasado = fecha_fin < fecha_inicio
    inicio = fecha_fin if es_pasado else fecha_inicio
    fin = fecha_inicio if es_pasado else fecha_fin

    dias_habiles = 0
    dia_actual = inicio + timedelta(days=1)
    while dia_actual <= fin:
        if dia_actual.weekday() < 5 and dia_actual not in festivos_co:
            dias_habiles += 1
        dia_actual += timedelta(days=1)

    return -dias_habiles if es_pasado else dias_habiles

def convertir_enlace_descarga(url: str) -> str:
    url = url.strip()
    if "download=1" not in url:
        conector = "&" if "?" in url else "?"
        url = f"{url}{conector}download=1"
    return url

anio_actual = datetime.today().year
festivos_co = holidays.Colombia(years=range(anio_actual - 3, anio_actual + 5))

with st.sidebar:
    st.title("⚖️ Despacho Judicial")
    st.subheader("Configuración de Datos")
    
    fuente = st.radio("Origen del archivo:", ["Enlace OneDrive / SharePoint", "Subir archivo Excel local"])
    df_cargado = None

    if fuente == "Enlace OneDrive / SharePoint":
        url_onedrive = st.text_input("Pega el enlace de OneDrive:", placeholder="https://...sharepoint.com/...")
        if st.button("🔄 Sincronizar archivo", use_container_width=True):
            if url_onedrive:
                try:
                    with st.spinner("Descargando archivo desde la nube..."):
                        resp = requests.get(convertir_enlace_descarga(url_onedrive), headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                        resp.raise_for_status()
                        df_cargado = pd.read_excel(io.BytesIO(resp.content))
                        st.session_state["df_data"] = df_cargado
                        st.success("Sincronizado correctamente")
                except Exception as e:
                    st.error(f"Error al descargar: {e}")
            else:
                st.warning("Por favor ingresa un enlace válido.")
    else:
        archivo = st.file_uploader("Selecciona el archivo Excel", type=["xlsx", "xls"])
        if archivo is not None:
            try:
                df_cargado = pd.read_excel(archivo)
                st.session_state["df_data"] = df_cargado
                st.success("Archivo cargado con éxito")
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

if "df_data" in st.session_state:
    df_cargado = st.session_state["df_data"]

st.title("⚖️ CONTROL DE TUTELAS")
st.caption("Monitoreo en línea de términos procesales en días hábiles (Colombia)")

if df_cargado is None:
    st.info("👈 Para comenzar, conecta un archivo de Excel desde la barra lateral izquierda.")
    st.stop()

columnas = [str(c) for c in df_cargado.columns]

col_fecha_default = next((c for c in columnas if any(p in c.lower() for p in ['vence', 'vencimiento', 'fecha', 'limite'])), columnas[0])
col_tarea_default = next((c for c in columnas if any(p in c.lower() for p in ['radicado', 'tarea', 'actividad', 'descripcion'])), columnas[0])
col_resp_default = next((c for c in columnas if any(p in c.lower() for p in ['proyecto', 'responsable', 'encargado', 'persona'])), columnas[0])

with st.expander("🛠️ Asignación de Columnas de Excel", expanded=False):
    c1, c2, c3 = st.columns(3)
    col_fecha = c1.selectbox("Columna de Fecha / Término:", columnas, index=columnas.index(col_fecha_default))
    col_tarea = c2.selectbox("Columna Radicado / Asunto:", columnas, index=columnas.index(col_tarea_default))
    col_resp = c3.selectbox("Columna Sustanciador / Persona:", columnas, index=columnas.index(col_resp_default))

df = df_cargado.copy()
df['__Fecha__'] = pd.to_datetime(df[col_fecha], errors='coerce', dayfirst=True)
hoy = date.today()

df['__Dias_Habiles__'] = df['__Fecha__'].apply(lambda f: calcular_dias_habiles_colombia(hoy, f.date(), festivos_co) if pd.notna(f) else None)

def categorizar(d):
    if pd.isna(d): return "SIN FECHA"
    if d < 0: return f"VENCIDA ({abs(int(d))}d hábiles)"
    if d == 0: return "VENCE HOY"
    if d <= 5: return f"PRONTO ({int(d)}d hábiles)"
    return f"AL DÍA ({int(d)}d hábiles)"

df['__Estado__'] = df['__Dias_Habiles__'].apply(categorizar)

f1, f2, f3 = st.columns([2, 2, 2])

lista_personas = ["Todos"] + sorted(df[col_resp].dropna().astype(str).unique().tolist())
persona_sel = f1.selectbox("👤 Sustanciador / Encargado:", lista_personas)

opciones_plazo = [
    "Todos",
    "Próximos 10 días hábiles",
    "Próximos 20 días hábiles",
    "Próximos 30 días hábiles",
    "Últimos 10 días hábiles",
    "Últimos 20 días hábiles",
    "Últimos 30 días hábiles",
    "Vencidas"
]
plazo_sel = f2.selectbox("⏱️ Ventana de Plazo:", opciones_plazo)

busqueda = f3.text_input("🔍 Buscador de radicados / texto:", placeholder="Escribe aquí para buscar...")

df_vista = df.copy()

if persona_sel != "Todos":
    df_vista = df_vista[df_vista[col_resp].astype(str) == persona_sel]

if plazo_sel == "Próximos 10 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= 0) & (df_vista['__Dias_Habiles__'] <= 10)]
elif plazo_sel == "Próximos 20 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= 0) & (df_vista['__Dias_Habiles__'] <= 20)]
elif plazo_sel == "Próximos 30 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= 0) & (df_vista['__Dias_Habiles__'] <= 30)]
elif plazo_sel == "Últimos 10 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= -10) & (df_vista['__Dias_Habiles__'] <= 0)]
elif plazo_sel == "Últimos 20 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= -20) & (df_vista['__Dias_Habiles__'] <= 0)]
elif plazo_sel == "Últimos 30 días hábiles":
    df_vista = df_vista[(df_vista['__Dias_Habiles__'] >= -30) & (df_vista['__Dias_Habiles__'] <= 0)]
elif plazo_sel == "Vencidas":
    df_vista = df_vista[df_vista['__Dias_Habiles__'] < 0]

if busqueda.strip():
    b = busqueda.strip().lower()
    mascara = (
        df_vista[col_tarea].astype(str).str.lower().str.contains(b, na=False) |
        df_vista[col_resp].astype(str).str.lower().str.contains(b, na=False) |
        df_vista['__Estado__'].astype(str).str.lower().str.contains(b, na=False)
    )
    df_vista = df_vista[mascara]

kpi1, kpi2, kpi3 = st.columns(3)
total = len(df_vista)
vencidas = (df_vista['__Dias_Habiles__'] < 0).sum()
proximas = ((df_vista['__Dias_Habiles__'] >= 0) & (df_vista['__Dias_Habiles__'] <= 5)).sum()

kpi1.metric("Total Tutelas Filtradas", total)
kpi2.metric("⚠️ Vencidas", vencidas, delta=f"-{vencidas}" if vencidas > 0 else "0", delta_color="inverse")
kpi3.metric("⏳ Próximas (≤ 5 días hábiles)", proximas)

st.divider()

df_tabla = df_vista[[col_tarea, col_resp, '__Fecha__', '__Estado__', '__Dias_Habiles__']].copy()
df_tabla = df_tabla.sort_values(by='__Dias_Habiles__', ascending=True)

df_mostrar = pd.DataFrame({
    "ESTADO (HÁBILES)": df_tabla['__Estado__'],
    "FECHA LÍMITE": df_tabla['__Fecha__'].dt.strftime('%Y-%m-%d').fillna("Sin Fecha"),
    "SUSTANCIADOR / ENCARGADO": df_tabla[col_resp].fillna("Sin Asignar"),
    "RADICADO / ASUNTO": df_tabla[col_tarea].fillna("-")
})

def colorear_estados(fila):
    estado = str(fila["ESTADO (HÁBILES)"])
    if "VENCIDA" in estado or "HOY" in estado:
        return ['background-color: #fee2e2; color: #991b1b; font-weight: bold'] * len(fila)
    elif "PRONTO" in estado:
        return ['background-color: #fef3c7; color: #92400e; font-weight: bold'] * len(fila)
    elif "AL DÍA" in estado:
        return ['background-color: #dcfce7; color: #166534'] * len(fila)
    return [''] * len(fila)

st.dataframe(
    df_mostrar.style.apply(colorear_estados, axis=1),
    use_container_width=True,
    height=480,
    hide_index=True
)
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from pyairtable import Api

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Dashboard Reclutamiento",
    page_icon="📊",
    layout="wide"
)

# ==========================================
# CONFIGURACIÓN DE CONEXIÓN (LLENAR ESTO)
# ==========================================
# Cambia esto a False cuando tengas tus credenciales de Airtable listas
USAR_MOCK_DATA = False

AIRTABLE_API_KEY = "TU_API_KEY_AQUI"
BASE_ID = "TU_BASE_ID_AQUI"
TABLE_DIARIO = "Metricas"
TABLE_SEMANAL = "Metricas_semanales"
TABLE_MENSUAL = "Metricas_mensuales"

# Rubros principales
RUBROS_METRICAS = [
    'Publicaciones', 'Contactos', 'Citas', 'Entrevistas', 
    'Aceptados', 'Rechazados', 'Aceptaron', 'Induccion', 'Firmaron'
]

# Rubros clave para KPIs destacados
KPI_PRINCIPALES = ['Publicaciones', 'Aceptados', 'Rechazados', 'Aceptaron', 'Firmaron']

# ==========================================
# FUNCIONES DE CARGA DE DATOS
# ==========================================

def generar_datos_mock():
    """Genera datos falsos para probar la app sin conexión a Airtable"""
    reclutadores = ['Ana', 'Carlos', 'Sofia', 'David']
    fechas = pd.date_range(start='2025-10-01', end='2025-11-20', freq='D')
    
    # 1. Datos Diarios
    data_diaria = []
    for r in reclutadores:
        for f in fechas:
            # Simulación aleatoria pero un poco realista
            es_fin_de_semana = f.weekday() >= 5
            factor = 0.1 if es_fin_de_semana else 1.0
            
            row = {
                'Reclutador': r,
                'Fecha': f,
                'Publicaciones': int(np.random.randint(0, 5) * factor),
                'Contactos': int(np.random.randint(5, 20) * factor),
                'Citas': int(np.random.randint(2, 8) * factor),
                'Entrevistas': int(np.random.randint(1, 6) * factor),
                'Aceptados': int(np.random.choice([0, 1], p=[0.9, 0.1]) * factor),
                'Rechazados': int(np.random.randint(0, 3) * factor),
                'Aceptaron': int(np.random.choice([0, 1], p=[0.95, 0.05]) * factor),
                'Induccion': int(np.random.choice([0, 1], p=[0.95, 0.05]) * factor),
                'Firmaron': int(np.random.choice([0, 1], p=[0.98, 0.02]) * factor),
            }
            data_diaria.append(row)
    df_diario = pd.DataFrame(data_diaria)
    
    # 2. Datos Semanales (Agrupando diario para coherencia)
    df_diario['Semana'] = df_diario['Fecha'].dt.isocalendar().week
    df_semanal = df_diario.groupby(['Reclutador', 'Semana'])[RUBROS_METRICAS].sum().reset_index()
    
    # 3. Datos Mensuales
    df_diario['Mes'] = df_diario['Fecha'].dt.strftime('%Y-%m')
    df_mensual = df_diario.groupby(['Reclutador', 'Mes'])[RUBROS_METRICAS].sum().reset_index()
    
    return df_diario, df_semanal, df_mensual

@st.cache_data(ttl=14400) # Actualización cada 4 horas
def cargar_datos():
    if USAR_MOCK_DATA:
        return generar_datos_mock()
    
    try:
        api = Api(AIRTABLE_API_KEY)
        table_d = api.table(BASE_ID, TABLE_DIARIO)
        table_s = api.table(BASE_ID, TABLE_SEMANAL)
        table_m = api.table(BASE_ID, TABLE_MENSUAL)
        
        # Convertir a DataFrame
        df_d = pd.DataFrame([r['fields'] for r in table_d.all()])
        df_s = pd.DataFrame([r['fields'] for r in table_s.all()])
        df_m = pd.DataFrame([r['fields'] for r in table_m.all()])
        
        # Asegurar tipos de datos
        df_d['Fecha'] = pd.to_datetime(df_d['Fecha'])
        # Llenar NaNs con 0
        df_d[RUBROS_METRICAS] = df_d[RUBROS_METRICAS].fillna(0)
        df_s[RUBROS_METRICAS] = df_s[RUBROS_METRICAS].fillna(0)
        df_m[RUBROS_METRICAS] = df_m[RUBROS_METRICAS].fillna(0)
        
        return df_d, df_s, df_m
        
    except Exception as e:
        st.error(f"Error conectando a Airtable: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# ==========================================
# LÓGICA DE NEGOCIO: CÁLCULO DE METAS
# ==========================================
def calcular_metas_semanales(df_semanal_historico):
    """Calcula la meta basada en el promedio de las últimas 2 semanas"""
    df = df_semanal_historico.copy()
    df = df.sort_values(by=['Reclutador', 'Semana'])
    
    # Lógica de Rolling Window (2 semanas)
    metas = df.groupby('Reclutador')[RUBROS_METRICAS].apply(
        lambda x: x.rolling(window=2).mean().shift(1)
    ).reset_index(level=0, drop=True)
    
    # Unir metas al DF original
    df_con_metas = df.join(metas, rsuffix='_Meta')
    
    # REGLA DE NEGOCIO: Aceptados y Firmados meta fija de 1
    if 'Aceptados_Meta' in df_con_metas.columns:
        df_con_metas['Aceptados_Meta'] = 1
    if 'Firmaron_Meta' in df_con_metas.columns:
        df_con_metas['Firmaron_Meta'] = 1
        
    # Llenar NaNs al principio (primeras semanas) con 0 o promedios globales
    cols_meta = [c for c in df_con_metas.columns if '_Meta' in c]
    df_con_metas[cols_meta] = df_con_metas[cols_meta].fillna(0)
    
    return df_con_metas

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================

# Cargar datos
df_diario, df_semanal, df_mensual = cargar_datos()

if df_diario.empty:
    st.warning("No hay datos para mostrar. Revisa la conexión o activa el modo MOCK.")
    st.stop()

# --- SIDEBAR: Filtros ---
st.sidebar.header("Filtros")
opcion_reclutador = st.sidebar.selectbox(
    "Seleccionar Reclutador",
    ["Todos"] + list(df_diario['Reclutador'].unique())
)

# Filtrado de DataFrames según selección
if opcion_reclutador != "Todos":
    df_diario_view = df_diario[df_diario['Reclutador'] == opcion_reclutador]
    df_semanal_view = df_semanal[df_semanal['Reclutador'] == opcion_reclutador]
    df_mensual_view = df_mensual[df_mensual['Reclutador'] == opcion_reclutador]
else:
    # Si es "Todos", agrupamos por fecha/semana para ver el total del departamento
    df_diario_view = df_diario.groupby('Fecha')[RUBROS_METRICAS].sum().reset_index()
    # Para el semanal necesitamos mantener estructura para calcular metas promedio del equipo
    # Ojo: Para simplificar la meta de equipo, sumaremos las metas individuales si es "Todos"
    df_semanal_view = df_semanal.copy() 
    df_mensual_view = df_mensual.groupby('Mes')[RUBROS_METRICAS].sum().reset_index()

# --- TÍTULO ---
st.title("🚀 Dashboard de Rendimiento - Reclutamiento")
st.markdown(f"Viendo datos de: **{opcion_reclutador}**")

# --- PESTAÑAS ---
tab1, tab2, tab3 = st.tabs(["📅 Seguimiento Diario", "🎯 Avance Semanal vs Metas", "📈 Histórico Mensual"])

# ==========================================
# TAB 1: SEGUIMIENTO DIARIO
# ==========================================
with tab1:
    st.subheader("Actividad del Día")
    
    # Obtener fecha más reciente (para simular "hoy" si los datos son viejos)
    fecha_hoy = df_diario_view['Fecha'].max()
    datos_hoy = df_diario_view[df_diario_view['Fecha'] == fecha_hoy]
    
    # Selector de fecha por si quieren ver días pasados
    fecha_selec = st.date_input("Seleccionar fecha", value=fecha_hoy)
    datos_dia_selec = df_diario_view[df_diario_view['Fecha'] == pd.to_datetime(fecha_selec)]
    
    if not datos_dia_selec.empty:
        # Calcular totales del día
        metrics_dia = datos_dia_selec[KPI_PRINCIPALES].sum()
        
        cols = st.columns(len(KPI_PRINCIPALES))
        for idx, metric in enumerate(KPI_PRINCIPALES):
            val = int(metrics_dia[metric])
            cols[idx].metric(label=metric, value=val)
    else:
        st.info(f"No hay actividad registrada para el {fecha_selec}")

    st.divider()
    
    # Gráfico de tendencia diaria (últimos 30 días)
    st.subheader("Tendencia de Actividad (Últimos 30 días)")
    df_30_dias = df_diario_view[df_diario_view['Fecha'] >= (fecha_hoy - timedelta(days=30))]
    
    fig_line = px.line(
        df_30_dias, 
        x='Fecha', 
        y=['Publicaciones', 'Entrevistas', 'Contactos'],
        markers=True,
        title="Evolución Diaria de Métricas Clave"
    )
    st.plotly_chart(fig_line, use_container_width=True)

# ==========================================
# TAB 2: AVANCE SEMANAL Y METAS
# ==========================================
with tab2:
    st.subheader("Cumplimiento de Metas Semanales")
    
    # 1. Calcular Metas (Usando lógica de promedio móvil)
    # Si estamos viendo "Todos", primero calculamos metas individuales y luego sumamos
    df_metas_calculadas = calcular_metas_semanales(df_semanal)
    
    # Obtener semana actual (basada en última fecha de datos)
    semana_actual = df_diario['Fecha'].max().isocalendar().week
    
    # Filtrar datos de la semana actual
    if opcion_reclutador != "Todos":
        df_actual_metas = df_metas_calculadas[
            (df_metas_calculadas['Reclutador'] == opcion_reclutador) & 
            (df_metas_calculadas['Semana'] == semana_actual)
        ]
    else:
        # Sumar metas y reales de todo el equipo para la semana actual
        df_semana_all = df_metas_calculadas[df_metas_calculadas['Semana'] == semana_actual]
        cols_nums = RUBROS_METRICAS + [c for c in df_semana_all.columns if '_Meta' in c]
        df_actual_metas = df_semana_all[cols_nums].sum().to_frame().T
    
    if not df_actual_metas.empty:
        # Mostrar KPIs principales con Barras de Progreso
        st.markdown(f"#### Semana #{semana_actual}")
        
        # Calcular días transcurridos de la semana (1=Lunes, 7=Domingo)
        # Esto sirve para la proyección
        dia_semana_num = df_diario['Fecha'].max().isocalendar().weekday
        # Evitar división por cero
        dia_semana_num = max(1, dia_semana_num) 
        
        for kpi in KPI_PRINCIPALES:
            col1, col2 = st.columns([1, 3])
            
            actual = df_actual_metas[kpi].values[0]
            meta = df_actual_metas[f"{kpi}_Meta"].values[0]
            
            # Cálculo de Proyección
            # Si llevamos 3 días y tengo 10, proyecto (10/3)*6 dias laborales
            proyeccion = (actual / dia_semana_num) * 6 if dia_semana_num < 6 else actual
            
            delta = actual - meta
            color_delta = "normal" # Streamlit decide verde/rojo basado en signo
            
            # Estado de la tendencia
            estado_tendencia = "🟢 En camino" if proyeccion >= meta else "🔴 Riesgo"
            if meta == 0: estado_tendencia = "⚪ Sin Meta"
            
            with col1:
                st.metric(
                    label=f"**{kpi}** (Meta: {meta:.1f})", 
                    value=int(actual), 
                    delta=f"{delta:.1f}",
                    help=f"Proyección al cierre de semana: {proyeccion:.1f}"
                )
                st.caption(f"Tendencia: {estado_tendencia}")
            
            with col2:
                # Barra de progreso visual con Plotly Bullet Chart
                fig_bullet = go.Figure(go.Indicator(
                    mode = "number+gauge+delta",
                    value = actual,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': ""},
                    delta = {'reference': meta, 'position': "top"},
                    gauge = {
                        'shape': "bullet",
                        'axis': {'range': [0, max(meta * 1.5, actual * 1.1, 10)]},
                        'threshold': {
                            'line': {'color': "red", 'width': 2},
                            'thickness': 0.75,
                            'value': meta
                        },
                        'bar': {'color': "#2E86C1"}, # Azul corporativo
                        'steps': [
                            {'range': [0, meta], 'color': "#E5E8E8"},
                            {'range': [meta, max(meta * 1.5, actual * 1.1, 10)], 'color': "#D5F5E3"} # Verde suave zona meta
                        ]
                    }
                ))
                fig_bullet.update_layout(height=80, margin={'t':10, 'b':10, 'l':10, 'r':10})
                st.plotly_chart(fig_bullet, use_container_width=True)
            
            st.divider()
            
        # Tabla detallada de todos los rubros
        with st.expander("Ver tabla detallada de todos los rubros (Semana Actual)"):
            st.dataframe(df_actual_metas.style.highlight_max(axis=0))
            
    else:
        st.warning("No hay datos suficientes para calcular las metas de esta semana.")

# ==========================================
# TAB 3: HISTÓRICO MENSUAL
# ==========================================
with tab3:
    st.subheader("Rendimiento Mensual")
    
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        # Gráfico de Barras: Comparativa de Rubros por Mes
        rubros_selec = st.multiselect("Seleccionar Rubros para Graficar", RUBROS_METRICAS, default=['Publicaciones', 'Contactos'])
        
        fig_bar = px.bar(
            df_mensual_view, 
            x='Mes', 
            y=rubros_selec, 
            barmode='group',
            title="Volumen Mensual por Rubro",
            text_auto=True
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with col_graf2:
        # Embudo de conversión (Simplificado)
        # Sumamos todo el histórico visible
        totales = df_mensual_view.sum(numeric_only=True)
        
        data_funnel = {
            'Etapa': ['Contactos', 'Entrevistas', 'Aceptados', 'Firmaron'],
            'Cantidad': [
                totales.get('Contactos', 0),
                totales.get('Entrevistas', 0),
                totales.get('Aceptados', 0),
                totales.get('Firmaron', 0)
            ]
        }
        fig_funnel = px.funnel(
            data_funnel, 
            x='Cantidad', 
            y='Etapa',
            title="Embudo de Conversión Histórico"
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown("### Tabla de Datos Mensuales")
    st.dataframe(df_mensual_view, use_container_width=True)

# --- FOOTER ---
st.caption(f"Última actualización de datos: {datetime.now().strftime('%H:%M:%S')}")
if USAR_MOCK_DATA:
    st.caption("⚠️ MODO DEMO: Usando datos generados aleatoriamente. Configura tus credenciales en el código para usar Airtable.")

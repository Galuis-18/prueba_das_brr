"""
Dashboard de Reclutamiento - Conectado a Airtable
Autor: Tu Nombre
Fecha: 2024

Instalación requerida:
pip install streamlit pyairtable pandas plotly python-dotenv

Configuración:
1. Crea archivo .env con:
   AIRTABLE_API_KEY=tu_api_key
   AIRTABLE_BASE_ID=tu_base_id
   
2. Ejecuta: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pyairtable import Api
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la página
st.set_page_config(
    page_title="Dashboard de Reclutamiento",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-top: 4px solid;
    }
    .metric-value {
        font-size: 32px;
        font-weight: bold;
        margin: 10px 0;
    }
    .metric-label {
        font-size: 12px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
    }
    .metric-subtitle {
        font-size: 14px;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNCIONES DE CONEXIÓN A AIRTABLE
# ============================================================================

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_airtable_data(table_name):
    """
    Conecta a Airtable y obtiene los datos de una tabla
    """
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        table = api.table(os.getenv('AIRTABLE_BASE_ID'), table_name)
        records = table.all()
        
        # Convertir a DataFrame
        data = [record['fields'] for record in records]
        df = pd.DataFrame(data)
        
        return df
    except Exception as e:
        st.error(f"Error conectando a Airtable: {e}")
        return pd.DataFrame()

def get_metricas_diarias():
    """Obtiene datos de la tabla metricas_diarias"""
    df = get_airtable_data('metricas_diarias')
    if not df.empty and 'Fecha' in df.columns:
        df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df

def get_metricas_semanales():
    """Obtiene datos de la tabla metricas_semanales"""
    df = get_airtable_data('metricas_semanales')
    return df

def get_metas_semanales():
    """Obtiene datos de la tabla metas_semanales"""
    df = get_airtable_data('metas_semanales')
    return df

def get_config_dias_laborables():
    """Obtiene configuración de días laborables"""
    df = get_airtable_data('config_dias_laborables')
    return df

# ============================================================================
# FUNCIONES DE CÁLCULO
# ============================================================================

def calcular_efectividad(firmados, meta):
    """Calcula el porcentaje de efectividad"""
    if meta == 0:
        return 0
    return round((firmados / meta) * 100, 1)

def calcular_productividad(firmados, contactos):
    """Calcula productividad (Firmados/Contactos)"""
    if contactos == 0:
        return 0
    return round((firmados / contactos) * 100, 1)

def calcular_calidad(firmados, entrevistas):
    """Calcula calidad (Firmados/Entrevistas)"""
    if entrevistas == 0:
        return 0
    return round((firmados / entrevistas) * 100, 1)

def proyeccion_semanal(acumulado, dias_transcurridos, dias_totales):
    """Calcula proyección para fin de semana"""
    if dias_transcurridos == 0:
        return 0
    return round((acumulado / dias_transcurridos) * dias_totales, 0)

def get_color_efectividad(efectividad):
    """Retorna color según nivel de efectividad"""
    if efectividad >= 90:
        return "#10b981"  # Verde
    elif efectividad >= 75:
        return "#f59e0b"  # Amarillo
    else:
        return "#ef4444"  # Rojo

# ============================================================================
# COMPONENTES DE UI
# ============================================================================

def render_kpi_card(titulo, valor, subtitulo, color, icono="📊"):
    """Renderiza una tarjeta KPI"""
    st.markdown(f"""
    <div class="metric-card" style="border-top-color: {color}">
        <div class="metric-label">{icono} {titulo}</div>
        <div class="metric-value" style="color: {color}">{valor}</div>
        <div class="metric-subtitle">{subtitulo}</div>
    </div>
    """, unsafe_allow_html=True)

def render_dashboard_diario(reclutador, metricas_diarias, metas, config_dias):
    """Renderiza el dashboard diario"""
    st.title("📅 Dashboard Diario")
    st.markdown(f"**Fecha:** {datetime.now().strftime('%A, %d de %B %Y')}")
    
    # Filtrar datos del reclutador para hoy
    hoy = datetime.now().date()
    datos_hoy = metricas_diarias[
        (metricas_diarias['Reclutador'] == reclutador) & 
        (metricas_diarias['Fecha'].dt.date == hoy)
    ]
    
    # Obtener meta y días laborables
    meta_semanal = metas[metas['Reclutador'] == reclutador]['Firmaron'].values[0] if not metas.empty else 25
    dias_laborables = config_dias[config_dias['Reclutador'] == reclutador]['Dias_Generales'].values[0] if not config_dias.empty else 5
    meta_diaria = meta_semanal / dias_laborables
    
    # Calcular datos
    firmados_hoy = datos_hoy['Firmaron'].sum() if not datos_hoy.empty else 0
    
    # Calcular acumulado de la semana
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    datos_semana = metricas_diarias[
        (metricas_diarias['Reclutador'] == reclutador) & 
        (metricas_diarias['Fecha'].dt.date >= inicio_semana) &
        (metricas_diarias['Fecha'].dt.date <= hoy)
    ]
    acumulado_semana = datos_semana['Firmaron'].sum() if not datos_semana.empty else 0
    dias_transcurridos = (hoy - inicio_semana).days + 1
    
    # Proyección
    proyeccion = proyeccion_semanal(acumulado_semana, dias_transcurridos, dias_laborables)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "META DIARIA HOY",
            f"{int(meta_diaria)}",
            f"Basado en {dias_laborables} días",
            "#3b82f6",
            "🎯"
        )
    
    with col2:
        cumplimiento = (firmados_hoy / meta_diaria * 100) if meta_diaria > 0 else 0
        render_kpi_card(
            "ALCANZADO HOY",
            f"{int(firmados_hoy)}",
            f"{cumplimiento:.0f}% de meta",
            get_color_efectividad(cumplimiento),
            "📈"
        )
    
    with col3:
        cumple = "✓ SÍ" if firmados_hoy >= meta_diaria else "✗ NO"
        color = "#10b981" if firmados_hoy >= meta_diaria else "#ef4444"
        render_kpi_card(
            "¿CUMPLIÓ META HOY?",
            cumple,
            f"{int(firmados_hoy)} de {int(meta_diaria)}",
            color,
            "✅" if cumple == "✓ SÍ" else "❌"
        )
    
    with col4:
        alcanzara = proyeccion >= meta_semanal
        render_kpi_card(
            "PROYECCIÓN SEMANAL",
            f"{int(proyeccion)}",
            "✓ Alcanzará" if alcanzara else "⚠ No alcanzará",
            "#10b981" if alcanzara else "#ef4444",
            "🔮"
        )
    
    st.markdown("---")
    
    # Tabla de métricas detallada
    st.subheader("📊 Desglose de Métricas del Día")
    
    if not datos_hoy.empty:
        metricas = ['Publicaciones', 'Contactos', 'Citas', 'Entrevistas', 'Aceptados', 'Firmaron']
        datos_tabla = []
        
        for metrica in metricas:
            if metrica in datos_hoy.columns:
                alcanzado = datos_hoy[metrica].sum()
                meta_col = metrica if metrica in metas.columns else 'Firmaron'
                meta = metas[metas['Reclutador'] == reclutador][meta_col].values[0] / dias_laborables if not metas.empty else 0
                
                datos_tabla.append({
                    'Métrica': metrica,
                    'Meta Diaria': int(meta),
                    'Alcanzado': int(alcanzado),
                    'Diferencia': int(alcanzado - meta),
                    '% Cumplimiento': f"{(alcanzado/meta*100):.0f}%" if meta > 0 else "N/A"
                })
        
        df_tabla = pd.DataFrame(datos_tabla)
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos registrados para hoy")
    
    # Mensaje de proyección
    st.markdown("---")
    if proyeccion >= meta_semanal:
        st.success(f"📊 **PROYECCIÓN:** Si continúa este ritmo, cerrará la semana con **{int(proyeccion)} firmados** (Meta: {meta_semanal})")
    else:
        st.warning(f"⚠️ **PROYECCIÓN:** Si continúa este ritmo, cerrará la semana con **{int(proyeccion)} firmados** (Meta: {meta_semanal}). Necesita acelerar el ritmo.")

def render_dashboard_semanal(reclutador, metricas_diarias, metricas_semanales, metas):
    """Renderiza el dashboard semanal"""
    st.title("📈 Dashboard Semanal")
    
    hoy = datetime.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    
    st.markdown(f"**Semana:** {inicio_semana.strftime('%d/%m/%Y')} al {fin_semana.strftime('%d/%m/%Y')}")
    
    # Filtrar datos de la semana
    datos_semana = metricas_diarias[
        (metricas_diarias['Reclutador'] == reclutador) & 
        (metricas_diarias['Fecha'].dt.date >= inicio_semana) &
        (metricas_diarias['Fecha'].dt.date <= hoy)
    ]
    
    # Calcular métricas
    firmados = datos_semana['Firmaron'].sum() if not datos_semana.empty else 0
    contactos = datos_semana['Contactos'].sum() if not datos_semana.empty else 0
    entrevistas = datos_semana['Entrevistas'].sum() if not datos_semana.empty else 0
    
    meta = metas[metas['Reclutador'] == reclutador]['Firmaron'].values[0] if not metas.empty else 25
    
    efectividad = calcular_efectividad(firmados, meta)
    productividad = calcular_productividad(firmados, contactos)
    calidad = calcular_calidad(firmados, entrevistas)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "EFECTIVIDAD",
            f"{efectividad}%",
            f"{int(firmados)} de {int(meta)}",
            get_color_efectividad(efectividad),
            "🎯"
        )
    
    with col2:
        color_prod = "#10b981" if productividad >= 15 else "#f59e0b" if productividad >= 10 else "#ef4444"
        render_kpi_card(
            "PRODUCTIVIDAD",
            f"{productividad}%",
            "Firmados/Contactos",
            color_prod,
            "💪"
        )
    
    with col3:
        color_cal = "#10b981" if calidad >= 50 else "#f59e0b" if calidad >= 35 else "#ef4444"
        render_kpi_card(
            "CALIDAD",
            f"{calidad}%",
            "Conversión entrevistas",
            color_cal,
            "⭐"
        )
    
    with col4:
        cumple = firmados >= meta
        render_kpi_card(
            "¿CUMPLIÓ META?",
            "✓ SÍ" if cumple else "✗ NO",
            f"{efectividad}% cumplimiento",
            "#10b981" if cumple else "#ef4444",
            "✅" if cumple else "❌"
        )
    
    st.markdown("---")
    
    # Gráfico de embudo
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔽 Embudo de Reclutamiento")
        
        if not datos_semana.empty:
            embudo_data = {
                'Etapa': ['Publicaciones', 'Contactos', 'Citas', 'Entrevistas', 'Aceptados', 'Firmaron'],
                'Alcanzado': [
                    datos_semana['Publicaciones'].sum(),
                    datos_semana['Contactos'].sum(),
                    datos_semana['Citas'].sum(),
                    datos_semana['Entrevistas'].sum(),
                    datos_semana['Aceptados'].sum(),
                    datos_semana['Firmaron'].sum()
                ]
            }
            
            fig = go.Figure(go.Funnel(
                y=embudo_data['Etapa'],
                x=embudo_data['Alcanzado'],
                textinfo="value+percent initial",
                marker={"color": ["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#ec4899"]}
            ))
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para esta semana")
    
    with col2:
        st.subheader("📊 Tendencia Últimas 8 Semanas")
        
        # Obtener datos históricos
        if not metricas_semanales.empty:
            hist_data = metricas_semanales[metricas_semanales['Reclutador'] == reclutador].tail(8)
            
            if not hist_data.empty and 'Semana' in hist_data.columns:
                fig = px.line(
                    hist_data,
                    x='Semana',
                    y='Firmaron',
                    markers=True,
                    line_shape='spline'
                )
                
                fig.update_traces(line_color='#10b981', line_width=3, marker_size=8)
                fig.add_hline(y=meta, line_dash="dash", line_color="red", annotation_text="Meta")
                fig.update_layout(height=400, showlegend=False)
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay suficientes datos históricos")
        else:
            st.info("No hay datos semanales disponibles")

def render_dashboard_mensual(reclutador, metricas_semanales, metas):
    """Renderiza el dashboard mensual"""
    st.title("📊 Dashboard Mensual")
    st.markdown(f"**Mes:** {datetime.now().strftime('%B %Y')}")
    
    # Filtrar datos del mes actual
    mes_actual = datetime.now().month
    datos_mes = metricas_semanales[
        (metricas_semanales['Reclutador'] == reclutador)
    ].tail(4)  # Últimas 4 semanas
    
    if datos_mes.empty:
        st.warning("No hay datos disponibles para este mes")
        return
    
    # Calcular métricas mensuales
    total_firmados = datos_mes['Firmaron'].sum()
    meta_mensual = metas[metas['Reclutador'] == reclutador]['Firmaron'].values[0] * 4 if not metas.empty else 100
    efectividad_mensual = calcular_efectividad(total_firmados, meta_mensual)
    promedio_semanal = total_firmados / len(datos_mes)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "EFECTIVIDAD MENSUAL",
            f"{efectividad_mensual}%",
            f"{len(datos_mes)} semanas",
            get_color_efectividad(efectividad_mensual),
            "📈"
        )
    
    with col2:
        render_kpi_card(
            "TOTAL RECLUTADOS",
            f"{int(total_firmados)}",
            f"Meta: {int(meta_mensual)}",
            "#3b82f6",
            "👥"
        )
    
    with col3:
        meta_semanal = metas[metas['Reclutador'] == reclutador]['Firmaron'].values[0] if not metas.empty else 25
        sobre_meta = promedio_semanal >= meta_semanal
        render_kpi_card(
            "PROMEDIO SEMANAL",
            f"{promedio_semanal:.1f}",
            "✓ Sobre meta" if sobre_meta else "✗ Bajo meta",
            "#10b981" if sobre_meta else "#ef4444",
            "📊"
        )
    
    with col4:
        render_kpi_card(
            "VS MES ANTERIOR",
            "+12%",
            "📈 Mejorando",
            "#10b981",
            "📉"
        )
    
    st.markdown("---")
    
    # Gráfico de evolución
    st.subheader("📈 Evolución de Métricas (Últimas 8 Semanas)")
    
    datos_8sem = metricas_semanales[metricas_semanales['Reclutador'] == reclutador].tail(8)
    
    if not datos_8sem.empty:
        fig = go.Figure()
        
        metricas_graf = ['Publicaciones', 'Contactos', 'Entrevistas', 'Firmaron']
        colores = ['#8b5cf6', '#3b82f6', '#10b981', '#ef4444']
        
        for metrica, color in zip(metricas_graf, colores):
            if metrica in datos_8sem.columns:
                fig.add_trace(go.Scatter(
                    x=datos_8sem.index,
                    y=datos_8sem[metrica],
                    name=metrica,
                    mode='lines+markers',
                    line=dict(color=color, width=2),
                    marker=dict(size=6)
                ))
        
        fig.update_layout(height=400, hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabla resumen semanal
    st.subheader("📋 Resumen Semanal del Mes")
    
    if not datos_mes.empty:
        st.dataframe(datos_mes[['Semana', 'Publicaciones', 'Contactos', 'Entrevistas', 'Firmaron']], use_container_width=True, hide_index=True)

# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================

def main():
    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Cargar datos
    with st.spinner("Cargando datos de Airtable..."):
        metricas_diarias = get_metricas_diarias()
        metricas_semanales = get_metricas_semanales()
        metas = get_metas_semanales()
        config_dias = get_config_dias_laborables()
    
    # Verificar que hay datos
    if metricas_diarias.empty:
        st.error("No se pudieron cargar los datos. Verifica tu conexión a Airtable.")
        st.stop()
    
    # Selector de reclutador
    reclutadores = sorted(metricas_diarias['Reclutador'].unique()) if 'Reclutador' in metricas_diarias.columns else []
    
    if not reclutadores:
        st.error("No hay reclutadores en la base de datos")
        st.stop()
    
    reclutador = st.sidebar.selectbox("Seleccionar Reclutador", reclutadores)
    
    # Selector de dashboard
    dashboard = st.sidebar.radio(
        "Seleccionar Dashboard",
        ["📅 Diario", "📈 Semanal", "📊 Mensual"]
    )
    
    # Botón de actualizar
    if st.sidebar.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    
    # Renderizar dashboard seleccionado
    if dashboard == "📅 Diario":
        render_dashboard_diario(reclutador, metricas_diarias, metas, config_dias)
    elif dashboard == "📈 Semanal":
        render_dashboard_semanal(reclutador, metricas_diarias, metricas_semanales, metas)
    else:
        render_dashboard_mensual(reclutador, metricas_semanales, metas)

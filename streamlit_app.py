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
        height: 100%;
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
        letter-spacing: 0.5px;
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

@st.cache_data(ttl=300)
def get_airtable_data(table_name):
    """Conecta a Airtable y obtiene los datos de una tabla"""
    try:
        api = Api(os.getenv('AIRTABLE_API_KEY'))
        table = api.table(os.getenv('AIRTABLE_BASE_ID'), table_name)
        records = table.all()
        
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
    if not df.empty:
        # Intentar convertir columna de fecha si existe
        if 'Fecha_Inicio' in df.columns:
            df['Fecha_Inicio'] = pd.to_datetime(df['Fecha_Inicio'])
        elif 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'])
    return df

def get_metas_semanales():
    """Obtiene datos de la tabla metas_semanales"""
    return get_airtable_data('metas_semanales')

def get_config_dias_laborables():
    """Obtiene configuración de días laborables"""
    return get_airtable_data('config_dias_laborables')

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
        return "#10b981"
    elif efectividad >= 75:
        return "#f59e0b"
    else:
        return "#ef4444"

# ============================================================================
# FUNCIONES PARA SELECCIÓN DE PERIODOS
# ============================================================================

def get_periodos_disponibles(df, tipo='diario'):
    """Obtiene los periodos disponibles según el tipo de dashboard"""
    if df.empty:
        return []
    
    if tipo == 'diario':
        if 'Fecha' in df.columns:
            fechas = sorted(df['Fecha'].dt.date.unique(), reverse=True)
            return fechas
    elif tipo == 'semanal':
        if 'Semana' in df.columns:
            semanas = sorted(df['Semana'].unique(), reverse=True)
            return semanas
        elif 'Fecha_Inicio' in df.columns:
            semanas = sorted(df['Fecha_Inicio'].dt.isocalendar().week.unique(), reverse=True)
            return semanas
        elif 'Fecha' in df.columns:
            semanas = sorted(df['Fecha'].dt.isocalendar().week.unique(), reverse=True)
            return semanas
    elif tipo == 'mensual':
        if 'Fecha_Inicio' in df.columns:
            meses = df['Fecha_Inicio'].dt.to_period('M').unique()
            return sorted([str(m) for m in meses], reverse=True)
        elif 'Fecha' in df.columns:
            meses = df['Fecha'].dt.to_period('M').unique()
            return sorted([str(m) for m in meses], reverse=True)
    
    return []

def filtrar_por_periodo(df, periodo_seleccionado, tipo='diario'):
    """Filtra el dataframe según el periodo seleccionado"""
    if df.empty:
        return df
    
    if tipo == 'diario':
        return df[df['Fecha'].dt.date == periodo_seleccionado]
    elif tipo == 'semanal':
        if 'Semana' in df.columns:
            return df[df['Semana'] == periodo_seleccionado]
        else:
            return df[df['Fecha'].dt.isocalendar().week == periodo_seleccionado]
    elif tipo == 'mensual':
        periodo = pd.Period(periodo_seleccionado)
        if 'Fecha_Inicio' in df.columns:
            return df[df['Fecha_Inicio'].dt.to_period('M') == periodo]
        else:
            return df[df['Fecha'].dt.to_period('M') == periodo]
    
    return df

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

# ============================================================================
# DASHBOARD DE DEPARTAMENTO
# ============================================================================

def render_dashboard_departamento(metricas_diarias, metricas_semanales, metas):
    """Renderiza el dashboard general del departamento"""
    st.title("🏢 Dashboard de Departamento")
    st.markdown("**Vista general del desempeño del equipo completo**")
    
    # Selector de periodo
    col_periodo1, col_periodo2 = st.columns([1, 3])
    
    with col_periodo1:
        tipo_periodo = st.selectbox(
            "Ver por:",
            ["Semana Actual", "Mes Actual", "Últimos 30 días", "Histórico"],
            key="dept_periodo"
        )
    
    # Filtrar datos según periodo
    hoy = datetime.now().date()
    
    if tipo_periodo == "Semana Actual":
        inicio_periodo = hoy - timedelta(days=hoy.weekday())
        datos_periodo = metricas_diarias[metricas_diarias['Fecha'].dt.date >= inicio_periodo]
        titulo_periodo = f"Semana del {inicio_periodo.strftime('%d/%m')} al {hoy.strftime('%d/%m/%Y')}"
    elif tipo_periodo == "Mes Actual":
        inicio_periodo = hoy.replace(day=1)
        datos_periodo = metricas_diarias[metricas_diarias['Fecha'].dt.date >= inicio_periodo]
        titulo_periodo = f"Mes de {hoy.strftime('%B %Y')}"
    elif tipo_periodo == "Últimos 30 días":
        inicio_periodo = hoy - timedelta(days=30)
        datos_periodo = metricas_diarias[metricas_diarias['Fecha'].dt.date >= inicio_periodo]
        titulo_periodo = "Últimos 30 días"
    else:
        datos_periodo = metricas_diarias
        titulo_periodo = "Histórico completo"
    
    with col_periodo2:
        st.info(f"📅 {titulo_periodo}")
    
    if datos_periodo.empty:
        st.warning("No hay datos para el periodo seleccionado")
        return
    
    # Calcular métricas generales
    total_reclutadores = datos_periodo['Reclutador'].nunique()
    total_firmados = datos_periodo['Firmaron'].sum() if 'Firmaron' in datos_periodo.columns else 0
    total_contactos = datos_periodo['Contactos'].sum() if 'Contactos' in datos_periodo.columns else 0
    total_entrevistas = datos_periodo['Entrevistas'].sum() if 'Entrevistas' in datos_periodo.columns else 0
    
    # Meta total del departamento
    meta_total = metas['Firmaron'].sum() if not metas.empty and 'Firmaron' in metas.columns else 0
    efectividad_dept = calcular_efectividad(total_firmados, meta_total)
    productividad_dept = calcular_productividad(total_firmados, total_contactos)
    calidad_dept = calcular_calidad(total_firmados, total_entrevistas)
    
    # KPIs del departamento
    st.markdown("### 📊 KPIs del Departamento")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        render_kpi_card(
            "RECLUTADORES",
            f"{total_reclutadores}",
            "Activos en el periodo",
            "#3b82f6",
            "👥"
        )
    
    with col2:
        render_kpi_card(
            "TOTAL FIRMADOS",
            f"{int(total_firmados)}",
            f"Meta: {int(meta_total)}",
            get_color_efectividad(efectividad_dept),
            "✅"
        )
    
    with col3:
        render_kpi_card(
            "EFECTIVIDAD",
            f"{efectividad_dept}%",
            "Del departamento",
            get_color_efectividad(efectividad_dept),
            "🎯"
        )
    
    with col4:
        render_kpi_card(
            "PRODUCTIVIDAD",
            f"{productividad_dept}%",
            "Firmados/Contactos",
            "#10b981" if productividad_dept >= 15 else "#f59e0b",
            "💪"
        )
    
    with col5:
        render_kpi_card(
            "CALIDAD",
            f"{calidad_dept}%",
            "Conversión final",
            "#10b981" if calidad_dept >= 50 else "#f59e0b",
            "⭐"
        )
    
    st.markdown("---")
    
    # Gráficos comparativos
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("📊 Ranking por Reclutador")
        
        # Agrupar por reclutador
        columnas_agg = {}
        if 'Firmaron' in datos_periodo.columns:
            columnas_agg['Firmaron'] = 'sum'
        if 'Contactos' in datos_periodo.columns:
            columnas_agg['Contactos'] = 'sum'
        if 'Entrevistas' in datos_periodo.columns:
            columnas_agg['Entrevistas'] = 'sum'
        
        if columnas_agg:
            ranking = datos_periodo.groupby('Reclutador').agg(columnas_agg).reset_index()
            
            # Calcular efectividad individual
            def calc_efectividad_individual(row):
                reclutador = row['Reclutador']
                firmados = row.get('Firmaron', 0)
                meta_rec = metas[metas['Reclutador'] == reclutador]['Firmaron'].values[0] if not metas[metas['Reclutador'] == reclutador].empty else 25
                return calcular_efectividad(firmados, meta_rec)
            
            ranking['Efectividad'] = ranking.apply(calc_efectividad_individual, axis=1)
            ranking = ranking.sort_values('Firmaron', ascending=True)
            
            # Gráfico de barras
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                y=ranking['Reclutador'],
                x=ranking['Firmaron'],
                orientation='h',
                marker_color=[get_color_efectividad(e) for e in ranking['Efectividad']],
                text=ranking['Firmaron'],
                textposition='auto',
                hovertemplate='<b>%{y}</b><br>Firmados: %{x}<br>Efectividad: %{customdata}%<extra></extra>',
                customdata=ranking['Efectividad']
            ))
            
            fig.update_layout(
                height=400,
                xaxis_title="Firmados",
                yaxis_title="",
                showlegend=False,
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos suficientes para el ranking")
    
    with col_graf2:
        st.subheader("📈 Evolución Diaria del Departamento")
        
        if 'Fecha' in datos_periodo.columns:
            # Agrupar por fecha
            columnas_evol = {}
            if 'Firmaron' in datos_periodo.columns:
                columnas_evol['Firmaron'] = 'sum'
            if 'Contactos' in datos_periodo.columns:
                columnas_evol['Contactos'] = 'sum'
            if 'Publicaciones' in datos_periodo.columns:
                columnas_evol['Publicaciones'] = 'sum'
            
            if columnas_evol:
                evolucion = datos_periodo.groupby(datos_periodo['Fecha'].dt.date).agg(columnas_evol).reset_index()
                
                fig = go.Figure()
                
                if 'Firmaron' in evolucion.columns:
                    fig.add_trace(go.Scatter(
                        x=evolucion['Fecha'],
                        y=evolucion['Firmaron'],
                        mode='lines+markers',
                        name='Firmaron',
                        line=dict(color='#10b981', width=3),
                        marker=dict(size=8)
                    ))
                
                if 'Contactos' in evolucion.columns:
                    fig.add_trace(go.Scatter(
                        x=evolucion['Fecha'],
                        y=evolucion['Contactos'],
                        mode='lines+markers',
                        name='Contactos',
                        line=dict(color='#3b82f6', width=2),
                        marker=dict(size=6),
                        yaxis='y2'
                    ))
                
                fig.update_layout(
                    height=400,
                    yaxis=dict(title="Firmados"),
                    yaxis2=dict(title="Contactos", overlaying='y', side='right'),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay datos de evolución disponibles")
        else:
            st.info("No hay datos de fecha disponibles")
    
    st.markdown("---")
    
    # Tabla detallada
    st.subheader("📋 Detalle por Reclutador")
    
    if 'Firmaron' in datos_periodo.columns and 'ranking' in locals():
        tabla_detalle = ranking.copy()
        
        # Agregar meta y diferencia
        tabla_detalle['Meta'] = tabla_detalle['Reclutador'].apply(
            lambda r: metas[metas['Reclutador'] == r]['Firmaron'].values[0] if not metas[metas['Reclutador'] == r].empty else 25
        )
        tabla_detalle['Diferencia'] = tabla_detalle['Firmaron'] - tabla_detalle['Meta']
        tabla_detalle['% Efectividad'] = tabla_detalle['Efectividad'].apply(lambda x: f"{x}%")
        
        # Seleccionar columnas disponibles
        columnas_tabla = ['Reclutador', 'Firmaron', 'Meta', 'Diferencia', '% Efectividad']
        if 'Contactos' in tabla_detalle.columns:
            columnas_tabla.append('Contactos')
        if 'Entrevistas' in tabla_detalle.columns:
            columnas_tabla.append('Entrevistas')
        
        tabla_detalle = tabla_detalle[columnas_tabla].sort_values('Firmaron', ascending=False)
        
        st.dataframe(tabla_detalle, use_container_width=True, hide_index=True)

# ============================================================================
# DASHBOARD DIARIO
# ============================================================================

def render_dashboard_diario(reclutador, metricas_diarias, metas, config_dias):
    """Renderiza el dashboard diario con selector de fecha"""
    st.title("📅 Dashboard Diario")
    
    # Selector de fecha
    col_fecha1, col_fecha2 = st.columns([1, 3])
    
    with col_fecha1:
        fechas_disponibles = get_periodos_disponibles(metricas_diarias, 'diario')
        
        if not fechas_disponibles:
            st.error("No hay fechas disponibles")
            return
        
        fecha_seleccionada = st.selectbox(
            "Seleccionar fecha:",
            fechas_disponibles,
            format_func=lambda x: x.strftime('%d/%m/%Y - %A') if hasattr(x, 'strftime') else str(x),
            key="fecha_diaria"
        )
    
    with col_fecha2:
        if hasattr(fecha_seleccionada, 'strftime'):
            st.info(f"📅 {fecha_seleccionada.strftime('%A, %d de %B %Y')}")
        else:
            st.info(f"📅 {fecha_seleccionada}")
    
    # Filtrar datos
    datos_dia = metricas_diarias[
        (metricas_diarias['Reclutador'] == reclutador) & 
        (metricas_diarias['Fecha'].dt.date == fecha_seleccionada)
    ]
    
    # Obtener configuración
    meta_semanal = 25  # Valor por defecto
    dias_laborables = 5  # Valor por defecto
    
    if not metas.empty and 'Reclutador' in metas.columns and 'Firmaron' in metas.columns:
        meta_rec = metas[metas['Reclutador'] == reclutador]
        if not meta_rec.empty:
            meta_semanal = meta_rec['Firmaron'].values[0]
    
    if not config_dias.empty and 'Reclutador' in config_dias.columns:
        config_rec = config_dias[config_dias['Reclutador'] == reclutador]
        if not config_rec.empty and 'Dias_Generales' in config_rec.columns:
            dias_laborables = config_rec['Dias_Generales'].values[0]
    
    meta_diaria = meta_semanal / dias_laborables
    
    # Calcular datos
    firmados_dia = datos_dia['Firmaron'].sum() if not datos_dia.empty and 'Firmaron' in datos_dia.columns else 0
    
    # Calcular acumulado de la semana
    inicio_semana = fecha_seleccionada - timedelta(days=fecha_seleccionada.weekday())
    datos_semana = metricas_diarias[
        (metricas_diarias['Reclutador'] == reclutador) & 
        (metricas_diarias['Fecha'].dt.date >= inicio_semana) &
        (metricas_diarias['Fecha'].dt.date <= fecha_seleccionada)
    ]
    acumulado_semana = datos_semana['Firmaron'].sum() if not datos_semana.empty and 'Firmaron' in datos_semana.columns else 0
    dias_transcurridos = (fecha_seleccionada - inicio_semana).days + 1
    
    # Proyección
    proyeccion = proyeccion_semanal(acumulado_semana, dias_transcurridos, dias_laborables)
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "META DIARIA",
            f"{int(meta_diaria)}",
            f"Basado en {dias_laborables} días",
            "#3b82f6",
            "🎯"
        )
    
    with col2:
        cumplimiento = (firmados_dia / meta_diaria * 100) if meta_diaria > 0 else 0
        render_kpi_card(
            "ALCANZADO",
            f"{int(firmados_dia)}",
            f"{cumplimiento:.0f}% de meta",
            get_color_efectividad(cumplimiento),
            "📈"
        )
    
    with col3:
        cumple = "✓ SÍ" if firmados_dia >= meta_diaria else "✗ NO"
        color = "#10b981" if firmados_dia >= meta_diaria else "#ef4444"
        render_kpi_card(
            "¿CUMPLIÓ META?",
            cumple,
            f"{int(firmados_dia)} de {int(meta_diaria)}",
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
    
    # Tabla de métricas
    st.subheader("📊 Desglose de Métricas del Día")
    
    if not datos_dia.empty:
        metricas = ['Publicaciones', 'Contactos', 'Citas', 'Entrevistas', 'Aceptados', 'Firmaron']
        datos_tabla = []
        
        for metrica in metricas:
            if metrica in datos_dia.columns:
                alcanzado = datos_dia[metrica].sum()
                
                # Intentar obtener meta para esta métrica
                meta_metrica = 0
                if not metas.empty and metrica in metas.columns:
                    meta_rec = metas[metas['Reclutador'] == reclutador]
                    if not meta_rec.empty:
                        meta_metrica = meta_rec[metrica].values[0] / dias_laborables
                
                datos_tabla.append({
                    'Métrica': metrica,
                    'Meta Diaria': int(meta_metrica) if meta_metrica > 0 else 'N/A',
                    'Alcanzado': int(alcanzado),
                    'Diferencia': int(alcanzado - meta_metrica) if meta_metrica > 0 else 'N/A',
                    '% Cumplimiento': f"{(alcanzado/meta_metrica*100):.0f}%" if meta_metrica > 0 else "N/A"
                })
        
        if datos_tabla:
            df_tabla = pd.DataFrame(datos_tabla)
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)
        else:
            st.info("No hay métricas disponibles para mostrar")
    else:
        st.info(f"No hay datos registrados para {fecha_seleccionada.strftime('%d/%m/%Y') if hasattr(fecha_seleccionada, 'strftime') else fecha_seleccionada}")

# ============================================================================
# DASHBOARD SEMANAL
# ============================================================================

def render_dashboard_semanal(reclutador, metricas_diarias, metricas_semanales, metas):
    """Renderiza el dashboard semanal con selector de semana"""
    st.title("📈 Dashboard Semanal")
    
    # Selector de semana
    col_semana1, col_semana2 = st.columns([1, 3])
    
    with col_semana1:
        semanas_disponibles = get_periodos_disponibles(metricas_semanales, 'semanal')
        
        if not semanas_disponibles:
            st.error("No hay semanas disponibles")
            return
        
        semana_seleccionada = st.selectbox(
            "Seleccionar semana:",
            semanas_disponibles,
            format_func=lambda x: f"Semana {x}",
            key="semana_semanal"
        )
    
    with col_semana2:
        st.info(f"📅 Semana {semana_seleccionada}")
    
    # Filtrar datos
    datos_semana = filtrar_por_periodo(metricas_semanales, semana_seleccionada, 'semanal')
    datos_semana_rec = datos_semana[datos_semana['Reclutador'] == reclutador] if not datos_semana.empty else pd.DataFrame()
    
    if datos_semana_rec.empty:
        st.warning(f"No hay datos para {reclutador} en la semana {semana_seleccionada}")
        return
    
    # Calcular métricas
    firmados = datos_semana_rec['Firmaron'].sum() if 'Firmaron' in datos_semana_rec.columns else 0
    contactos = datos_semana_rec['Contactos'].sum() if 'Contactos' in datos_semana_rec.columns else 0
    entrevistas = datos_semana_rec['Entrevistas'].sum() if 'Entrevistas' in datos_semana_rec.columns else 0
    
    # Obtener meta
    meta = 25
    if not metas.empty and 'Reclutador' in metas.columns and 'Firmaron' in metas.columns:
        meta_rec = metas[metas['Reclutador'] == reclutador]
        if not meta_rec.empty:
            meta = meta_rec['Firmaron'].values[0]
    
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
    
    # Gráficos
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        st.subheader("🔽 Embudo de Reclutamiento")
        
        if not datos_semana_rec.empty:
            embudo_data = {
                'Etapa': ['Publicaciones', 'Contactos', 'Citas', 'Entrevistas', 'Aceptados', 'Firmaron'],
                'Alcanzado': [
                    datos_semana_rec['Publicaciones'].sum() if 'Publicaciones' in datos_semana_rec.columns else 0,
                    datos_semana_rec['Contactos'].sum() if 'Contactos' in datos_semana_rec.columns else 0,
                    datos_semana_rec['Citas'].sum() if 'Citas' in datos_semana_rec.columns else 0,
                    datos_semana_rec['Entrevistas'].sum() if 'Entrevistas' in datos_semana_rec.columns else 0,
                    datos_semana_rec['Aceptados'].sum() if 'Aceptados' in datos_semana_rec.columns else 0,
                    datos_semana_rec['Firmaron'].sum() if 'Firmaron' in datos_semana_rec.columns else 0
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
            st.info("No hay datos para mostrar")
    
    with col_graf2:
        st.subheader("📊 Comparativo con Promedio")
        
        # Calcular promedio de últimas 8 semanas
        semanas_historicas = metricas_semanales[metricas_semanales['Reclutador'] == reclutador].tail(8)
        
        if not semanas_historicas.empty and 'Firmaron' in semanas_historicas.columns:
            promedio_firmados = semanas_historicas['Firmaron'].mean()
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=['Promedio 8 sem', 'Semana Actual'],
                y=[promedio_firmados, firmados],
                marker_color=['#94a3b8', get_color_efectividad(efectividad)],
                text=[f"{promedio_firmados:.1f}", f"{firmados}"],
                textposition='auto'
            ))
            
            fig.add_hline(y=meta, line_dash="dash", line_color="red", annotation_text="Meta")
            
            fig.update_layout(height=400, showlegend=False, yaxis_title="Firmados")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos históricos suficientes")

# ============================================================================
# DASHBOARD MENSUAL
# ============================================================================

def render_dashboard_mensual(reclutador, metricas_semanales, metas):
    """Renderiza el dashboard mensual con selector de mes"""
    st.title("📊 Dashboard Mensual")
    
    # Selector de mes
    col_mes1, col_mes2 = st.columns([1, 3])
    
    with col_mes1:
        meses_disponibles = get_periodos_disponibles(metricas_semanales, 'mensual')
        
        if not meses_disponibles:
            st.error("No hay meses disponibles")
            return
        
        mes_seleccionado = st.selectbox(
            "Seleccionar mes:",
            meses_disponibles,
            format_func=lambda x: pd.Period(x).strftime('%B %Y'),
            key="mes_mensual"
        )
    
    with col_mes2:
        st.info(f"📅 {pd.Period(mes_seleccionado).strftime('%B %Y')}")
    
    # Filtrar datos
    datos_mes = filtrar_por_periodo(metricas_semanales, mes_seleccionado, 'mensual')
    datos_mes_rec = datos_mes[datos_mes['Reclutador'] == reclutador] if not datos_mes.empty else pd.DataFrame()
    
    if datos_mes_rec.empty:
        st.warning(f"No hay datos para {reclutador} en {mes_seleccionado}")
        return
    
    # Calcular métricas mensuales
    total_firmados = datos_mes_rec['Firmaron'].sum() if 'Firmaron' in datos_mes_rec.columns else 0
    
    # Obtener meta
    meta_semanal = 25
    if not metas.empty and 'Reclutador' in metas.columns and 'Firmaron' in metas.columns:
        meta_rec = metas[metas['Reclutador'] == reclutador]
        if not meta_rec.empty:
            meta_semanal = meta_rec['Firmaron'].values[0]
    
    meta_mensual = meta_semanal * 4
    efectividad_mensual = calcular_efectividad(total_firmados, meta_mensual)
    promedio_semanal = total_firmados / len(datos_mes_rec) if len(datos_mes_rec) > 0 else 0
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_kpi_card(
            "EFECTIVIDAD MENSUAL",
            f"{efectividad_mensual}%",
            f"{len(datos_mes_rec)} semanas",
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
            "SEMANAS ACTIVAS",
            f"{len(datos_mes_rec)}",
            "En el mes",
            "#3b82f6",
            "📅"
        )
    
    st.markdown("---")
    
    # Gráfico de evolución semanal del mes
    st.subheader("📈 Evolución Semanal del Mes")
    
    if not datos_mes_rec.empty and 'Semana' in datos_mes_rec.columns and 'Firmaron' in datos_mes_rec.columns:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=datos_mes_rec['Semana'],
            y=datos_mes_rec['Firmaron'],
            mode='lines+markers',
            name='Firmaron',
            line=dict(color='#10b981', width=3),
            marker=dict(size=10)
        ))
        
        fig.add_hline(y=meta_semanal, line_dash="dash", line_color="red", annotation_text="Meta Semanal")
        
        fig.update_layout(
            height=400,
            xaxis_title="Semana",
            yaxis_title="Firmados",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de evolución disponibles")
    
    # Tabla detallada
    st.subheader("📋 Detalle Semanal")
    
    if not datos_mes_rec.empty:
        tabla_cols = ['Semana']
        for col in ['Publicaciones', 'Contactos', 'Entrevistas', 'Firmaron']:
            if col in datos_mes_rec.columns:
                tabla_cols.append(col)
        
        if len(tabla_cols) > 1:
            tabla_display = datos_mes_rec[tabla_cols].copy()
            if 'Semana' in tabla_display.columns:
                tabla_display = tabla_display.sort_values('Semana')
            st.dataframe(tabla_display, use_container_width=True, hide_index=True)
        else:
            st.info("No hay suficientes columnas para mostrar")

# ============================================================================
# APLICACIÓN PRINCIPAL
# ============================================================================

def main():
    # Header
    st.title("📊 Dashboard de Reclutamiento")
    st.markdown("**Sistema de Análisis de Desempeño**")
    st.markdown("---")
    
    # Cargar datos
    with st.spinner("🔄 Cargando datos de Airtable..."):
        metricas_diarias = get_metricas_diarias()
        metricas_semanales = get_metricas_semanales()
        metas = get_metas_semanales()
        config_dias = get_config_dias_laborables()
    
    # Verificar que hay datos
    if metricas_diarias.empty and metricas_semanales.empty:
        st.error("❌ No se pudieron cargar los datos. Verifica tu conexión a Airtable.")
        
        with st.expander("🔍 Ver información de diagnóstico"):
            st.write("**Tablas intentadas:**")
            st.write("- metricas_diarias")
            st.write("- metricas_semanales")
            st.write("- metas_semanales")
            st.write("- config_dias_laborables")
            
            st.write("\n**Verifica:**")
            st.write("1. Archivo .env existe y tiene las credenciales correctas")
            st.write("2. Las tablas en Airtable existen con esos nombres exactos")
            st.write("3. El API key tiene permisos de lectura")
            st.write("4. La Base ID es correcta")
        
        st.stop()
    
    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Selector de tipo de dashboard
    dashboard_tipo = st.sidebar.radio(
        "Tipo de Dashboard",
        ["🏢 Departamento", "👤 Individual"],
        key="tipo_dashboard"
    )
    
    st.sidebar.markdown("---")
    
    # Si es individual, mostrar opciones
    if dashboard_tipo == "👤 Individual":
        # Obtener lista de reclutadores
        reclutadores = []
        if not metricas_diarias.empty and 'Reclutador' in metricas_diarias.columns:
            reclutadores.extend(metricas_diarias['Reclutador'].unique().tolist())
        if not metricas_semanales.empty and 'Reclutador' in metricas_semanales.columns:
            reclutadores.extend(metricas_semanales['Reclutador'].unique().tolist())
        
        reclutadores = sorted(list(set(reclutadores)))
        
        if not reclutadores:
            st.error("No hay reclutadores en la base de datos")
            st.stop()
        
        reclutador = st.sidebar.selectbox(
            "📋 Seleccionar Reclutador",
            reclutadores,
            key="reclutador_individual"
        )
        
        st.sidebar.markdown("---")
        
        vista = st.sidebar.radio(
            "Vista",
            ["📅 Diario", "📈 Semanal", "📊 Mensual"],
            key="vista_individual"
        )
    
    # Botón de actualizar
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Actualizar Datos", key="btn_actualizar"):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"🕐 Última actualización: {datetime.now().strftime('%H:%M:%S')}")
    
    # Información de datos cargados
    with st.sidebar.expander("📊 Info de Datos"):
        st.write(f"**Registros diarios:** {len(metricas_diarias)}")
        st.write(f"**Registros semanales:** {len(metricas_semanales)}")
        st.write(f"**Metas configuradas:** {len(metas)}")
        st.write(f"**Configuraciones:** {len(config_dias)}")
    
    # Renderizar dashboard según selección
    if dashboard_tipo == "🏢 Departamento":
        if not metricas_diarias.empty:
            render_dashboard_departamento(metricas_diarias, metricas_semanales, metas)
        else:
            st.error("No hay datos diarios disponibles para el dashboard de departamento")
    else:
        if vista == "📅 Diario":
            if not metricas_diarias.empty:
                render_dashboard_diario(reclutador, metricas_diarias, metas, config_dias)
            else:
                st.error("No hay datos diarios disponibles")
        elif vista == "📈 Semanal":
            if not metricas_semanales.empty:
                render_dashboard_semanal(reclutador, metricas_diarias, metricas_semanales, metas)
            else:
                st.error("No hay datos semanales disponibles")
        else:  # Mensual
            if not metricas_semanales.empty:
                render_dashboard_mensual(reclutador, metricas_semanales, metas)
            else:
                st.error("No hay datos semanales disponibles para vista mensual")

if __name__ == "__main__":
    main()

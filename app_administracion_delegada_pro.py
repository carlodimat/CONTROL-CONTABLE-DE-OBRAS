import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import datetime

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Dashboard Procodima - Control de Obra",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# 2. SISTEMA DE DISEÑO - CSS MODO CLARO PREMIUM (Glassmorphism & Estilos Corporativos)
st.markdown("""
    <style>
    /* Importar fuente Inter */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
        color: #1f2937; /* Gris muy oscuro */
    }

    /* Fondo general */
    .stApp {
        background-color: #f8fafc; /* Slate muy claro */
    }

    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Estilo de la Barra Lateral */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
        box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }

    /* Estilos Premium para las Tarjetas de Métricas (Glassmorphism) */
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }

    /* Etiquetas de Métricas */
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        color: #64748b !important; /* Gris azulado */
        letter-spacing: 0.05em;
    }

    /* Valores de Métricas */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 900 !important;
        color: #0f172a !important; /* Azul muy oscuro */
    }

    /* Deltas (Variaciones) */
    [data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
    }

    /* Header y Subheader Personalizados */
    .premium-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 40px 30px;
        border-radius: 20px;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.4);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .premium-title {
        font-size: 2.5rem;
        font-weight: 900;
        margin: 0;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }
    
    .premium-subtitle {
        font-size: 1.1rem;
        font-weight: 400;
        opacity: 0.9;
        margin-top: 5px;
    }

    /* Estilizar Expander / Acordeón */
    .streamlit-expanderHeader {
        background-color: #ffffff;
        border-radius: 10px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
    }

    /* Dataframes Premium */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    /* Botones primarios */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
    }

    </style>
""", unsafe_allow_html=True)

# 3. GESTIÓN DE ESTADO (Inicialización)
if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro = None
if 'empresa_nombre' not in st.session_state:
    st.session_state.empresa_nombre = "EMPRESA C.A."
if 'obra_nombre' not in st.session_state:
    st.session_state.obra_nombre = "NOMBRE DE LA OBRA"
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

# Funciones de Soporte
def procesar_csv(df):
    """Procesa el CSV cargado, asegura tipos de datos correctos y crea columnas calculadas faltantes"""
    try:
        # Asegurar columnas numéricas
        cols_numericas = ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA']
        for col in cols_numericas:
            if col not in df.columns:
                df[col] = 0.0 # Crear columna si no existe
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # Recalcular Honorarios y Costo Total si estaban en 0 o vacíos pero hay % Admin (Lógica original del HTML)
        mask_admin = df['% ADMIN'] > 0
        df.loc[mask_admin, 'HONORARIOS'] = df.loc[mask_admin, 'MONTO BASE USD'] * (df.loc[mask_admin, '% ADMIN'] / 100.0)
        df['COSTO TOTAL'] = df['MONTO BASE USD'] + df['HONORARIOS']
        
        # Parsear fechas
        if 'FECHA' in df.columns:
            df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')
        
        # Limpiar strings
        cols_str = ['CLASE', 'PROVEEDOR', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'DESCRIPCION', 'MONEDA', 'FORMA PAGO', 'ESTADO']
        for col in cols_str:
            if col not in df.columns:
                df[col] = ''
            df[col] = df[col].astype(str).str.strip().str.upper()
            df.loc[df[col] == 'NAN', col] = ''
                
        return df
    except Exception as e:
        st.error(f"Error procesando los datos: {e}")
        return None

# PANTALLA DE LOGIN Y AUDITORÍA
if st.session_state.usuario_actual is None:
    st.markdown("""
        <div style='text-align: center; margin-top: 100px;'>
            <h1 style='color: #1e3a8a; font-weight: 900; font-size: 3rem;'>Control de Obra</h1>
            <p style='color: #64748b; font-size: 1.2rem; margin-bottom: 20px;'>Acceso al Sistema de Administración Delegada</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<div style='background: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>", unsafe_allow_html=True)
        usuario_input = st.text_input("👤 Nombre del Auditor / Usuario", placeholder="Ej: Arq. Carlos Dimatteo")
        if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
            if usuario_input.strip() != "":
                st.session_state.usuario_actual = usuario_input.strip().upper()
                st.rerun()
            else:
                st.error("Por favor, ingrese su nombre para propósitos de auditoría.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# 4. PANTALLA DE CARGA (Si no hay datos)
if st.session_state.df_maestro is None:
    st.markdown(f"""
        <div style='text-align: center; margin-top: 50px;'>
            <h2 style='color: #1e3a8a; font-weight: 800;'>Bienvenido, {st.session_state.usuario_actual}</h2>
            <p style='color: #64748b; font-size: 1.1rem; margin-bottom: 40px;'>Carga tu archivo CSV maestro para iniciar el panel interactivo.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        archivo_cargado = st.file_uploader("📂 Arrastra tu archivo CSV aquí", type=['csv'])
        
        if archivo_cargado is not None:
            df = pd.read_csv(archivo_cargado)
            df_procesado = procesar_csv(df)
            
            if df_procesado is not None:
                st.session_state.df_maestro = df_procesado
                
                # Intentar auto-detectar Obra y Empresa si existen columnas
                if 'OBRA' in df_procesado.columns:
                    st.session_state.obra_nombre = df_procesado['OBRA'].dropna().iloc[0]
                if 'EMPRESA' in df_procesado.columns:
                    st.session_state.empresa_nombre = df_procesado['EMPRESA'].dropna().iloc[0]
                
                st.success("✅ Base de datos cargada correctamente.")
                st.rerun()
                
        st.divider()
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>O puedes comenzar con una base de datos en blanco</p>", unsafe_allow_html=True)
        if st.button("📄 Iniciar Base de Datos Vacía", use_container_width=True):
            # Crear estructura vacía
            columnas_base = ["CLASE","FECHA","PROVEEDOR","TIPO","CAPITULO","SUBCAPITULO","DESCRIPCION","MONEDA","TASA","MONTO ORIG","MONTO BASE USD","MONTO PAGADO","HONORARIOS","COSTO TOTAL","FORMA PAGO","LINK FACTURA","LINK COMPROBANTE","ESTADO", "% ADMIN"]
            st.session_state.df_maestro = pd.DataFrame(columns=columnas_base)
            st.rerun()

    st.stop() # Detener ejecución si no hay datos

# --- FIN FASE 1: A PARTIR DE AQUÍ EL ESTADO df_maestro EXISTE ---

df_app = st.session_state.df_maestro

# ENCABEZADO PREMIUM
st.markdown(f"""
    <div class="premium-header">
        <div>
            <p class="premium-title">{st.session_state.empresa_nombre}</p>
            <p class="premium-subtitle"><i class="fa-solid fa-building"></i> Proyecto: <b>{st.session_state.obra_nombre}</b></p>
        </div>
        <div style="text-align: right;">
            <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: 600; display: block; margin-bottom: 5px;">
                👤 Auditor: {st.session_state.usuario_actual}
            </span>
            <span style="background: rgba(255,255,255,0.2); padding: 8px 15px; border-radius: 20px; font-size: 0.9rem; font-weight: 600;">
                {len(df_app)} Registros en Total
            </span>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- FASE 2: MOTOR DE FILTRADO Y KPIS PRINCIPALES ---

# Limpiar DataFrames base
df_gastos_base = df_app[df_app['CLASE'] == 'GASTO'].copy()
df_ingresos = df_app[df_app['CLASE'] == 'INGRESO'].copy()

# --- FASE 5: FORMULARIOS INTERACTIVOS (MODALES) ---

@st.dialog("Añadir Nuevo Registro")
def modal_nuevo_registro(clase_registro):
    st.write(f"Complete los datos para el nuevo **{clase_registro}**")
    
    with st.form("form_nuevo_registro"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fecha_input = st.date_input("Fecha", datetime.date.today())
            prov_input = st.text_input("Proveedor", placeholder="Ej: HOME DEPOT")
            tipo_input = st.selectbox("Tipo", ["MATERIAL", "MANO DE OBRA", "CONTRATO", "EQUIPO", "OTRO"])
            desc_input = st.text_input("Descripción")
            
        with col_f2:
            cap_input = st.text_input("Capítulo", placeholder="Ej: CIMENTACION")
            subcap_input = st.text_input("Subcapítulo", placeholder="Ej: EXCAVACION")
            moneda_input = st.selectbox("Moneda", ["MXN", "USD"])
            monto_orig_input = st.number_input("Monto Original", min_value=0.0, step=100.0)
            
        if clase_registro == 'GASTO':
            pct_admin = st.number_input("% Admin Delegada (Calculado)", value=10.0)
            estado_input = st.selectbox("Estado", ["PAGADO", "PENDIENTE"])
        else:
            pct_admin = 0.0
            estado_input = "PAGADO"
            
        submit_btn = st.form_submit_button("Guardar Registro", type="primary")
        
        if submit_btn:
            # Cálculos
            tasa_cambio = 1.0 if moneda_input == "USD" else 18.0 # Asumimos 18 MXN/USD para simplicidad si no se pide
            monto_base_usd = monto_orig_input / tasa_cambio if moneda_input == "MXN" else monto_orig_input
            honorarios = monto_base_usd * (pct_admin / 100)
            costo_total = monto_base_usd + honorarios
            
            nuevo_registro = {
                'CLASE': clase_registro,
                'FECHA': pd.to_datetime(fecha_input),
                'PROVEEDOR': prov_input.upper(),
                'TIPO': tipo_input.upper(),
                'CAPITULO': cap_input.upper(),
                'SUBCAPITULO': subcap_input.upper(),
                'DESCRIPCION': desc_input.upper(),
                'MONEDA': moneda_input,
                'TASA': tasa_cambio,
                'MONTO ORIG': monto_orig_input,
                'MONTO BASE USD': monto_base_usd,
                'MONTO PAGADO': monto_base_usd if estado_input == 'PAGADO' else 0,
                'HONORARIOS': honorarios,
                'COSTO TOTAL': costo_total,
                'ESTADO': estado_input,
                '% ADMIN': pct_admin
            }
            
            # Añadir al df maestro
            df_nuevo = pd.DataFrame([nuevo_registro])
            st.session_state.df_maestro = pd.concat([st.session_state.df_maestro, df_nuevo], ignore_index=True)
            st.success("✅ Registro guardado con éxito.")
            st.rerun()

# Botones de Acción Global (Sidebar)
st.sidebar.markdown("<br><h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-plus'></i> Acciones Rápidas</h2>", unsafe_allow_html=True)

col_btn1, col_btn2 = st.sidebar.columns(2)
if col_btn1.button("➕ Gasto", use_container_width=True):
    modal_nuevo_registro("GASTO")
if col_btn2.button("➕ Ingreso", use_container_width=True):
    modal_nuevo_registro("INGRESO")

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# Filtros Globales (Continuación Fase 2...)
st.sidebar.markdown("<h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-filter'></i> Filtros Globales</h2>", unsafe_allow_html=True)

# Lógica de meses para filtrar
df_gastos_base['MES_AÑO'] = df_gastos_base['FECHA'].dt.strftime('%m-%Y').fillna('N/A')
meses_disp = ["Todos"] + list(df_gastos_base[df_gastos_base['MES_AÑO'] != 'N/A']['MES_AÑO'].unique())
mes_sel = st.sidebar.selectbox("📅 Período (Mes/Año)", meses_disp)

tipo_sel = st.sidebar.selectbox("📂 Tipo de Gasto", ["Todos"] + sorted(df_gastos_base['TIPO'].dropna().unique().tolist()))
capitulo_sel = st.sidebar.selectbox("🏗️ Capítulo", ["Todos"] + sorted(df_gastos_base['CAPITULO'].dropna().unique().tolist()))

# Filtrar subcapítulos basados en el capítulo seleccionado
subcap_options = ["Todos"]
if capitulo_sel != "Todos":
    subcap_options += sorted(df_gastos_base[df_gastos_base['CAPITULO'] == capitulo_sel]['SUBCAPITULO'].dropna().unique().tolist())
else:
    subcap_options += sorted(df_gastos_base['SUBCAPITULO'].dropna().unique().tolist())
    
subcapitulo_sel = st.sidebar.selectbox("🧱 Sub-Capítulo", subcap_options)
prov_sel = st.sidebar.selectbox("👥 Proveedor", ["Todos"] + sorted(df_gastos_base['PROVEEDOR'].dropna().unique().tolist()))
estado_sel = st.sidebar.selectbox("💳 Estado del Gasto", ["Todos", "PAGADO", "PENDIENTE"])

admin_pct = st.sidebar.number_input("💼 % Admin. Delegada Global", value=10.0, step=0.5)

# Aplicar Filtros a los Gastos
df_gastos = df_gastos_base.copy()
if mes_sel != "Todos":
    df_gastos = df_gastos[df_gastos['MES_AÑO'] == mes_sel]
if tipo_sel != "Todos":
    df_gastos = df_gastos[df_gastos['TIPO'] == tipo_sel]
if capitulo_sel != "Todos":
    df_gastos = df_gastos[df_gastos['CAPITULO'] == capitulo_sel]
if subcapitulo_sel != "Todos":
    df_gastos = df_gastos[df_gastos['SUBCAPITULO'] == subcapitulo_sel]
if prov_sel != "Todos":
    df_gastos = df_gastos[df_gastos['PROVEEDOR'] == prov_sel]
if estado_sel != "Todos":
    df_gastos = df_gastos[df_gastos['ESTADO'] == estado_sel]

# Actualizar el % Admin en el vuelo para cálculos si se cambió en el filtro (Opcional, en la HTML se usaba de la data original o se sobrescribía, aquí respetaremos la original pero permitiremos ver el global simulado)
total_ingresos = df_ingresos['MONTO BASE USD'].sum()
total_gastos_netos = df_gastos['MONTO BASE USD'].sum()

# En la lógica original, los honorarios de los filtros se recalculan o se suman. Sumaremos los del dataframe filtrado.
total_honorarios = df_gastos['HONORARIOS'].sum()

# Sin embargo, si el usuario quiere que el %Admin del filtro sobreescriba, calculamos un simulado:
simulated_honorarios = total_gastos_netos * (admin_pct / 100)
# Usaremos el original del CSV, pero mostraremos ambos o confiaremos en el CSV por integridad de pagos.
# Usaremos el que trajo el CSV (total_honorarios) para evitar descuadres de tesorería.

costo_total_obra = total_gastos_netos + total_honorarios
saldo_caja = total_ingresos - costo_total_obra

# Deuda (Gastos pendientes)
df_deudas = df_gastos[df_gastos['ESTADO'] == 'PENDIENTE']
total_deuda = df_deudas['MONTO BASE USD'].sum() + df_deudas['HONORARIOS'].sum()

# Renderizado de KPIs
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("🟢 TOTAL INGRESOS", f"$ {total_ingresos:,.2f}", delta=f"{len(df_ingresos)} Registros", delta_color="normal")
col2.metric("🔨 GASTOS NETOS", f"$ {total_gastos_netos:,.2f}", delta=f"Filtrado", delta_color="off")
col3.metric("💼 ADMIN DELEGADA", f"$ {total_honorarios:,.2f}", delta=f"Honorarios", delta_color="off")
col4.metric("🔴 COSTO TOTAL", f"$ {costo_total_obra:,.2f}", delta=f"-${total_deuda:,.2f} Deuda", delta_color="inverse")
col5.metric("🏦 SALDO EN CAJA", f"$ {saldo_caja:,.2f}", delta="Disponible", delta_color="normal" if saldo_caja >= 0 else "inverse")

st.markdown("<br>", unsafe_allow_html=True)

# --- FASE 3 Y 4: TABS DE VISUALIZACIÓN ---

tab_graficos, tab_egresos, tab_ingresos, tab_deudas, tab_contratos, tab_presupuestos = st.tabs([
    "📊 GRÁFICOS", "💸 EGRESOS", "💰 INGRESOS", "🔴 DEUDAS", "📄 CONTRATOS", "🎯 PRESUPUESTOS"
])

# Funciones de utilidad para formatos de pandas
def formatear_usd(val):
    return f"${val:,.2f}"

with tab_egresos:
    st.markdown("### 💸 Detalle de Egresos (Gastos Registrados)")
    st.info(f"Mostrando **{len(df_gastos)}** registros según los filtros actuales.")
    
    # Mostrar tabla principal de egresos
    cols_mostrar_gastos = [c for c in ['FECHA', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'PROVEEDOR', 'DESCRIPCION', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO'] if c in df_gastos.columns]
    
    if not df_gastos.empty:
        st.dataframe(
            df_gastos[cols_mostrar_gastos].sort_values('FECHA', ascending=False).style.format({
                'MONTO ORIG': "{:,.2f}",
                '% ADMIN': "{:,.2f}",
                'HONORARIOS': formatear_usd,
                'COSTO TOTAL': formatear_usd,
                'MONTO BASE USD': formatear_usd
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.warning("No hay gastos registrados con los filtros actuales.")

with tab_ingresos:
    st.markdown("### 💰 Control de Ingresos")
    if not df_ingresos.empty:
        cols_mostrar_ing = [c for c in ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'FORMA PAGO', 'MONTO ORIG', 'TASA', 'MONTO BASE USD'] if c in df_ingresos.columns]
        st.dataframe(
            df_ingresos[cols_mostrar_ing].sort_values('FECHA', ascending=False).style.format({
                'MONTO ORIG': "{:,.2f}",
                'TASA': "{:,.2f}",
                'MONTO BASE USD': formatear_usd
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.warning("No hay ingresos registrados en la base de datos.")

with tab_deudas:
    st.markdown("### 🔴 Cuentas por Pagar (Gastos Pendientes)")
    if not df_deudas.empty:
        cols_mostrar_deudas = [c for c in ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'COSTO TOTAL', 'MONTO PAGADO'] if c in df_deudas.columns]
        df_deudas_view = df_deudas[cols_mostrar_deudas].copy()
        
        # Calcular Saldo Pendiente
        if 'COSTO TOTAL' in df_deudas_view.columns and 'MONTO PAGADO' in df_deudas_view.columns:
            df_deudas_view['SALDO PENDIENTE'] = df_deudas_view['COSTO TOTAL'] - df_deudas_view['MONTO PAGADO']
        
        st.dataframe(
            df_deudas_view.sort_values('FECHA', ascending=False).style.format({
                'COSTO TOTAL': formatear_usd,
                'MONTO PAGADO': formatear_usd,
                'SALDO PENDIENTE': formatear_usd
            }),
            use_container_width=True,
            height=400
        )
    else:
        st.success("🎉 ¡No hay deudas pendientes registradas!")

with tab_contratos:
    st.markdown("### 📄 Control de Contratos (Subcontratistas)")
    # En la app HTML, los contratos son un tipo o categoría, o están en una tabla separada. 
    # Como todo viene de un solo CSV, filtraremos por TIPO == 'CONTRATO' o 'CONTRATISTA' si existe, o agruparemos.
    # Simulamos el control de contratos sumando los gastos agrupados por proveedor si son del tipo contratista.
    df_contratos = df_gastos_base[df_gastos_base['TIPO'].isin(['CONTRATO', 'CONTRATISTA'])]
    
    if not df_contratos.empty:
        # Agrupar por proveedor
        contratos_grouped = df_contratos.groupby('PROVEEDOR').agg({
            'COSTO TOTAL': 'sum',
            'MONTO PAGADO': 'sum'
        }).reset_index()
        contratos_grouped['SALDO CONTRATO'] = contratos_grouped['COSTO TOTAL'] - contratos_grouped['MONTO PAGADO']
        
        st.dataframe(
            contratos_grouped.style.format({
                'COSTO TOTAL': formatear_usd,
                'MONTO PAGADO': formatear_usd,
                'SALDO CONTRATO': formatear_usd
            }),
            use_container_width=True
        )
    else:
        st.info("No se encontraron registros de tipo CONTRATO o CONTRATISTA en la base de datos.")

with tab_presupuestos:
    st.markdown("### 🎯 Presupuestos Estimados por Capítulo")
    # Para los presupuestos, agruparemos los gastos por CAPITULO y mostraremos el ejecutado.
    # En el futuro se puede añadir una tabla separada de presupuestos reales en session_state.
    presupuestos_grouped = df_gastos_base.groupby(['CAPITULO']).agg({
        'COSTO TOTAL': 'sum'
    }).reset_index().rename(columns={'COSTO TOTAL': 'MONTO EJECUTADO'})
    
    st.dataframe(
        presupuestos_grouped.style.format({
            'MONTO EJECUTADO': formatear_usd
        }),
        use_container_width=True
    )

with tab_graficos:
    st.markdown("### 📊 Panel de Análisis Financiero")
    
    if not df_gastos.empty:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gráfico de Distribución por Capítulo (Donut)
            graf_cap = df_gastos.groupby('CAPITULO')['COSTO TOTAL'].sum().reset_index()
            fig_cap = px.pie(graf_cap, values='COSTO TOTAL', names='CAPITULO', hole=0.4, 
                             title="Distribución por Capítulo",
                             color_discrete_sequence=px.colors.sequential.Teal)
            fig_cap.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_cap, use_container_width=True)
            
            # Gráfico Top Proveedores (Barras Horizontales)
            graf_prov = df_gastos.groupby('PROVEEDOR')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=True).tail(10)
            fig_prov = px.bar(graf_prov, x='COSTO TOTAL', y='PROVEEDOR', orientation='h',
                              title="Top 10 Proveedores (Costo Total)",
                              color='COSTO TOTAL', color_continuous_scale='Blues')
            fig_prov.update_layout(margin=dict(t=40, b=0, l=0, r=0), coloraxis_showscale=False)
            st.plotly_chart(fig_prov, use_container_width=True)

        with col_g2:
            # Gráfico de Evolución Mensual
            graf_mes = df_gastos.groupby('MES_AÑO')['COSTO TOTAL'].sum().reset_index()
            # Ordenar por fecha real si es posible, por ahora confiamos en el string o lo ordenamos básico
            fig_mes = px.bar(graf_mes, x='MES_AÑO', y='COSTO TOTAL', 
                             title="Evolución de Gastos por Período",
                             color_discrete_sequence=['#3b82f6'])
            fig_mes.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_mes, use_container_width=True)
            
            # Gráfico por Tipo de Gasto
            graf_tipo = df_gastos.groupby('TIPO')['COSTO TOTAL'].sum().reset_index()
            fig_tipo = px.pie(graf_tipo, values='COSTO TOTAL', names='TIPO', hole=0.4, 
                             title="Distribución por Tipo",
                             color_discrete_sequence=px.colors.sequential.Plotly3)
            fig_tipo.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_tipo, use_container_width=True)

    else:
        st.warning("No hay datos suficientes para generar gráficos.")

# --- FASE 6: EXPORTADORES Y GUARDADO ---
st.sidebar.markdown("<br><h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-download'></i> Exportar Datos</h2>", unsafe_allow_html=True)

# Preparar CSV para descarga
csv_data = df_app.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="💾 Descargar CSV Maestro",
    data=csv_data,
    file_name=f"MAESTRO_{st.session_state.obra_nombre}_{datetime.date.today().strftime('%Y%m%d')}.csv",
    mime='text/csv',
    use_container_width=True
)

st.sidebar.markdown("<br><p style='text-size:0.8rem; color:gray;'>App Profesional desarrollada por Procodima AI.</p>", unsafe_allow_html=True)


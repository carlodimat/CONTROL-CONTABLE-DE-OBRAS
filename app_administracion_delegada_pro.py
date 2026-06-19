import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import datetime
import urllib.request
import json

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

    html, body, input, select, textarea, button {
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

    /* CONTRASTE Y VISIBILIDAD DE MENÚS Y POPOVERS (Tres puntitos de las columnas y selectores) */
    [role="menu"], [role="menuitem"], [role="option"], [data-testid*="Menu"], [data-testid*="popover"], [data-testid="stDataFrameColumnMenu"], .glide-grid-portal, [class*="glide-grid"], [class*="portal"], [class*="popover"], [class*="Popup"], [class*="Menu"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
    }
    [role="menuitem"] *, [role="option"] *, [data-testid="stDataFrameColumnMenu"] *, .glide-grid-portal *, [class*="glide-grid"] *, [class*="stDataFrameColumnMenu"] * {
        color: #0f172a !important;
    }
    [role="menuitem"]:hover, [role="menuitem"]:hover *, [role="option"]:hover, [role="option"]:hover *, [class*="menu-item"]:hover, [class*="MenuItem"]:hover {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
    }

    </style>
""", unsafe_allow_html=True)

import os

# 3. GESTIÓN DE ESTADO (Inicialización)
if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro = None
if 'empresa_nombre' not in st.session_state:
    st.session_state.empresa_nombre = "EMPRESA C.A."
if 'obra_nombre' not in st.session_state:
    st.session_state.obra_nombre = "NOMBRE DE LA OBRA"
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None
if 'reset_counter_gastos' not in st.session_state:
    st.session_state.reset_counter_gastos = 0
if 'reset_counter_ingresos' not in st.session_state:
    st.session_state.reset_counter_ingresos = 0
if 'reset_counter_contratos' not in st.session_state:
    st.session_state.reset_counter_contratos = 0

# Columnas por defecto para inicialización
cols_def_gastos = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'LINK FACTURA', 'LINK COMPROBANTE']
cols_def_ingresos = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', 'MONTO BASE USD', 'FORMA PAGO', 'LINK COMPROBANTE']

if 'columnas_visibles_gastos' not in st.session_state:
    st.session_state.columnas_visibles_gastos = cols_def_gastos.copy()
if 'columnas_visibles_ingresos' not in st.session_state:
    st.session_state.columnas_visibles_ingresos = cols_def_ingresos.copy()

# Rutas de Caché Local
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_META_PATH = os.path.join(CACHE_DIR, ".session_metadata.json")
CACHE_DB_PATH = os.path.join(CACHE_DIR, ".session_database.csv")

def guardar_cache_local():
    try:
        meta = {
            "usuario_actual": st.session_state.get("usuario_actual"),
            "empresa_nombre": st.session_state.get("empresa_nombre"),
            "obra_nombre": st.session_state.get("obra_nombre"),
            "admin_pct_global": st.session_state.get("admin_pct_global", 15.0),
            "columnas_visibles_gastos": st.session_state.get("columnas_visibles_gastos"),
            "columnas_visibles_ingresos": st.session_state.get("columnas_visibles_ingresos")
        }
        with open(CACHE_META_PATH, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
        if st.session_state.df_maestro is not None:
            st.session_state.df_maestro.to_csv(CACHE_DB_PATH, index=False)
    except Exception:
        pass

def cargar_cache_local():
    try:
        if os.path.exists(CACHE_META_PATH) and os.path.exists(CACHE_DB_PATH):
            with open(CACHE_META_PATH, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            st.session_state.usuario_actual = meta.get("usuario_actual")
            st.session_state.empresa_nombre = meta.get("empresa_nombre")
            st.session_state.obra_nombre = meta.get("obra_nombre")
            if "admin_pct_global" in meta:
                st.session_state.admin_pct_global = meta.get("admin_pct_global")
            if "columnas_visibles_gastos" in meta:
                st.session_state.columnas_visibles_gastos = meta.get("columnas_visibles_gastos")
            if "columnas_visibles_ingresos" in meta:
                st.session_state.columnas_visibles_ingresos = meta.get("columnas_visibles_ingresos")
            
            df = pd.read_csv(CACHE_DB_PATH)
            st.session_state.df_maestro = procesar_csv(df)
            return True
    except Exception:
        pass
    return False

def borrar_cache_local():
    try:
        if os.path.exists(CACHE_META_PATH):
            os.remove(CACHE_META_PATH)
        if os.path.exists(CACHE_DB_PATH):
            os.remove(CACHE_DB_PATH)
    except Exception:
        pass

# Funciones de Soporte
def obtener_tasa_bcv():
    """Obtiene la tasa oficial del BCV en tiempo real usando urllib (sin dependencias externas)"""
    try:
        url = "https://ve.dolarapi.com/v1/dolares/oficial"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            return float(data.get('promedio', 1.0))
    except Exception:
        return 1.0

def procesar_csv(df):
    """Procesa el CSV cargado, asegura tipos de datos correctos y crea columnas calculadas faltantes"""
    try:
        # Asegurar todas las columnas necesarias en el CSV maestro
        columnas_base = ["CLASE","FECHA","PROVEEDOR","TIPO","CAPITULO","SUBCAPITULO","DESCRIPCION","MONEDA","TASA","MONTO ORIG","MONTO BASE USD","MONTO PAGADO","HONORARIOS","COSTO TOTAL","FORMA PAGO","LINK FACTURA","LINK COMPROBANTE","ESTADO", "% ADMIN"]
        for col in columnas_base:
            if col not in df.columns:
                df[col] = 0.0 if col in ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA'] else ''

        # Limpiar strings primero
        cols_str = ['CLASE', 'PROVEEDOR', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'DESCRIPCION', 'MONEDA', 'FORMA PAGO', 'ESTADO']
        for col in cols_str:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df.loc[df[col].isin(['NAN', 'NONE', 'NAT', '<NA>']), col] = ''

        # Asegurar columnas numéricas
        cols_numericas = ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA']
        for col in cols_numericas:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Parsear fechas
        if 'FECHA' in df.columns:
            df['FECHA'] = pd.to_datetime(df['FECHA'], errors='coerce')

        # Recalcular columnas derivadas de forma consistente
        is_usd = (df['MONEDA'] == 'USD') | (df['MONEDA'] == '')
        has_tasa = df['TASA'] > 0

        # Calcular MONTO BASE USD
        df.loc[is_usd, 'MONTO BASE USD'] = df.loc[is_usd, 'MONTO ORIG']
        df.loc[~is_usd & has_tasa, 'MONTO BASE USD'] = df.loc[~is_usd & has_tasa, 'MONTO ORIG'] / df.loc[~is_usd & has_tasa, 'TASA']
        df.loc[~is_usd & ~has_tasa, 'MONTO BASE USD'] = df.loc[~is_usd & ~has_tasa, 'MONTO ORIG']

        # Calcular HONORARIOS y COSTO TOTAL para GASTOS
        is_gasto = df['CLASE'] == 'GASTO'
        default_admin = st.session_state.get('admin_pct_global', 15.0)
        pct_admin_temp = df['% ADMIN'].copy()
        mask_cero = is_gasto & ((pct_admin_temp == 0) | (pct_admin_temp.isna()))
        pct_admin_temp.loc[mask_cero] = default_admin

        df.loc[is_gasto, 'HONORARIOS'] = df.loc[is_gasto, 'MONTO BASE USD'] * (pct_admin_temp.loc[is_gasto] / 100.0)
        df.loc[is_gasto, 'COSTO TOTAL'] = df.loc[is_gasto, 'MONTO BASE USD'] + df.loc[is_gasto, 'HONORARIOS']

        # Para INGRESOS
        is_ingreso = df['CLASE'] == 'INGRESO'
        df.loc[is_ingreso, 'HONORARIOS'] = 0.0
        df.loc[is_ingreso, 'COSTO TOTAL'] = df.loc[is_ingreso, 'MONTO BASE USD']

        # MONTO PAGADO según el estado
        is_pagado = df['ESTADO'] == 'PAGADO'
        df.loc[is_pagado, 'MONTO PAGADO'] = df.loc[is_pagado, 'MONTO BASE USD']
        df.loc[~is_pagado, 'MONTO PAGADO'] = 0.0

        return df
    except Exception as e:
        st.error(f"Error procesando los datos: {e}")
        return None

def aplicar_buscador_universal(df, query):
    if not query:
        return df
    # Filtrar filas que contengan el término en cualquier columna
    mask = df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
    return df[mask]

def guardar_cambios_maestro(df_original_filtrado, df_editado_filtrado):
    df_maestro = st.session_state.df_maestro.copy()
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        for col in df_editado_filtrado.columns:
            if col in df_maestro.columns:
                df_maestro.loc[indices_comunes, col] = df_editado_filtrado.loc[indices_comunes, col]
                
    # 3. Identificar filas nuevas añadidas
    indices_nuevos = df_editado_filtrado.index.difference(df_original_filtrado.index)
    if not indices_nuevos.empty:
        df_nuevos = df_editado_filtrado.loc[indices_nuevos].copy()
        
        # En caso de que CLASE venga vacío para nueva fila, por defecto es GASTO
        if 'CLASE' in df_nuevos.columns:
            df_nuevos['CLASE'] = df_nuevos['CLASE'].fillna('').astype(str).str.strip().str.upper()
            df_nuevos.loc[df_nuevos['CLASE'] == '', 'CLASE'] = 'GASTO'
        else:
            df_nuevos['CLASE'] = 'GASTO'
            
        # Rellenar columnas faltantes en el editor con valores por defecto
        for col in df_maestro.columns:
            if col not in df_nuevos.columns:
                df_nuevos[col] = 0.0 if col in ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA'] else ''
        df_maestro = pd.concat([df_maestro, df_nuevos[df_maestro.columns]], ignore_index=True)
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        guardar_cache_local()

def guardar_cambios_filtrados(df_original_filtrado, df_editado_filtrado, clase_default):
    df_maestro = st.session_state.df_maestro.copy()
    global_admin = st.session_state.get('admin_pct_global', 15.0)
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        for col in df_editado_filtrado.columns:
            if col in df_maestro.columns:
                if col == '% ADMIN':
                    # Si el valor editado es igual al global default, guardarlo como 0.0 para mantener la vinculación global
                    for idx in indices_comunes:
                        val = df_editado_filtrado.loc[idx, col]
                        df_maestro.loc[idx, col] = 0.0 if val == global_admin else val
                else:
                    df_maestro.loc[indices_comunes, col] = df_editado_filtrado.loc[indices_comunes, col]
                
    # 3. Identificar filas nuevas añadidas
    indices_nuevos = df_editado_filtrado.index.difference(df_original_filtrado.index)
    if not indices_nuevos.empty:
        df_nuevos = df_editado_filtrado.loc[indices_nuevos].copy()
        df_nuevos['CLASE'] = clase_default
        
        # Si tiene la columna % ADMIN, limpiar los valores que coincidan con el global a 0.0
        if '% ADMIN' in df_nuevos.columns:
            df_nuevos.loc[df_nuevos['% ADMIN'] == global_admin, '% ADMIN'] = 0.0
            
        # Rellenar columnas faltantes en el editor con valores por defecto
        for col in df_maestro.columns:
            if col not in df_nuevos.columns:
                df_nuevos[col] = 0.0 if col in ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA'] else ''
        df_maestro = pd.concat([df_maestro, df_nuevos[df_maestro.columns]], ignore_index=True)
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Procesar y recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        guardar_cache_local()

def agrupar_gastos_divididos(df):
    if df.empty:
        return df
        
    # Crear una copia para no alterar el original
    df_copy = df.copy()
    
    # Limpiar descripción (eliminar sufijo de porcentaje como (15%) o (10%))
    import re
    def limpiar_desc(desc):
        if not isinstance(desc, str):
            return desc
        return re.sub(r' \(\d+(\.\d+)?\%\)$', '', desc).strip().upper()
        
    df_copy['DESCRIPCION_LIMPIA'] = df_copy['DESCRIPCION'].apply(limpiar_desc)
    
    # Asegurar tipo fecha
    if 'FECHA' in df_copy.columns:
        df_copy['FECHA_STR'] = df_copy['FECHA'].dt.strftime('%Y-%m-%d').fillna('')
    else:
        df_copy['FECHA_STR'] = ''
        
    # Agrupar por fecha, proveedor, descripción limpia, tipo, moneda, tasa, estado y forma pago
    group_cols = ['FECHA_STR', 'PROVEEDOR', 'DESCRIPCION_LIMPIA', 'TIPO', 'MONEDA', 'TASA', 'ESTADO', 'FORMA PAGO']
    
    # Rellenar nulos temporalmente para evitar que groupby descarte filas
    for col in group_cols:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].fillna('')
            
    grouped_rows = []
    for keys, group in df_copy.groupby(group_cols, dropna=False):
        fecha_str, proveedor, desc_limpia, tipo, moneda, tasa, estado, forma_pago = keys
        
        total_monto_orig = group['MONTO ORIG'].sum()
        total_monto_base = group['MONTO BASE USD'].sum()
        total_honorarios = group['HONORARIOS'].sum()
        total_costo_total = group['COSTO TOTAL'].sum()
        
        # Determinar capítulo y subcapítulo
        caps = sorted(list(set([str(c).strip().upper() for c in group['CAPITULO'].unique() if str(c).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        subcaps = sorted(list(set([str(s).strip().upper() for s in group['SUBCAPITULO'].unique() if str(s).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE', '-']])))
        
        if len(caps) > 1:
            cap_val = "VARIOS (DIVIDIDO)"
        elif len(caps) == 1:
            if len(group) > 1:
                cap_val = f"{caps[0]} (DIVIDIDO)"
            else:
                cap_val = caps[0]
        else:
            cap_val = ""
            
        if len(subcaps) > 1:
            subcap_val = "VARIOS (DIVIDIDO)"
        elif len(subcaps) == 1:
            subcap_val = subcaps[0]
        else:
            subcap_val = ""
            
        row = {
            'FECHA': pd.to_datetime(fecha_str) if fecha_str else pd.NaT,
            'PROVEEDOR': proveedor,
            'DESCRIPCION': desc_limpia,
            'TIPO': tipo,
            'MONEDA': moneda,
            'TASA': tasa,
            'MONTO ORIG': total_monto_orig,
            'MONTO BASE USD': total_monto_base,
            'HONORARIOS': total_honorarios,
            'COSTO TOTAL': total_costo_total,
            'ESTADO': estado,
            'FORMA PAGO': forma_pago,
            'CAPITULO': cap_val,
            'SUBCAPITULO': subcap_val
        }
        grouped_rows.append(row)
        
    df_grouped = pd.DataFrame(grouped_rows)
    if not df_grouped.empty:
        df_grouped = df_grouped.sort_values('FECHA', ascending=False)
    return df_grouped

# Cargar caché local al inicio si existe y no hay sesión activa
if st.session_state.usuario_actual is None:
    cargar_cache_local()

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
                guardar_cache_local()
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
            df_procesado = procesar_csv(pd.read_csv(archivo_cargado))
            if df_procesado is not None:
                st.session_state.df_maestro = df_procesado
                # Intentar leer los nombres desde el CSV si existen las columnas
                if 'OBRA' in df_procesado.columns:
                    st.session_state.obra_nombre = str(df_procesado['OBRA'].dropna().iloc[0]).upper()
                else:
                    # Autodetectar desde el nombre del archivo si la columna no existe (ej. RANCHO 120626.csv -> RANCHO 120626)
                    st.session_state.obra_nombre = archivo_cargado.name.upper().replace('.CSV', '').replace('.TXT', '')
                    
                if 'EMPRESA' in df_procesado.columns:
                    st.session_state.empresa_nombre = str(df_procesado['EMPRESA'].dropna().iloc[0]).upper()
                
                st.success("✅ Base de datos cargada correctamente.")
                guardar_cache_local()
                st.rerun()
                
        st.divider()
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>O puedes comenzar con una base de datos en blanco</p>", unsafe_allow_html=True)
        if st.button("📄 Iniciar Base de Datos Vacía", use_container_width=True):
            # Crear estructura vacía
            columnas_base = ["CLASE","FECHA","PROVEEDOR","TIPO","CAPITULO","SUBCAPITULO","DESCRIPCION","MONEDA","TASA","MONTO ORIG","MONTO BASE USD","MONTO PAGADO","HONORARIOS","COSTO TOTAL","FORMA PAGO","LINK FACTURA","LINK COMPROBANTE","ESTADO", "% ADMIN"]
            st.session_state.df_maestro = pd.DataFrame(columns=columnas_base)
            guardar_cache_local()
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

# Configuraciones de Proyecto (Sidebar Superior)
st.sidebar.markdown("<h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-gear'></i> Configuración</h2>", unsafe_allow_html=True)
nueva_empresa = st.sidebar.text_input("🏢 Empresa", value=st.session_state.empresa_nombre)
nueva_obra = st.sidebar.text_input("🏗️ Proyecto", value=st.session_state.obra_nombre)
if nueva_empresa != st.session_state.empresa_nombre or nueva_obra != st.session_state.obra_nombre:
    st.session_state.empresa_nombre = nueva_empresa
    st.session_state.obra_nombre = nueva_obra
    guardar_cache_local()
    st.rerun()

# Botón para cerrar sesión y cargar otro archivo
if st.sidebar.button("🔄 Cambiar de Proyecto / Cerrar Sesión", use_container_width=True):
    borrar_cache_local()
    st.session_state.df_maestro = None
    st.session_state.usuario_actual = None
    st.session_state.empresa_nombre = "EMPRESA C.A."
    st.session_state.obra_nombre = "NOMBRE DE LA OBRA"
    st.rerun()

st.sidebar.markdown("<hr>", unsafe_allow_html=True)

# --- FASE 2: MOTOR DE FILTRADO Y KPIS PRINCIPALES ---

# Failsafe: Si la sesión conservó datos viejos sin las columnas, crearlas al vuelo.
cols_calculadas = ['HONORARIOS', 'COSTO TOTAL', '% ADMIN']
for col in cols_calculadas:
    if col not in df_app.columns:
        df_app[col] = 0.0

# Limpiar DataFrames base
df_gastos_base = df_app[df_app['CLASE'] == 'GASTO'].copy()
df_ingresos = df_app[df_app['CLASE'] == 'INGRESO'].copy()

# --- FASE 5: FORMULARIOS INTERACTIVOS (MODALES) ---

@st.dialog("Añadir Nuevo Registro")
def modal_nuevo_registro(clase_registro, admin_global_val):
    st.write(f"Complete los datos para el nuevo **{clase_registro}**")
    
    df_actual = st.session_state.df_maestro
    tasa_bcv = obtener_tasa_bcv()
    
    col1, col2 = st.columns(2)
    
    # ---------------------------------------------
    # LOGICA PARA GASTOS
    # ---------------------------------------------
    if clase_registro == "GASTO":
        lista_prov = ["➕ NUEVO PROVEEDOR"] + sorted(list(set([str(p).strip() for p in df_actual['PROVEEDOR'].unique() if str(p).strip() not in ['', 'NAN', 'NaN']])))
        lista_cap = ["➕ NUEVO CAPÍTULO"] + sorted(list(set([str(c).strip() for c in df_actual['CAPITULO'].unique() if str(c).strip() not in ['', 'NAN', 'NaN']])))
        lista_sub = ["➕ NUEVO SUB-CAPÍTULO"] + sorted(list(set([str(s).strip() for s in df_actual['SUBCAPITULO'].unique() if str(s).strip() not in ['', 'NAN', 'NaN']])))
        lista_tipo = ["➕ NUEVO TIPO"] + sorted(list(set([str(t).strip() for t in df_actual['TIPO'].unique() if str(t).strip() not in ['', 'NAN', 'NaN']])))
        
        with col1:
            fecha_input = st.date_input("📅 Fecha")
            tipo_sel = st.selectbox("🏷️ Tipo de Gasto", options=lista_tipo)
            tipo = st.text_input("✍️ Escriba el Nuevo Tipo") if tipo_sel == "➕ NUEVO TIPO" else tipo_sel
            descripcion = st.text_area("📝 Descripción")
            moneda = st.selectbox("💵 Moneda", ["USD", "VES", "EUR"])
            monto = st.number_input("💰 Monto Original", min_value=0.0, step=10.0)
            
        with col2:
            prov_sel = st.selectbox("🏢 Proveedor", options=lista_prov)
            proveedor = st.text_input("✍️ Escriba el Nuevo Proveedor") if prov_sel == "➕ NUEVO PROVEEDOR" else prov_sel
            cap_sel = st.selectbox("🏗️ Capítulo", options=lista_cap)
            capitulo = st.text_input("✍️ Escriba el Nuevo Capítulo") if cap_sel == "➕ NUEVO CAPÍTULO" else cap_sel
            sub_sel = st.selectbox("🧱 Sub-Capítulo", options=lista_sub)
            subcapitulo = st.text_input("✍️ Escriba el Nuevo Sub-Capítulo") if sub_sel == "➕ NUEVO SUB-CAPÍTULO" else sub_sel
            
            tasa = st.number_input("📈 Tasa de Cambio (Ref. BCV)", value=tasa_bcv, min_value=0.0, format="%.4f")
            estado = st.selectbox("✅ Estado", ["PAGADO", "PENDIENTE"])
            forma_pago = st.selectbox("💳 Forma de Pago", ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"])
            admin_pct = st.number_input("💼 % Administración Delegada", value=float(admin_global_val), step=0.5)

    # ---------------------------------------------
    # LOGICA PARA INGRESOS
    # ---------------------------------------------
    else:
        lista_pagadores = ["➕ NUEVO PAGADOR"] + sorted(list(set([str(p).strip() for p in df_actual['PROVEEDOR'].unique() if str(p).strip() not in ['', 'NAN', 'NaN']])))
        
        with col1:
            fecha_input = st.date_input("📅 Fecha")
            pagador_sel = st.selectbox("👤 Pagador / Cliente", options=lista_pagadores)
            proveedor = st.text_input("✍️ Escriba el Nuevo Pagador") if pagador_sel == "➕ NUEVO PAGADOR" else pagador_sel
            descripcion = st.text_area("📝 Descripción del Ingreso")
            
        with col2:
            moneda = st.selectbox("💵 Moneda", ["USD", "VES", "EUR"])
            monto = st.number_input("💰 Monto del Ingreso", min_value=0.0, step=100.0)
            tasa = st.number_input("📈 Tasa de Cambio (Ref. BCV)", value=tasa_bcv, min_value=0.0, format="%.4f")
            forma_pago = st.selectbox("💳 Forma de Pago", ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"])
            
        # Forzar variables obligatorias para el esquema del CSV (sin calcular admin)
        tipo = "INGRESO"
        capitulo = "N/A"
        subcapitulo = "N/A"
        estado = "PAGADO"
        admin_pct = 0.0
        
    st.markdown("---")
    # Cálculos dinámicos en vivo para visualización
    monto_base_usd_calc = monto / tasa if moneda != "USD" and tasa > 0 else monto
    honorarios_calc = monto_base_usd_calc * (admin_pct / 100) if clase_registro == "GASTO" else 0.0
    costo_total_calc = monto_base_usd_calc + honorarios_calc
    
    if clase_registro == "GASTO":
        st.info(f"🧮 **Cálculo de Gasto:** Monto Base `💲{monto_base_usd_calc:,.2f} USD` + Honorarios `💲{honorarios_calc:,.2f} USD` = **COSTO TOTAL `💲{costo_total_calc:,.2f} USD`**")
    else:
        st.success(f"🧮 **Cálculo de Ingreso:** Este ingreso equivale a **💲 {monto_base_usd_calc:,.2f} USD** a la tasa actual.")
            
    submit_btn = st.button("Guardar Registro", type="primary", use_container_width=True)
    
    if submit_btn:
        # Usar los cálculos dinámicos ya hechos
        monto_base_usd = monto_base_usd_calc
        honorarios = honorarios_calc
        costo_total = costo_total_calc
        
        nuevo_registro = {
            'CLASE': clase_registro,
            'FECHA': pd.to_datetime(fecha_input),
            'PROVEEDOR': proveedor.upper(),
            'TIPO': tipo.upper(),
            'CAPITULO': capitulo.upper(),
            'SUBCAPITULO': subcapitulo.upper(),
            'DESCRIPCION': descripcion.upper(),
            'MONEDA': moneda,
            'TASA': tasa,
            'MONTO ORIG': monto,
            'MONTO BASE USD': monto_base_usd,
            'MONTO PAGADO': monto_base_usd if estado == 'PAGADO' else 0,
            'HONORARIOS': honorarios,
            'COSTO TOTAL': costo_total,
            'ESTADO': estado,
            '% ADMIN': admin_pct
        }
        
        # Añadir al df maestro de forma segura
        df_nuevo = pd.DataFrame([nuevo_registro])
        st.session_state.df_maestro = pd.concat([df_actual, df_nuevo], ignore_index=True)
        st.success("✅ Registro guardado con éxito.")
        guardar_cache_local()
        st.rerun()

# --- FASE 1: BARRA LATERAL (FILTROS Y ACCIONES) ---
with st.sidebar:
    st.markdown("<h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-bolt'></i> Acciones Rápidas</h2>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("<h3 style='color:#1e3a8a; font-weight:700;'><i class='fa-solid fa-percent'></i> Tasa Administrativa</h3>", unsafe_allow_html=True)
    admin_pct = st.number_input("💼 % Admin. Delegada Global", value=15.0, step=0.5, key="admin_pct_global")
    st.markdown("---")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ Gasto", use_container_width=True):
            modal_nuevo_registro("GASTO", admin_pct)
    with col_btn2:
        if st.button("➕ Ingreso", use_container_width=True):
            modal_nuevo_registro("INGRESO", admin_pct)
            
    st.markdown("---")
    st.markdown("<h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-filter'></i> Filtros Globales</h2>", unsafe_allow_html=True)

# Lógica de meses para filtrar e input de buscador
search_query = st.sidebar.text_input(
    "🔍 Buscador Universal", 
    value="", 
    help="Escribe cualquier dato (proveedor, descripción, capítulo, estado, etc.) para buscar y filtrar en todas las pestañas de edición a la vez."
).strip()

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

# Aplicar buscador universal
if search_query:
    df_gastos = aplicar_buscador_universal(df_gastos, search_query)
    df_ingresos = aplicar_buscador_universal(df_ingresos, search_query)


# Recálculo Dinámico de Administración Delegada
pct_admin_efectivo = df_gastos['% ADMIN'].copy()
mask_cero_gastos = (pct_admin_efectivo == 0) | (pct_admin_efectivo.isna())
pct_admin_efectivo.loc[mask_cero_gastos] = admin_pct

df_gastos['HONORARIOS'] = df_gastos['MONTO BASE USD'] * (pct_admin_efectivo / 100.0)
df_gastos['COSTO TOTAL'] = df_gastos['MONTO BASE USD'] + df_gastos['HONORARIOS']

# Actualizar KPIs
total_ingresos = df_ingresos['MONTO BASE USD'].sum()
total_gastos_netos = df_gastos['MONTO BASE USD'].sum()
total_honorarios = df_gastos['HONORARIOS'].sum()
costo_total_obra = df_gastos['COSTO TOTAL'].sum()
saldo_caja = total_ingresos - costo_total_obra

# Deuda (Gastos pendientes)
df_deudas = df_gastos[df_gastos['ESTADO'] == 'PENDIENTE']
total_deuda = df_deudas['COSTO TOTAL'].sum()

# Resumen de totales filtrados para la barra lateral (visible en tiempo real)
if not df_gastos.empty:
    monto_orig_por_moneda_sb = df_gastos.groupby('MONEDA')['MONTO ORIG'].sum()
    monto_orig_str_sb = " | ".join([f"{val:,.2f} {mon}" for mon, val in monto_orig_por_moneda_sb.items()])
else:
    monto_orig_str_sb = "0.00 USD"

st.sidebar.markdown(f"""
<div style="background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #e2e8f0; margin-top: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <p style="margin: 0; font-size: 0.8rem; color: #64748b; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em;">📊 Resumen Filtrado (Gastos)</p>
    <hr style="margin: 8px 0; border-color: #f1f5f9;">
    <p style="margin: 3px 0; font-size: 0.9rem; color: #0f172a;"><b>Monto Original:</b> {monto_orig_str_sb}</p>
    <p style="margin: 3px 0; font-size: 0.9rem; color: #0f172a;"><b>Honorarios:</b> ${total_honorarios:,.2f} USD</p>
    <p style="margin: 3px 0; font-size: 0.9rem; color: #0f172a;"><b>Costo Total:</b> ${costo_total_obra:,.2f} USD</p>
</div>
""", unsafe_allow_html=True)

# Renderizado de KPIs
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("🟢 TOTAL INGRESOS", f"$ {total_ingresos:,.2f}", delta=f"{len(df_ingresos)} Registros", delta_color="normal")
col2.metric("🔨 GASTOS NETOS", f"$ {total_gastos_netos:,.2f}", delta=f"Filtrado", delta_color="off")
col3.metric("💼 ADMIN DELEGADA", f"$ {total_honorarios:,.2f}", delta=f"Honorarios", delta_color="off")
col4.metric("🔴 COSTO TOTAL", f"$ {costo_total_obra:,.2f}", delta=f"-${total_deuda:,.2f} Deuda", delta_color="inverse")
col5.metric("🏦 SALDO EN CAJA", f"$ {saldo_caja:,.2f}", delta="Disponible", delta_color="normal" if saldo_caja >= 0 else "inverse")

st.markdown("<br>", unsafe_allow_html=True)

# --- FASE 3 Y 4: TABS DE VISUALIZACIÓN ---

tab_graficos, tab_egresos, tab_ingresos, tab_deudas, tab_contratos, tab_presupuestos, tab_editor = st.tabs([
    "📊 GRÁFICOS", "💸 EGRESOS", "💰 INGRESOS", "🔴 DEUDAS", "📄 CONTRATOS", "🎯 PRESUPUESTOS", "🛠️ EDITOR MAESTRO"
])

# Funciones de utilidad para formatos de pandas
def formatear_usd(val):
    return f"${val:,.2f}"

with tab_egresos:
    st.markdown("### 💸 Detalle de Egresos (Gastos Registrados)")
    
    cols_mostrar_gastos = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'LINK FACTURA', 'LINK COMPROBANTE']
    
    df_gastos_sort = df_gastos.sort_values('FECHA', ascending=False) if not df_gastos.empty else pd.DataFrame(columns=cols_mostrar_gastos)
    if not df_gastos_sort.empty:
        mask_cero_g = (df_gastos_sort['% ADMIN'] == 0) | (df_gastos_sort['% ADMIN'].isna())
        df_gastos_sort.loc[mask_cero_g, '% ADMIN'] = admin_pct
        # Recalcular honorarios y costo total sobre df_gastos_sort
        df_gastos_sort['HONORARIOS'] = df_gastos_sort['MONTO BASE USD'] * (df_gastos_sort['% ADMIN'] / 100.0)
        df_gastos_sort['COSTO TOTAL'] = df_gastos_sort['MONTO BASE USD'] + df_gastos_sort['HONORARIOS']

    # Métricas de Sumas de Egresos
    sum_orig_eg = df_gastos_sort['MONTO ORIG'].sum() if not df_gastos_sort.empty else 0.0
    sum_hon_eg = df_gastos_sort['HONORARIOS'].sum() if not df_gastos_sort.empty else 0.0
    sum_tot_eg = df_gastos_sort['COSTO TOTAL'].sum() if not df_gastos_sort.empty else 0.0

    # Agrupar Monto Original por moneda para mostrar en el tooltip/help
    if not df_gastos_sort.empty:
        monto_orig_por_moneda_eg = df_gastos_sort.groupby('MONEDA')['MONTO ORIG'].sum()
        monto_orig_str_eg = " | ".join([f"{val:,.2f} {mon}" for mon, val in monto_orig_por_moneda_eg.items()])
    else:
        monto_orig_str_eg = "0.00 USD"

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric(
        "💰 SUMA MONTO ORIGINAL", 
        f"{sum_orig_eg:,.2f}" if df_gastos_sort.empty or df_gastos_sort['MONEDA'].nunique() <= 1 else "Varios (ver ayuda)", 
        help=f"Detalle por Moneda: {monto_orig_str_eg}\nNota: Si hay monedas mezcladas, la suma directa no es representativa en una sola moneda. Use el Costo Total (USD) como referencia unificada."
    )
    col_m2.metric("💼 SUMA HONORARIOS", f"$ {sum_hon_eg:,.2f}")
    col_m3.metric("🔴 SUMA COSTO TOTAL", f"$ {sum_tot_eg:,.2f}")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Agregar Toggle para agrupar/consolidar gastos divididos
    col_eg_opt1, col_eg_opt2 = st.columns([2, 1])
    with col_eg_opt1:
        st.info(f"Mostrando **{len(df_gastos)}** registros según los filtros actuales.")
    with col_eg_opt2:
        agrupar_gastos = st.checkbox("🔍 Agrupar Gastos Divididos", value=False, help="Consolida los gastos parciales/divididos (que tienen la misma fecha, proveedor, descripción y tipo) en una sola fila para ver el gasto total completo. Oculta la subdivisión por capítulos.")

    # Limpieza de columnas visibles de gastos por seguridad
    cols_validas_gastos = [col for col in st.session_state.columnas_visibles_gastos if col in cols_mostrar_gastos]
    if not cols_validas_gastos:
        cols_validas_gastos = cols_mostrar_gastos.copy()
        st.session_state.columnas_visibles_gastos = cols_validas_gastos
        
    with st.expander("👁️ Configurar Columnas Visibles (Egresos)"):
        columnas_gastos_actualizadas = st.multiselect(
            "Selecciona las columnas que deseas mostrar en la tabla de Egresos:",
            options=cols_mostrar_gastos,
            default=cols_validas_gastos
        )
        if columnas_gastos_actualizadas != st.session_state.columnas_visibles_gastos:
            if columnas_gastos_actualizadas:
                st.session_state.columnas_visibles_gastos = columnas_gastos_actualizadas
            else:
                st.session_state.columnas_visibles_gastos = cols_mostrar_gastos.copy()
            guardar_cache_local()
            st.rerun()

    if agrupar_gastos:
        st.warning("⚠️ **VISTA DE REVISIÓN AGRUPADA:** En este modo los gastos divididos se muestran consolidados en su total original. Para editar o borrar celdas, desmarca la casilla 'Agrupar Gastos Divididos'.")
        df_gastos_grouped = agrupar_gastos_divididos(df_gastos_sort)
        cols_mostrar_grouped = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO', 'CAPITULO', 'SUBCAPITULO']
        
        st.dataframe(
            df_gastos_grouped[cols_mostrar_grouped].style.format({
                'MONTO ORIG': "{:,.2f}",
                'TASA': "{:,.4f}",
                'MONTO BASE USD': formatear_usd,
                'HONORARIOS': formatear_usd,
                'COSTO TOTAL': formatear_usd
            }),
            use_container_width=True,
            height=400
        )
    else:
        # Obtener formas de pago dinámicas para no generar advertencias en el editor
        fp_gastos = sorted(list(set([str(fp).strip().upper() for fp in st.session_state.df_maestro['FORMA PAGO'].unique() if str(fp).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        for fp in ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"]:
            if fp not in fp_gastos:
                fp_gastos.append(fp)
                
        monedas_gastos = sorted(list(set([str(m).strip().upper() for m in st.session_state.df_maestro['MONEDA'].unique() if str(m).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        for m in ["USD", "VES", "EUR"]:
            if m not in monedas_gastos:
                monedas_gastos.append(m)
                
        estados_gastos = sorted(list(set([str(e).strip().upper() for e in st.session_state.df_maestro['ESTADO'].unique() if str(e).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        for e in ["PAGADO", "PENDIENTE"]:
            if e not in estados_gastos:
                estados_gastos.append(e)

        df_gastos_editado = st.data_editor(
            df_gastos_sort[cols_mostrar_gastos],
            num_rows="dynamic",
            use_container_width=True,
            height=400,
            disabled=['HONORARIOS', 'COSTO TOTAL'],
            column_order=st.session_state.columnas_visibles_gastos,
            column_config={
                "FECHA": st.column_config.DateColumn("📅 Fecha"),
                "MONEDA": st.column_config.SelectboxColumn("💵 Moneda", options=monedas_gastos, required=True),
                "TASA": st.column_config.NumberColumn("📈 Tasa", format="%.4f", min_value=0.0),
                "MONTO ORIG": st.column_config.NumberColumn("💰 Monto Orig.", format="%.2f", min_value=0.0),
                "% ADMIN": st.column_config.NumberColumn("💼 % Admin", format="%.2f", min_value=0.0),
                "HONORARIOS": st.column_config.NumberColumn("💼 Honorarios (USD)", format="$%.2f", disabled=True),
                "COSTO TOTAL": st.column_config.NumberColumn("🔴 Costo Total (USD)", format="$%.2f", disabled=True),
                "ESTADO": st.column_config.SelectboxColumn("✅ Estado", options=estados_gastos, required=True),
                "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_gastos, required=True),
            },
            key=f"editor_gastos_{st.session_state.reset_counter_gastos}"
        )
        
        col_save_g = st.columns([1, 1])
        with col_save_g[0]:
            if st.button("💾 Guardar Cambios de Egresos", type="primary", use_container_width=True):
                guardar_cambios_filtrados(df_gastos_sort[cols_mostrar_gastos], df_gastos_editado, clase_default="GASTO")
                st.success("✅ Egresos actualizados con éxito.")
                st.rerun()
        with col_save_g[1]:
            if st.button("👁️ Mostrar Columnas Ocultas / Restablecer Vista", use_container_width=True, key="reset_egresos"):
                st.session_state.reset_counter_gastos += 1
                st.rerun()

with tab_ingresos:
    st.markdown("### 💰 Control de Ingresos")
    st.info(f"Mostrando **{len(df_ingresos)}** registros. Puedes editar celdas o eliminar filas (seleccionándolas en la casilla izquierda y presionando la tecla Supr/Delete).")
    
    cols_mostrar_ing = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', 'MONTO BASE USD', 'FORMA PAGO', 'LINK COMPROBANTE']
    
    # Limpieza de columnas visibles de ingresos por seguridad
    cols_validas_ingresos = [col for col in st.session_state.columnas_visibles_ingresos if col in cols_mostrar_ing]
    if not cols_validas_ingresos:
        cols_validas_ingresos = cols_mostrar_ing.copy()
        st.session_state.columnas_visibles_ingresos = cols_validas_ingresos

    with st.expander("👁️ Configurar Columnas Visibles (Ingresos)"):
        columnas_ingresos_actualizadas = st.multiselect(
            "Selecciona las columnas que deseas mostrar en la tabla de Ingresos:",
            options=cols_mostrar_ing,
            default=cols_validas_ingresos
        )
        if columnas_ingresos_actualizadas != st.session_state.columnas_visibles_ingresos:
            if columnas_ingresos_actualizadas:
                st.session_state.columnas_visibles_ingresos = columnas_ingresos_actualizadas
            else:
                st.session_state.columnas_visibles_ingresos = cols_mostrar_ing.copy()
            guardar_cache_local()
            st.rerun()

    df_ingresos_sort = df_ingresos.sort_values('FECHA', ascending=False) if not df_ingresos.empty else pd.DataFrame(columns=cols_mostrar_ing)
    
    # Obtener formas de pago dinámicas para no generar advertencias en el editor
    fp_ingresos = sorted(list(set([str(fp).strip().upper() for fp in st.session_state.df_maestro['FORMA PAGO'].unique() if str(fp).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for fp in ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"]:
        if fp not in fp_ingresos:
            fp_ingresos.append(fp)
            
    monedas_ingresos = sorted(list(set([str(m).strip().upper() for m in st.session_state.df_maestro['MONEDA'].unique() if str(m).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for m in ["USD", "VES", "EUR"]:
        if m not in monedas_ingresos:
            monedas_ingresos.append(m)

    df_ingresos_editado = st.data_editor(
        df_ingresos_sort[cols_mostrar_ing],
        num_rows="dynamic",
        use_container_width=True,
        height=400,
        disabled=['MONTO BASE USD'],
        column_order=st.session_state.columnas_visibles_ingresos,
        column_config={
            "FECHA": st.column_config.DateColumn("📅 Fecha"),
            "MONEDA": st.column_config.SelectboxColumn("💵 Moneda", options=monedas_ingresos, required=True),
            "TASA": st.column_config.NumberColumn("📈 Tasa", format="%.4f", min_value=0.0),
            "MONTO ORIG": st.column_config.NumberColumn("💰 Monto", format="%.2f", min_value=0.0),
            "MONTO BASE USD": st.column_config.NumberColumn("💵 Monto USD", format="$%.2f", disabled=True),
            "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_ingresos, required=True),
        },
        key=f"editor_ingresos_{st.session_state.reset_counter_ingresos}"
    )
    
    col_save_i = st.columns([1, 1])
    with col_save_i[0]:
        if st.button("💾 Guardar Cambios de Ingresos", type="primary", use_container_width=True):
            guardar_cambios_filtrados(df_ingresos_sort[cols_mostrar_ing], df_ingresos_editado, clase_default="INGRESO")
            st.success("✅ Ingresos actualizados con éxito.")
            st.rerun()
    with col_save_i[1]:
        if st.button("👁️ Mostrar Columnas Ocultas / Restablecer Vista", use_container_width=True, key="reset_ingresos"):
            st.session_state.reset_counter_ingresos += 1
            st.rerun()

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

def guardar_cambios_contratos(df_original_filtrado, df_editado_filtrado):
    df_maestro = st.session_state.df_maestro.copy()
    global_admin = st.session_state.get('admin_pct_global', 15.0)
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        for col in df_editado_filtrado.columns:
            if col in df_maestro.columns:
                if col == '% ADMIN':
                    # Si el valor editado es igual al global default, guardarlo como 0.0 para mantener la vinculación global
                    for idx in indices_comunes:
                        val = df_editado_filtrado.loc[idx, col]
                        df_maestro.loc[idx, col] = 0.0 if val == global_admin else val
                else:
                    df_maestro.loc[indices_comunes, col] = df_editado_filtrado.loc[indices_comunes, col]
                
    # 3. Identificar filas nuevas añadidas
    indices_nuevos = df_editado_filtrado.index.difference(df_original_filtrado.index)
    if not indices_nuevos.empty:
        df_nuevos = df_editado_filtrado.loc[indices_nuevos].copy()
        df_nuevos['CLASE'] = 'GASTO'
        
        # Forzar tipo a CONTRATO si viene vacío
        if 'TIPO' in df_nuevos.columns:
            df_nuevos['TIPO'] = df_nuevos['TIPO'].fillna('').astype(str).str.strip().str.upper()
            df_nuevos.loc[df_nuevos['TIPO'] == '', 'TIPO'] = 'CONTRATO'
        else:
            df_nuevos['TIPO'] = 'CONTRATO'
            
        if '% ADMIN' in df_nuevos.columns:
            df_nuevos.loc[df_nuevos['% ADMIN'] == global_admin, '% ADMIN'] = 0.0
            
        # Rellenar columnas faltantes en el editor con valores por defecto
        for col in df_maestro.columns:
            if col not in df_nuevos.columns:
                df_nuevos[col] = 0.0 if col in ['MONTO ORIG', 'MONTO BASE USD', 'MONTO PAGADO', 'HONORARIOS', 'COSTO TOTAL', '% ADMIN', 'TASA'] else ''
        df_maestro = pd.concat([df_maestro, df_nuevos[df_maestro.columns]], ignore_index=True)
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        guardar_cache_local()

with tab_contratos:
    st.markdown("### 📄 Control de Contratos (Subcontratistas)")
    
    cols_mostrar_contratos = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', '% ADMIN', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO', 'CAPITULO', 'SUBCAPITULO', 'LINK FACTURA', 'LINK COMPROBANTE']
    
    # Filtrar contratos aplicando filtros globales y buscador universal (omitimos tipo porque siempre es CONTRATO/CONTRATISTA)
    df_contratos = df_gastos_base[df_gastos_base['TIPO'].isin(['CONTRATO', 'CONTRATISTA'])].copy()
    if mes_sel != "Todos":
        df_contratos = df_contratos[df_contratos['MES_AÑO'] == mes_sel]
    if capitulo_sel != "Todos":
        df_contratos = df_contratos[df_contratos['CAPITULO'] == capitulo_sel]
    if subcapitulo_sel != "Todos":
        df_contratos = df_contratos[df_contratos['SUBCAPITULO'] == subcapitulo_sel]
    if prov_sel != "Todos":
        df_contratos = df_contratos[df_contratos['PROVEEDOR'] == prov_sel]
    if estado_sel != "Todos":
        df_contratos = df_contratos[df_contratos['ESTADO'] == estado_sel]
    if search_query:
        df_contratos = aplicar_buscador_universal(df_contratos, search_query)

    df_contratos_sort = df_contratos.sort_values('FECHA', ascending=False) if not df_contratos.empty else pd.DataFrame(columns=cols_mostrar_contratos)
    if not df_contratos_sort.empty:
        mask_cero_c = (df_contratos_sort['% ADMIN'] == 0) | (df_contratos_sort['% ADMIN'].isna())
        df_contratos_sort.loc[mask_cero_c, '% ADMIN'] = admin_pct
        # Asegurar recalculo de honorarios y costo total sobre df_contratos_sort
        df_contratos_sort['HONORARIOS'] = df_contratos_sort['MONTO BASE USD'] * (df_contratos_sort['% ADMIN'] / 100.0)
        df_contratos_sort['COSTO TOTAL'] = df_contratos_sort['MONTO BASE USD'] + df_contratos_sort['HONORARIOS']

    # Métricas de Sumas de Contratos
    sum_orig_con = df_contratos_sort['MONTO ORIG'].sum() if not df_contratos_sort.empty else 0.0
    sum_hon_con = df_contratos_sort['HONORARIOS'].sum() if not df_contratos_sort.empty else 0.0
    sum_tot_con = df_contratos_sort['COSTO TOTAL'].sum() if not df_contratos_sort.empty else 0.0

    # Agrupar Monto Original por moneda para mostrar en el tooltip/help
    if not df_contratos_sort.empty:
        monto_orig_por_moneda_con = df_contratos_sort.groupby('MONEDA')['MONTO ORIG'].sum()
        monto_orig_str_con = " | ".join([f"{val:,.2f} {mon}" for mon, val in monto_orig_por_moneda_con.items()])
    else:
        monto_orig_str_con = "0.00 USD"

    col_mc1, col_mc2, col_mc3 = st.columns(3)
    col_mc1.metric(
        "💰 CONTRATOS MONTO ORIG.", 
        f"{sum_orig_con:,.2f}" if df_contratos_sort.empty or df_contratos_sort['MONEDA'].nunique() <= 1 else "Varios (ver ayuda)", 
        help=f"Detalle por Moneda: {monto_orig_str_con}\nNota: Si hay monedas mezcladas, la suma directa no es representativa en una sola moneda. Use el Costo Total (USD) como referencia unificada."
    )
    col_mc2.metric("💼 CONTRATOS HONORARIOS", f"$ {sum_hon_con:,.2f}")
    col_mc3.metric("🔴 CONTRATOS COSTO TOTAL", f"$ {sum_tot_con:,.2f}")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # Obtener formas de pago dinámicas para no generar advertencias en el editor
    fp_contratos = sorted(list(set([str(fp).strip().upper() for fp in st.session_state.df_maestro['FORMA PAGO'].unique() if str(fp).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for fp in ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"]:
        if fp not in fp_contratos:
            fp_contratos.append(fp)
            
    monedas_contratos = sorted(list(set([str(m).strip().upper() for m in st.session_state.df_maestro['MONEDA'].unique() if str(m).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for m in ["USD", "VES", "EUR"]:
        if m not in monedas_contratos:
            monedas_contratos.append(m)
            
    estados_contratos = sorted(list(set([str(e).strip().upper() for e in st.session_state.df_maestro['ESTADO'].unique() if str(e).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for e in ["PAGADO", "PENDIENTE"]:
        if e not in estados_contratos:
            estados_contratos.append(e)

    tipos_contratos = sorted(list(set([str(t).strip().upper() for t in st.session_state.df_maestro['TIPO'].unique() if str(t).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
    for t in ["CONTRATO", "CONTRATISTA"]:
        if t not in tipos_contratos:
            tipos_contratos.append(t)
            
    # 1. Resumen Consolidado por Subcontratista
    st.markdown("#### 📊 Resumen Consolidado de Subcontratistas")
    if not df_contratos_sort.empty:
        # Agrupar por proveedor sobre df_contratos_sort (que ya tiene los totales consistentes)
        contratos_grouped = df_contratos_sort.groupby('PROVEEDOR').agg({
            'COSTO TOTAL': 'sum',
            'MONTO PAGADO': 'sum'
        }).reset_index()
        contratos_grouped['SALDO CONTRATO'] = contratos_grouped['COSTO TOTAL'] - contratos_grouped['MONTO PAGADO']
        contratos_grouped['% EJECUCIÓN'] = (contratos_grouped['MONTO PAGADO'] / contratos_grouped['COSTO TOTAL'] * 100.0).fillna(0.0)
        
        st.dataframe(
            contratos_grouped,
            use_container_width=True,
            column_config={
                "PROVEEDOR": st.column_config.TextColumn("Subcontratista"),
                "COSTO TOTAL": st.column_config.NumberColumn("Monto Contratado (USD)", format="$%.2f"),
                "MONTO PAGADO": st.column_config.NumberColumn("Monto Ejecutado/Pagado (USD)", format="$%.2f"),
                "SALDO CONTRATO": st.column_config.NumberColumn("Saldo Pendiente (USD)", format="$%.2f"),
                "% EJECUCIÓN": st.column_config.ProgressColumn(
                    "% Ejecución",
                    help="Porcentaje del contrato pagado/ejecutado",
                    format="%.1f%%",
                    min_value=0.0,
                    max_value=100.0
                )
            },
            hide_index=True
        )
        
        # Gráfico comparativo de subcontratistas (Monto Contratado vs. Ejecutado)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📊 Gráfico Comparativo de Subcontratistas")
        
        df_chart_contratos = contratos_grouped.sort_values('COSTO TOTAL', ascending=True)
        df_melted = df_chart_contratos.melt(
            id_vars=['PROVEEDOR'],
            value_vars=['MONTO PAGADO', 'SALDO CONTRATO'],
            var_name='Estado',
            value_name='Monto (USD)'
        )
        df_melted['Estado'] = df_melted['Estado'].replace({
            'MONTO PAGADO': 'Ejecutado (Pagado)',
            'SALDO CONTRATO': 'Pendiente'
        })
        
        fig_sub = px.bar(
            df_melted,
            y='PROVEEDOR',
            x='Monto (USD)',
            color='Estado',
            orientation='h',
            title="Comparativa de Contratos: Monto Ejecutado vs. Pendiente por Subcontratista",
            labels={'PROVEEDOR': 'Subcontratista', 'Monto (USD)': 'Monto (USD)', 'Estado': 'Estatus del Contrato'},
            color_discrete_map={
                'Ejecutado (Pagado)': '#10b981',  # Verde
                'Pendiente': '#ef4444'  # Rojo
            }
        )
        fig_sub.update_layout(
            margin=dict(t=40, b=20, l=40, r=20),
            barmode='stack',
            hovermode="y unified"
        )
        st.plotly_chart(fig_sub, use_container_width=True)
    else:
        st.info("No se encontraron registros de tipo CONTRATO o CONTRATISTA en la base de datos.")
        
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # 2. Editor Detallado de Contratos
    st.markdown("#### ✍️ Detalle y Edición de Contratos")
    
    agrupar_contratos = st.checkbox(
        "🔍 Agrupar Pagos/Gastos Divididos", 
        value=False, 
        key="agrupar_contratos_toggle", 
        help="Consolida los pagos parciales o divididos (que comparten fecha, subcontratista y descripción) en una sola fila para ver el pago total completo, ocultando la subdivisión por capítulos."
    )
    
    df_contratos_sort = df_contratos.sort_values('FECHA', ascending=False) if not df_contratos.empty else pd.DataFrame(columns=cols_mostrar_contratos)
    if not df_contratos_sort.empty:
        mask_cero_c = (df_contratos_sort['% ADMIN'] == 0) | (df_contratos_sort['% ADMIN'].isna())
        df_contratos_sort.loc[mask_cero_c, '% ADMIN'] = admin_pct

    if agrupar_contratos:
        st.warning("⚠️ **VISTA DE REVISIÓN AGRUPADA:** En este modo los pagos divididos se muestran consolidados en su total original. Para editar o borrar celdas, desmarca la casilla 'Agrupar Pagos/Gastos Divididos'.")
        df_contratos_grouped = agrupar_gastos_divididos(df_contratos_sort)
        cols_mostrar_grouped = ['FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO']
        st.dataframe(
            df_contratos_grouped[cols_mostrar_grouped].style.format({
                'MONTO ORIG': "{:,.2f}",
                'TASA': "{:,.4f}",
                'MONTO BASE USD': formatear_usd,
                'HONORARIOS': formatear_usd,
                'COSTO TOTAL': formatear_usd
            }),
            use_container_width=True,
            height=350
        )
    else:
        df_contratos_editado = st.data_editor(
            df_contratos_sort[cols_mostrar_contratos],
            num_rows="dynamic",
            use_container_width=True,
            height=350,
            disabled=['HONORARIOS', 'COSTO TOTAL'],
            column_config={
                "FECHA": st.column_config.DateColumn("📅 Fecha"),
                "PROVEEDOR": st.column_config.TextColumn("Subcontratista"),
                "DESCRIPCION": st.column_config.TextColumn("Descripción"),
                "MONEDA": st.column_config.SelectboxColumn("💵 Moneda", options=monedas_contratos, required=True),
                "TASA": st.column_config.NumberColumn("📈 Tasa", format="%.4f", min_value=0.0),
                "MONTO ORIG": st.column_config.NumberColumn("💰 Monto Orig.", format="%.2f", min_value=0.0),
                "% ADMIN": st.column_config.NumberColumn("💼 % Admin", format="%.2f", min_value=0.0),
                "HONORARIOS": st.column_config.NumberColumn("💼 Honorarios (USD)", format="$%.2f", disabled=True),
                "COSTO TOTAL": st.column_config.NumberColumn("🔴 Costo Total (USD)", format="$%.2f", disabled=True),
                "ESTADO": st.column_config.SelectboxColumn("✅ Estado", options=estados_contratos, required=True),
                "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_contratos, required=True),
                "TIPO": st.column_config.SelectboxColumn("🏷️ Tipo", options=tipos_contratos, required=True),
                "CAPITULO": st.column_config.TextColumn("🏗️ Capítulo"),
                "SUBCAPITULO": st.column_config.TextColumn("🧱 Subcapítulo"),
            },
            key=f"editor_contratos_{st.session_state.reset_counter_contratos}"
        )
        
        col_save_c = st.columns([1, 1])
        with col_save_c[0]:
            if st.button("💾 Guardar Cambios de Contratos", type="primary", use_container_width=True):
                guardar_cambios_contratos(df_contratos_sort[cols_mostrar_contratos], df_contratos_editado)
                st.success("✅ Contratos actualizados con éxito.")
                st.rerun()
        with col_save_c[1]:
            if st.button("👁️ Restablecer Vista de Contratos", use_container_width=True, key="reset_contratos"):
                st.session_state.reset_counter_contratos += 1
                st.rerun()


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
    
    # 1. Gráfico Comparativo de Ingresos vs Egresos
    st.subheader("📈 Comparativa de Ingresos vs Egresos (Flujo de Caja)")
    
    df_eg_all = df_gastos_base.copy() if not df_gastos_base.empty else pd.DataFrame(columns=['FECHA', 'COSTO TOTAL'])
    df_in_all = df_ingresos.copy() if not df_ingresos.empty else pd.DataFrame(columns=['FECHA', 'MONTO BASE USD'])
    
    if not df_eg_all.empty or not df_in_all.empty:
        df_eg_all['TIPO_TRANS'] = 'EGRESO'
        df_eg_all['MONTO_USD'] = df_eg_all['COSTO TOTAL'] if 'COSTO TOTAL' in df_eg_all.columns else 0.0
        
        df_in_all['TIPO_TRANS'] = 'INGRESO'
        df_in_all['MONTO_USD'] = df_in_all['MONTO BASE USD'] if 'MONTO BASE USD' in df_in_all.columns else 0.0
        
        df_trans = pd.concat([
            df_eg_all[['FECHA', 'TIPO_TRANS', 'MONTO_USD']], 
            df_in_all[['FECHA', 'TIPO_TRANS', 'MONTO_USD']]
        ], ignore_index=True)
        
        df_trans = df_trans.dropna(subset=['FECHA'])
        df_trans['FECHA'] = pd.to_datetime(df_trans['FECHA'], errors='coerce')
        df_trans = df_trans.dropna(subset=['FECHA'])
        
        if not df_trans.empty:
            col_ctrl1, col_ctrl2 = st.columns(2)
            with col_ctrl1:
                periodo_graf = st.selectbox("📅 Periodicidad del Gráfico", ["Mensual", "Semanal"], key="periodo_graf")
            with col_ctrl2:
                acumulado_graf = st.radio("📈 Modo del Gráfico", ["Acumulado (Histórico)", "Por Período (Sin Acumular)"], key="acumulado_graf", horizontal=True)
                
            # Calcular el período
            if periodo_graf == "Mensual":
                df_trans['PERIODO'] = df_trans['FECHA'].dt.to_period('M')
            else:
                df_trans['PERIODO'] = df_trans['FECHA'].dt.to_period('W')
                
            # Agrupar
            grouped = df_trans.groupby(['PERIODO', 'TIPO_TRANS'])['MONTO_USD'].sum().unstack(fill_value=0.0).reset_index()
            
            # Asegurar que ambas columnas existan
            if 'INGRESO' not in grouped.columns:
                grouped['INGRESO'] = 0.0
            if 'EGRESO' not in grouped.columns:
                grouped['EGRESO'] = 0.0
                
            # Ordenar por periodo
            grouped = grouped.sort_values('PERIODO')
            grouped['PERIODO_STR'] = grouped['PERIODO'].astype(str)
            
            is_acumulado = acumulado_graf == "Acumulado (Histórico)"
            
            if is_acumulado:
                grouped['Ingresos Acumulados'] = grouped['INGRESO'].cumsum()
                grouped['Egresos Acumulados'] = grouped['EGRESO'].cumsum()
                grouped['Saldo Acumulado'] = grouped['Ingresos Acumulados'] - grouped['Egresos Acumulados']
                
                df_plot = grouped.melt(id_vars=['PERIODO_STR'], value_vars=['Ingresos Acumulados', 'Egresos Acumulados', 'Saldo Acumulado'], 
                                       var_name='Concepto', value_name='Monto (USD)')
                
                fig_comp = px.line(df_plot, x='PERIODO_STR', y='Monto (USD)', color='Concepto',
                                   title=f"Flujo de Caja Acumulado ({periodo_graf})",
                                   labels={'PERIODO_STR': 'Período', 'Monto (USD)': 'Monto (USD)'},
                                   color_discrete_map={
                                       'Ingresos Acumulados': '#10b981', # Verde
                                       'Egresos Acumulados': '#ef4444', # Rojo
                                       'Saldo Acumulado': '#3b82f6' # Azul
                                   },
                                   markers=True)
            else:
                grouped['Ingresos'] = grouped['INGRESO']
                grouped['Egresos'] = grouped['EGRESO']
                grouped['Saldo Neto'] = grouped['INGRESO'] - grouped['EGRESO']
                
                df_plot = grouped.melt(id_vars=['PERIODO_STR'], value_vars=['Ingresos', 'Egresos', 'Saldo Neto'], 
                                       var_name='Concepto', value_name='Monto (USD)')
                
                fig_comp = px.bar(df_plot, x='PERIODO_STR', y='Monto (USD)', color='Concepto',
                                  barmode='group',
                                  title=f"Ingresos vs Egresos por Período ({periodo_graf})",
                                  labels={'PERIODO_STR': 'Período', 'Monto (USD)': 'Monto (USD)'},
                                  color_discrete_map={
                                      'Ingresos': '#10b981',
                                      'Egresos': '#ef4444',
                                      'Saldo Neto': '#3b82f6'
                                  })
            
            fig_comp.update_layout(margin=dict(t=40, b=20, l=40, r=20), hovermode="x unified")
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.warning("No hay transacciones con fechas válidas para graficar la comparativa.")
    else:
        st.warning("No hay datos de ingresos ni egresos para graficar la comparativa.")
        
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("📊 Distribución y Evolución Detallada")
    
    if not df_gastos.empty:
        # Selector para alternar o mostrar ambos gráficos
        vista_grafico = st.radio(
            "🔍 Visualizar detalle por:", 
            ["Capítulos", "Sub-Capítulos", "Ambos (Ver los dos)", "Relación Jerárquica (Mapa de Árbol)"], 
            index=2, 
            horizontal=True, 
            key="vista_detalle_grafico"
        )
        
        if vista_grafico in ["Capítulos", "Ambos (Ver los dos)"]:
            # 1. Gráfico de Capítulos - Barra Apilada (Stacked) por Tipo de Gasto
            graf_cap = df_gastos.groupby(['CAPITULO', 'TIPO'])['COSTO TOTAL'].sum().reset_index()
            fig_cap = px.bar(graf_cap, x='CAPITULO', y='COSTO TOTAL', color='TIPO',
                             title="Distribución por Capítulo (Composición por Tipo de Gasto)",
                             labels={'CAPITULO': 'Capítulo', 'COSTO TOTAL': 'Costo Total (USD)', 'TIPO': 'Tipo de Gasto'},
                             color_discrete_sequence=px.colors.qualitative.Plotly)
            fig_cap.update_layout(margin=dict(t=45, b=20, l=40, r=20), barmode='stack', hovermode="x unified")
            fig_cap.update_xaxes(categoryorder='total descending')
            st.plotly_chart(fig_cap, use_container_width=True)
            
        if vista_grafico in ["Sub-Capítulos", "Ambos (Ver los dos)"]:
            # 2. Gráfico de Sub-Capítulos - Barra Apilada (Stacked) por Tipo de Gasto
            graf_subcap = df_gastos.groupby(['SUBCAPITULO', 'TIPO'])['COSTO TOTAL'].sum().reset_index()
            fig_subcap = px.bar(graf_subcap, x='SUBCAPITULO', y='COSTO TOTAL', color='TIPO',
                                title="Distribución por Sub-Capítulo (Composición por Tipo de Gasto)",
                                labels={'SUBCAPITULO': 'Sub-Capítulo', 'COSTO TOTAL': 'Costo Total (USD)', 'TIPO': 'Tipo de Gasto'},
                                color_discrete_sequence=px.colors.qualitative.Safe)
            fig_subcap.update_layout(margin=dict(t=45, b=20, l=40, r=20), barmode='stack', hovermode="x unified")
            fig_subcap.update_xaxes(categoryorder='total descending')
            st.plotly_chart(fig_subcap, use_container_width=True)
            
        if vista_grafico == "Relación Jerárquica (Mapa de Árbol)":
            # 3. Gráficos de Relación Jerárquica (Treemap y Sunburst)
            col_hier1, col_hier2 = st.columns(2)
            with col_hier1:
                orden_jerarquia = st.selectbox(
                    "🔍 Dirección de la Jerarquía:", 
                    ["Capítulo → Sub-Capítulo", "Sub-Capítulo → Capítulo"],
                    key="orden_jerarquia_seleccionado"
                )
            
            # Definir la ruta según la selección
            ruta_jerarquia = ['CAPITULO', 'SUBCAPITULO'] if orden_jerarquia == "Capítulo → Sub-Capítulo" else ['SUBCAPITULO', 'CAPITULO']
            
            df_hierarchical = df_gastos.copy()
            df_hierarchical['CAPITULO'] = df_hierarchical['CAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN CAPÍTULO')
            df_hierarchical['SUBCAPITULO'] = df_hierarchical['SUBCAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN SUBCAPÍTULO').replace('-', 'SIN SUBCAPÍTULO')
            
            graf_hier = df_hierarchical.groupby(['CAPITULO', 'SUBCAPITULO'])['COSTO TOTAL'].sum().reset_index()
            graf_hier = graf_hier[graf_hier['COSTO TOTAL'] > 0]
            
            if not graf_hier.empty:
                fig_tree = px.treemap(
                    graf_hier, 
                    path=ruta_jerarquia, 
                    values='COSTO TOTAL',
                    title=f"Mapa de Árbol: {orden_jerarquia} (Haz clic para ampliar)",
                    color='COSTO TOTAL',
                    color_continuous_scale='Mint',
                    labels={'parent': 'Categoría Padre', 'id': 'Categoría', 'COSTO TOTAL': 'Costo Total (USD)'}
                )
                fig_tree.update_layout(margin=dict(t=50, b=20, l=20, r=20))
                st.plotly_chart(fig_tree, use_container_width=True)
                
                st.info("💡 **Consejo de navegación:** En el Mapa de Árbol, puedes hacer **clic** en cualquier bloque superior para ver su desglose interno, y hacer clic en la barra superior para regresar.")
                
                fig_sun = px.sunburst(
                    graf_hier, 
                    path=ruta_jerarquia, 
                    values='COSTO TOTAL',
                    title=f"Estructura concéntrica ({orden_jerarquia})",
                    color='COSTO TOTAL',
                    color_continuous_scale='Mint',
                    labels={'parent': 'Categoría Padre', 'id': 'Categoría', 'COSTO TOTAL': 'Costo Total (USD)'}
                )
                fig_sun.update_layout(margin=dict(t=50, b=20, l=20, r=20))
                
                with st.expander("🔄 Ver Estructura Circular Alternativa (Sunburst)"):
                    st.plotly_chart(fig_sun, use_container_width=True)
            else:
                st.warning("No hay datos suficientes con costos mayores a cero para graficar la relación jerárquica.")
        
        # 3. Columnas para los otros gráficos detallados
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Gráfico Top Proveedores (Barras Horizontales)
            graf_prov = df_gastos.groupby('PROVEEDOR')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=True).tail(10)
            fig_prov = px.bar(graf_prov, x='COSTO TOTAL', y='PROVEEDOR', orientation='h',
                              title="Top 10 Proveedores (Costo Total)",
                              color='COSTO TOTAL', color_continuous_scale='Blues')
            fig_prov.update_layout(margin=dict(t=40, b=20, l=40, r=20), coloraxis_showscale=False)
            st.plotly_chart(fig_prov, use_container_width=True)
            
            # Gráfico por Tipo de Gasto (Donut)
            graf_tipo = df_gastos.groupby('TIPO')['COSTO TOTAL'].sum().reset_index()
            fig_tipo = px.pie(graf_tipo, values='COSTO TOTAL', names='TIPO', hole=0.4, 
                             title="Distribución Total por Tipo de Gasto",
                             color_discrete_sequence=px.colors.sequential.Plotly3)
            fig_tipo.update_layout(margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig_tipo, use_container_width=True)

        with col_g2:
            # Gráfico de Evolución Mensual
            graf_mes = df_gastos.groupby('MES_AÑO')['COSTO TOTAL'].sum().reset_index()
            fig_mes = px.bar(graf_mes, x='MES_AÑO', y='COSTO TOTAL', 
                             title="Evolución de Gastos por Período",
                             color_discrete_sequence=['#3b82f6'])
            fig_mes.update_layout(margin=dict(t=40, b=20, l=40, r=20))
            st.plotly_chart(fig_mes, use_container_width=True)
            
    else:
        st.warning("No hay datos suficientes para generar gráficos.")

with tab_editor:
    st.markdown("### 🛠️ Editor Maestro de Base de Datos")
    st.warning("⚠️ **ZONA DE EDICIÓN:** Aquí puedes comportarte como si estuvieras en Excel. Haz doble clic en cualquier celda para **modificar su valor**, o selecciona una fila entera (haciendo clic en la casilla vacía de la izquierda) y presiona la tecla **'Suprimir' o 'Delete' en tu teclado para borrarla**.")
    
    # Mostrar el DataFrame interactivo completo (filtrado si hay buscador universal)
    df_para_editar = st.session_state.df_maestro.copy()
    if search_query:
        df_para_editar = aplicar_buscador_universal(df_para_editar, search_query)
        st.info(f"🔍 Mostrando {len(df_para_editar)} registros coincidentes con '{search_query}'.")

    # Métricas de Sumas de Editor Maestro (solo de la clase GASTO para mantener coherencia con honorarios y costo total)
    df_ed_gastos = df_para_editar[df_para_editar['CLASE'] == 'GASTO']
    sum_orig_ed_g = df_ed_gastos['MONTO ORIG'].sum() if not df_ed_gastos.empty else 0.0
    sum_hon_ed_g = df_ed_gastos['HONORARIOS'].sum() if not df_ed_gastos.empty else 0.0
    sum_tot_ed_g = df_ed_gastos['COSTO TOTAL'].sum() if not df_ed_gastos.empty else 0.0

    # Agrupar Monto Original de Gastos por moneda para el tooltip
    if not df_ed_gastos.empty:
        monto_orig_por_moneda_ed = df_ed_gastos.groupby('MONEDA')['MONTO ORIG'].sum()
        monto_orig_str_ed = " | ".join([f"{val:,.2f} {mon}" for mon, val in monto_orig_por_moneda_ed.items()])
    else:
        monto_orig_str_ed = "0.00 USD"

    col_ed1, col_ed2, col_ed3 = st.columns(3)
    col_ed1.metric(
        "💰 SUMA MONTO ORIG. (GASTOS)", 
        f"{sum_orig_ed_g:,.2f}" if df_ed_gastos.empty or df_ed_gastos['MONEDA'].nunique() <= 1 else "Varios (ver ayuda)", 
        help=f"Detalle por Moneda: {monto_orig_str_ed}\nNota: Si hay monedas mezcladas, la suma directa no es representativa en una sola moneda. Use el Costo Total (USD) como referencia unificada."
    )
    col_ed2.metric("💼 SUMA HONORARIOS (GASTOS)", f"$ {sum_hon_ed_g:,.2f}")
    col_ed3.metric("🔴 SUMA COSTO TOTAL (GASTOS)", f"$ {sum_tot_ed_g:,.2f}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # st.data_editor permite editar celdas, borrar filas y añadir filas dinámicamente
    df_editado = st.data_editor(
        df_para_editar,
        num_rows="dynamic",
        use_container_width=True,
        height=500,
        key="editor_maestro"
    )
    
    if st.button("💾 Guardar Cambios del Editor", type="primary", use_container_width=True):
        guardar_cambios_maestro(df_para_editar, df_editado)
        st.success("✅ Base de datos actualizada con tus modificaciones. Ahora ve a descargar tu CSV Maestro.")
        st.rerun()

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


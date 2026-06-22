import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import datetime
import urllib.request
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, NextPageTemplate, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        if self._pageNumber == 1:
            return
        self.saveState()
        
        # Get actual page dimensions dynamically
        width, height = self._pagesize
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1e3a8a"))
        self.drawString(54, height - 42, "Reporte Maestro de Control de Obra")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        self.drawRightString(width - 54, height - 42, datetime.date.today().strftime('%d/%m/%Y'))
        
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, height - 50, width - 54, height - 50)
        
        # Footer
        self.line(54, 52, width - 54, 52)
        self.drawString(54, 40, "Desarrollado por DI MATTEO DESIGN-DIMAQUINAS C.A.")
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(width - 54, 40, page_text)
        self.restoreState()

def generar_grafico_tipo_gasto(df_gastos):
    if df_gastos.empty:
        return None
    df_grouped = df_gastos.groupby('TIPO')['COSTO TOTAL'].sum().reset_index()
    df_grouped = df_grouped[df_grouped['COSTO TOTAL'] > 0]
    if df_grouped.empty:
        return None
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    ax.pie(df_grouped['COSTO TOTAL'], labels=df_grouped['TIPO'], autopct='%1.1f%%', 
           colors=plt.cm.tab20.colors, startangle=90, textprops={'fontsize': 8.5})
    ax.axis('equal')
    ax.set_title("Egresos por Tipo de Gasto", fontsize=11, fontweight='bold', pad=10)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def generar_grafico_ejec_vs_est(df_presupuestos):
    if df_presupuestos.empty:
        return None
    df_sorted = df_presupuestos.sort_values('MONTO ESTIMADO', ascending=True)
    
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    y = range(len(df_sorted))
    
    monto_ej = df_sorted['MONTO EJECUTADO'].values
    monto_est = df_sorted['MONTO ESTIMADO'].values
    
    restante = [max(est - ej, 0.0) for est, ej in zip(monto_est, monto_ej)]
    exceso = [max(ej - est, 0.0) for est, ej in zip(monto_est, monto_ej)]
    
    ax.barh(y, monto_ej, label='Ejecutado (Real)', color='#ef4444')
    ax.barh(y, restante, left=monto_ej, label='Restante (Margen)', color='#3b82f6')
    ax.barh(y, exceso, left=[ej + r for ej, r in zip(monto_ej, restante)], label='Exceso (Desviación)', color='#7f1d1d')
    
    ax.set_yticks(y)
    ax.set_yticklabels(df_sorted['CAPITULO'], fontsize=7.5)
    ax.set_xlabel('Monto (USD)', fontsize=8.5)
    ax.set_title('Progreso Presupuesto por Capítulo', fontsize=11, fontweight='bold', pad=10)
    ax.legend(fontsize=7.5, loc='lower right')
    ax.tick_params(axis='x', which='major', labelsize=7.5)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def generar_grafico_contratos(df_contratos):
    if df_contratos.empty:
        return None
    contratos_grouped = df_contratos.groupby('PROVEEDOR').agg({
        'COSTO TOTAL': 'sum',
        'MONTO PAGADO': 'sum'
    }).reset_index()
    contratos_grouped['PENDIENTE'] = contratos_grouped['COSTO TOTAL'] - contratos_grouped['MONTO PAGADO']
    
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    x = range(len(contratos_grouped))
    width = 0.5
    ax.bar(x, contratos_grouped['MONTO PAGADO'], width, label='Ejecutado (Pagado)', color='#10b981')
    ax.bar(x, contratos_grouped['PENDIENTE'], width, bottom=contratos_grouped['MONTO PAGADO'], label='Pendiente', color='#ef4444')
    ax.set_xticks(x)
    ax.set_xticklabels(contratos_grouped['PROVEEDOR'], rotation=15, ha='right', fontsize=7.5)
    ax.set_ylabel('Monto (USD)', fontsize=8.5)
    ax.set_title('Contratos: Monto Ejecutado vs Pendiente', fontsize=11, fontweight='bold', pad=10)
    ax.legend(fontsize=7.5)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def slice_and_dice(sizes, x, y, w, h):
    total = sum(sizes)
    if total == 0:
        return [(x, y, w, h) for _ in sizes]
    
    rects = []
    current_x = x
    current_y = y
    horizontal = w >= h
    
    for size in sizes:
        fraction = size / total
        if horizontal:
            box_w = w * fraction
            rects.append((current_x, current_y, box_w, h))
            current_x += box_w
        else:
            box_h = h * fraction
            rects.append((current_x, current_y, w, box_h))
            current_y += box_h
    return rects

def generar_grafico_cap_stacked_pdf(df_gastos):
    if df_gastos.empty:
        return None
    df_grouped = df_gastos.groupby(['CAPITULO', 'TIPO'])['COSTO TOTAL'].sum().unstack(fill_value=0.0)
    df_grouped['TOTAL'] = df_grouped.sum(axis=1)
    df_grouped = df_grouped.sort_values('TOTAL', ascending=True)
    df_grouped = df_grouped.drop(columns=['TOTAL'])
    
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    df_grouped.plot(kind='barh', stacked=True, ax=ax, colormap='tab20')
    ax.set_title("Egresos por Capítulo (por Tipo)", fontsize=11, fontweight='bold', pad=8)
    ax.set_xlabel("Monto (USD)", fontsize=8.5)
    ax.set_ylabel("", fontsize=8.5)
    ax.tick_params(axis='both', which='major', labelsize=8)
    ax.legend(fontsize=7.5, loc='lower right')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def generar_grafico_subcap_stacked_pdf(df_gastos):
    if df_gastos.empty:
        return None
    df_grouped = df_gastos.groupby(['SUBCAPITULO', 'TIPO'])['COSTO TOTAL'].sum().unstack(fill_value=0.0)
    df_grouped = df_grouped[df_grouped.sum(axis=1) > 0]
    df_grouped['TOTAL'] = df_grouped.sum(axis=1)
    df_grouped = df_grouped.sort_values('TOTAL', ascending=True).tail(15)
    df_grouped = df_grouped.drop(columns=['TOTAL'])
    
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    df_grouped.plot(kind='barh', stacked=True, ax=ax, colormap='tab20b')
    ax.set_title("Top 15 Sub-Capítulos (por Tipo)", fontsize=11, fontweight='bold', pad=8)
    ax.set_xlabel("Monto (USD)", fontsize=8.5)
    ax.set_ylabel("", fontsize=8.5)
    ax.tick_params(axis='both', which='major', labelsize=7.5)
    ax.legend(fontsize=7.5, loc='lower right')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def generar_grafico_treemap_pdf(df_gastos):
    if df_gastos.empty:
        return None
    df_hier = df_gastos.copy()
    df_hier['CAPITULO'] = df_hier['CAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN CAPÍTULO')
    df_hier['SUBCAPITULO'] = df_hier['SUBCAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN SUBCAPÍTULO').replace('-', 'SIN SUBCAPÍTULO')
    
    df_grouped = df_hier.groupby(['CAPITULO', 'SUBCAPITULO'])['COSTO TOTAL'].sum().reset_index()
    df_grouped = df_grouped[df_grouped['COSTO TOTAL'] > 0]
    if df_grouped.empty:
        return None
        
    df_cap = df_grouped.groupby('CAPITULO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
    
    fig, ax = plt.subplots(figsize=(10.0, 5.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')
    
    cap_names = df_cap['CAPITULO'].tolist()
    cap_vals = df_cap['COSTO TOTAL'].tolist()
    cap_rects = slice_and_dice(cap_vals, 0, 0, 100, 100)
    
    import matplotlib.colors as mcolors
    cmap = matplotlib.colormaps['GnBu']
    norm = mcolors.Normalize(vmin=0, vmax=max(cap_vals) if cap_vals else 1)
    
    for i, (name, val) in enumerate(zip(cap_names, cap_vals)):
        cx, cy, cw, ch = cap_rects[i]
        if cw <= 0 or ch <= 0:
            continue
            
        color = cmap(norm(val))
        rect = plt.Rectangle((cx, cy), cw, ch, facecolor=color, edgecolor='white', linewidth=1.0)
        ax.add_patch(rect)
        
        if cw > 12 and ch > 8:
            short_name = name[:18] + '...' if len(name) > 20 else name
            ax.text(cx + cw/2, cy + ch - 5, f"{short_name}\n${val:,.0f}", ha='center', va='top', fontsize=7.5, fontweight='bold', color='#1e3a8a')
            
        df_sub = df_grouped[df_grouped['CAPITULO'] == name].sort_values('COSTO TOTAL', ascending=False)
        sub_names = df_sub['SUBCAPITULO'].tolist()
        sub_vals = df_sub['COSTO TOTAL'].tolist()
        sub_rects = slice_and_dice(sub_vals, cx, cy, cw, ch)
        
        for j, (sub_name, sub_val) in enumerate(zip(sub_names, sub_vals)):
            sx, sy, sw, sh = sub_rects[j]
            if sw <= 0 or sh <= 0:
                continue
            sub_rect = plt.Rectangle((sx, sy), sw, sh, facecolor='none', edgecolor='black', linewidth=0.3, alpha=0.2)
            ax.add_patch(sub_rect)
            
            if sw > 15 and sh > 10:
                short_sub = sub_name[:12] + '..' if len(sub_name) > 14 else sub_name
                ax.text(sx + sw/2, sy + sh/2 - 2, f"{short_sub}\n${sub_val:,.0f}", ha='center', va='center', fontsize=6.0, color='#1f2937')
                
    ax.set_title("Relación Jerárquica: Mapa de Árbol", fontsize=11, fontweight='bold', pad=10)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=640, height=320)

def generar_grafico_sunburst_pdf(df_gastos):
    if df_gastos.empty:
        return None
        
    df_hier = df_gastos.copy()
    df_hier['CAPITULO'] = df_hier['CAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN CAPÍTULO')
    df_hier['SUBCAPITULO'] = df_hier['SUBCAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN SUBCAPÍTULO').replace('-', 'SIN SUBCAPÍTULO')
    
    df_grouped = df_hier.groupby(['CAPITULO', 'SUBCAPITULO'])['COSTO TOTAL'].sum().reset_index()
    df_grouped = df_grouped[df_grouped['COSTO TOTAL'] > 0]
    if df_grouped.empty:
        return None
        
    df_grouped = df_grouped.sort_values(['CAPITULO', 'COSTO TOTAL'], ascending=[True, False])
    df_cap = df_grouped.groupby('CAPITULO')['COSTO TOTAL'].sum().reset_index().sort_values('CAPITULO')
    
    fig, ax = plt.subplots(figsize=(7.5, 5.8))
    
    cmap = matplotlib.colormaps['GnBu']
    import matplotlib.colors as mcolors
    
    outer_vals = df_grouped['COSTO TOTAL'].tolist()
    outer_labels = df_grouped['SUBCAPITULO'].tolist()
    
    inner_vals = df_cap['COSTO TOTAL'].tolist()
    inner_labels = df_cap['CAPITULO'].tolist()
    
    norm_inner = mcolors.Normalize(vmin=0, vmax=max(inner_vals) if inner_vals else 1)
    inner_colors = [cmap(norm_inner(v)) for v in inner_vals]
    
    outer_colors = []
    for i, row in df_grouped.iterrows():
        cap = row['CAPITULO']
        cap_row = df_cap[df_cap['CAPITULO'] == cap]
        if not cap_row.empty:
            cap_idx = cap_row.index[0]
            list_of_caps = df_cap['CAPITULO'].tolist()
            color_idx = list_of_caps.index(cap)
            outer_colors.append(inner_colors[color_idx])
        else:
            outer_colors.append('#e2e8f0')
            
    inner_labels_clean = [lab if val/sum(inner_vals) > 0.05 else '' for lab, val in zip(inner_labels, inner_vals)]
    outer_labels_clean = [lab if val/sum(outer_vals) > 0.05 else '' for lab, val in zip(outer_labels, outer_vals)]
    
    ax.pie(inner_vals, labels=inner_labels_clean, radius=0.6, colors=inner_colors,
           wedgeprops=dict(width=0.3, edgecolor='white', linewidth=0.5), labeldistance=0.4, textprops={'fontsize': 7.0, 'weight': 'bold', 'color': '#1e3a8a'})
              
    ax.pie(outer_vals, labels=outer_labels_clean, radius=1.0, colors=outer_colors,
           wedgeprops=dict(width=0.4, edgecolor='white', linewidth=0.5), labeldistance=0.8, textprops={'fontsize': 5.5, 'color': '#1f2937'})
              
    ax.set(aspect="equal")
    ax.set_title("Estructura Concéntrica", fontsize=11, fontweight='bold', pad=10)
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=400, height=320)

def generar_pdf_maestro(df_app, empresa_nombre, obra_nombre, usuario_actual, admin_pct, opciones_pdf=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    # Options dictionary fallback (default: all True)
    if opciones_pdf is None:
        opciones_pdf = {
            "flujo_caja": True,
            "tipo_gasto": True,
            "progreso_cap": True,
            "egresos_cap": True,
            "subcap": True,
            "treemap": True,
            "sunburst": True,
            "contratos_graf": True,
            "egresos_tabla": True,
            "ingresos_tabla": True,
            "contratos_tabla": True,
            "presupuestos_tabla": True,
        }
    
    # Define Page Templates for mixed layout
    frame_p = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='portrait_frame')
    frame_l = Frame(54, 72, 684, 468, id='landscape_frame') # margin 54, width 792-108=684, height 612-144=468
    
    template_p = PageTemplate(id='portrait', frames=frame_p, pagesize=letter)
    template_l = PageTemplate(id='landscape', frames=frame_l, pagesize=landscape(letter))
    doc.addPageTemplates([template_p, template_l])
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    style_normal = styles['Normal']
    
    # Primary theme colors
    c_primary = colors.HexColor("#1e3a8a")
    c_secondary = colors.HexColor("#3b82f6")
    c_text = colors.HexColor("#1f2937")
    c_light_bg = colors.HexColor("#f8fafc")
    
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=22,
        textColor=c_primary,
        spaceAfter=15
    )
    
    style_subtitle = ParagraphStyle(
        'DocSubtitle',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=11,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=25
    )
    
    style_h1 = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=c_primary,
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    style_body = ParagraphStyle(
        'BodyTextCustom',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=9,
        textColor=c_text,
        leading=13
    )
    
    style_th = ParagraphStyle(
        'TableHeader',
        parent=style_normal,
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.white,
        alignment=1 # Center
    )
    
    style_td = ParagraphStyle(
        'TableCell',
        parent=style_normal,
        fontName='Helvetica',
        fontSize=7,
        textColor=c_text,
        leading=9
    )
    
    style_td_num = ParagraphStyle(
        'TableCellNum',
        parent=style_td,
        alignment=2 # Right
    )
    
    style_td_bold = ParagraphStyle(
        'TableCellBold',
        parent=style_td,
        fontName='Helvetica-Bold'
    )
    

    def df_to_pdf_table(df, style_th, style_td_num, c_primary):
        headers = [Paragraph('<b>' + str(col) + '</b>', style_th) for col in df.columns]
        rows = [headers]
        for _, row in df.iterrows():
            row_data = []
            for col in df.columns:
                val = row[col]
                if isinstance(val, (int, float)):
                    if 'COSTO' in str(col).upper() or 'MONTO' in str(col).upper() or col == 'COSTO TOTAL':
                        val_str = f'${val:,.2f}'
                    elif col == 'PORCENTAJE_EJECUCION' or 'PORCENTAJE' in str(col).upper() or '%' in str(col):
                        val_str = f'{val:,.2f}%'
                    else:
                        val_str = f'{val:,.2f}'
                    row_data.append(Paragraph(val_str, style_td_num))
                else:
                    val_str = str(val)
                    # use style_td (which is left-aligned) for text
                    row_data.append(Paragraph(val_str, style_td))
            rows.append(row_data)
        
        # Determine column widths roughly
        # Total width is ~500 for portrait, ~700 for landscape
        # We will let ReportLab auto-size, but adding repeatRows=1 is crucial
        t = Table(rows, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_primary),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        return t

    style_td_num_bold = ParagraphStyle(
        'TableCellNumBold',
        parent=style_td_num,
        fontName='Helvetica-Bold'
    )

    story = []
    current_orientation = "portrait"
    
    # Dynamic orientation helper to insert correct PageBreaks and NextPageTemplates
    def agregar_pagina_con_orientacion(target_orientation):
        nonlocal current_orientation
        if story:
            story.append(NextPageTemplate(target_orientation))
            current_orientation = target_orientation
            story.append(PageBreak())
    
    # PAGE 1: COVER PAGE
    story.append(Spacer(1, 20))
    story.append(Paragraph("REPORTE MAESTRO DE CONTROL DE OBRA", style_title))
    story.append(Paragraph("Sistema de Administración Delegada — DI MATTEO DESIGN-DIMAQUINAS C.A.", style_subtitle))
    
    # Metadata Box
    metadata_data = [
        [Paragraph("<b>Empresa:</b>", style_body), Paragraph(empresa_nombre, style_body)],
        [Paragraph("<b>Proyecto:</b>", style_body), Paragraph(obra_nombre, style_body)],
        [Paragraph("<b>Auditor:</b>", style_body), Paragraph(usuario_actual, style_body)],
        [Paragraph("<b>Fecha de Reporte:</b>", style_body), Paragraph(datetime.datetime.now().strftime('%d/%m/%Y %I:%M %p'), style_body)]
    ]
    t_meta = Table(metadata_data, colWidths=[120, 384])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_light_bg),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 20))
    
    # Global KPIs Table
    df_gastos_base = df_app[df_app['CLASE'] == 'GASTO'].copy()
    df_ingresos = df_app[df_app['CLASE'] == 'INGRESO'].copy()
    
    # Calculate totals
    total_ingresos = df_ingresos['MONTO BASE USD'].sum()
    
    pct_admin_efectivo = df_gastos_base['% ADMIN'].copy()
    mask_cero_gastos = (pct_admin_efectivo == 0) | (pct_admin_efectivo.isna())
    pct_admin_efectivo.loc[mask_cero_gastos] = admin_pct
    
    df_gastos_base['HONORARIOS'] = df_gastos_base['MONTO BASE USD'] * (pct_admin_efectivo / 100.0)
    df_gastos_base['COSTO TOTAL'] = df_gastos_base['MONTO BASE USD'] + df_gastos_base['HONORARIOS']
    
    total_gastos_netos = df_gastos_base['MONTO BASE USD'].sum()
    total_honorarios = df_gastos_base['HONORARIOS'].sum()
    costo_total_obra = df_gastos_base['COSTO TOTAL'].sum()
    saldo_caja = total_ingresos - costo_total_obra
    
    df_deudas = df_gastos_base[df_gastos_base['ESTADO'] == 'PENDIENTE']
    total_deuda = df_deudas['COSTO TOTAL'].sum()
    
    story.append(Paragraph("Resumen Financiero Ejecutivo", style_h1))
    
    kpis_data = [
        [Paragraph("<b>Métrica Financiera</b>", style_body), Paragraph("<b>Monto (USD)</b>", style_body)],
        [Paragraph("🟢 Total Ingresos", style_body), Paragraph(f"${total_ingresos:,.2f}", style_body)],
        [Paragraph("🔨 Gastos Netos", style_body), Paragraph(f"${total_gastos_netos:,.2f}", style_body)],
        [Paragraph("💼 Administración Delegada (Honorarios)", style_body), Paragraph(f"${total_honorarios:,.2f}", style_body)],
        [Paragraph("🔴 Costo Total Obra (Egresos + Honorarios)", style_body), Paragraph(f"${costo_total_obra:,.2f}", style_body)],
        [Paragraph("🏦 Saldo Disponible en Caja", style_body), Paragraph(f"${saldo_caja:,.2f}", style_body)],
        [Paragraph("⚠️ Deudas por Pagar (Gastos Pendientes)", style_body), Paragraph(f"${total_deuda:,.2f}", style_body)]
    ]
    
    kpis_data_styled = []
    for r_idx, row in enumerate(kpis_data):
        row_styled = []
        for c_idx, cell in enumerate(row):
            if r_idx == 0:
                row_styled.append(Paragraph(f"<font color='white'>{cell.text}</font>", style_body))
            else:
                row_styled.append(cell)
        kpis_data_styled.append(row_styled)
        
    t_kpis = Table(kpis_data_styled, colWidths=[280, 224])
    t_kpis.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_primary),
        ('PADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_kpis)
    
    # ----------------------------------------------------
    # GRÁFICOS (TODOS EN ORIENTACIÓN HORIZONTAL / LANDSCAPE)
    # ----------------------------------------------------
    
    # 1. Gráfico de Flujo de Caja (General)
    if opciones_pdf.get("flujo_caja", True):
        fig_flow, ax_flow = plt.subplots(figsize=(10.0, 5.0))
        categories = ['Ingresos Totales', 'Costo Total Obra', 'Saldo en Caja']
        amounts = [total_ingresos, costo_total_obra, saldo_caja]
        colors_list = ['#10b981', '#ef4444', '#3b82f6']
        bars = ax_flow.bar(categories, amounts, color=colors_list, width=0.4)
        ax_flow.set_ylabel('Monto (USD)', fontsize=8.5)
        ax_flow.set_title('Flujo de Caja General (USD)', fontsize=11, fontweight='bold', pad=8)
        ax_flow.tick_params(axis='both', which='major', labelsize=8)
        for bar in bars:
            yval = bar.get_height()
            ax_flow.text(bar.get_x() + bar.get_width()/2, yval + (max(amounts)*0.01), f"${yval:,.2f}", ha='center', va='bottom', fontsize=8)
        plt.tight_layout()
        buf_flow = io.BytesIO()
        plt.savefig(buf_flow, format='png', dpi=150)
        plt.close(fig_flow)
        buf_flow.seek(0)
        img_flow = Image(buf_flow, width=640, height=320)
        
        agregar_pagina_con_orientacion("landscape")
        story.append(Paragraph("Distribución de Flujo de Caja", style_h1))
        story.append(Spacer(1, 10))
        story.append(img_flow)

    # 2. Gráfico por Tipo de Gasto (Donut)
    if opciones_pdf.get("tipo_gasto", True):
        img_tipo = generar_grafico_tipo_gasto(df_gastos_base)
        if img_tipo:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Egresos por Tipo de Gasto", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_tipo)
            
            df_tipo = df_gastos_base.groupby('TIPO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
            total_tipo = df_tipo['COSTO TOTAL'].sum()
            df_tipo['% DEL TOTAL'] = (df_tipo['COSTO TOTAL'] / total_tipo * 100) if total_tipo > 0 else 0
            df_tipo.loc['Total'] = ['TOTAL', total_tipo, 100.0]
            agregar_pagina_con_orientacion("portrait")
            story.append(Paragraph('Datos: Egresos por Tipo de Gasto', style_h1))
            story.append(Spacer(1, 5))
            story.append(df_to_pdf_table(df_tipo, style_th, style_td_num, c_primary))

    # Calculate budgets grouped for both PROGRESS bar chart and BUDGET ESTIMATES table
    if not df_gastos_base.empty:
        df_pres = df_gastos_base.copy()
        df_pres['CAPITULO'] = df_pres['CAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN CAPÍTULO')
        presupuestos_grouped = df_pres.groupby(['CAPITULO']).agg({'COSTO TOTAL': 'sum'}).reset_index().rename(columns={'COSTO TOTAL': 'MONTO EJECUTADO'})
    else:
        presupuestos_grouped = pd.DataFrame(columns=['CAPITULO', 'MONTO EJECUTADO'])
    
    presupuestos_estimados = st.session_state.get("presupuestos_estimados", {})
    presupuestos_grouped['MONTO ESTIMADO'] = presupuestos_grouped['CAPITULO'].map(lambda x: float(presupuestos_estimados.get(x, 0.0)))
    
    def calc_pct(row):
        est = row['MONTO ESTIMADO']
        ej = row['MONTO EJECUTADO']
        if est > 0:
            return min(max((ej / est) * 100, 0.0), 100.0)
        return 100.0 if ej > 0 else 100.0
    presupuestos_grouped['PORCENTAJE_EJECUCION'] = presupuestos_grouped.apply(calc_pct, axis=1)
    presupuestos_grouped['RESTANTE'] = presupuestos_grouped['MONTO ESTIMADO'] - presupuestos_grouped['MONTO EJECUTADO']

    # 3. Gráfico Progreso Presupuesto por Capítulo
    if opciones_pdf.get("progreso_cap", True):
        img_ejec_est = generar_grafico_ejec_vs_est(presupuestos_grouped)
        if img_ejec_est:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Progreso de Presupuesto por Capítulo", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_ejec_est)
            
            df_prog = presupuestos_grouped[['CAPITULO', 'MONTO EJECUTADO', 'MONTO ESTIMADO', 'PORCENTAJE_EJECUCION', 'RESTANTE']].copy()
            df_prog.loc['Total'] = ['TOTAL', df_prog['MONTO EJECUTADO'].sum(), df_prog['MONTO ESTIMADO'].sum(), 0.0, df_prog['RESTANTE'].sum()]
            agregar_pagina_con_orientacion("portrait")
            story.append(Paragraph('Datos: Progreso Presupuesto por Capítulo', style_h1))
            story.append(Spacer(1, 5))
            story.append(df_to_pdf_table(df_prog, style_th, style_td_num, c_primary))

    # 4. Gráfico Egresos por Capítulo Stacked
    if opciones_pdf.get("egresos_cap", True):
        img_cap_stacked = generar_grafico_cap_stacked_pdf(df_gastos_base)
        if img_cap_stacked:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Egresos por Capítulo (por Tipo de Gasto)", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_cap_stacked)
            
            df_cap = df_gastos_base.groupby('CAPITULO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
            total_cap = df_cap['COSTO TOTAL'].sum()
            df_cap['% DEL TOTAL'] = (df_cap['COSTO TOTAL'] / total_cap * 100) if total_cap > 0 else 0
            df_cap.loc['Total'] = ['TOTAL', total_cap, 100.0]
            agregar_pagina_con_orientacion("portrait")
            story.append(Paragraph('Datos: Egresos por Capítulo', style_h1))
            story.append(Spacer(1, 5))
            story.append(df_to_pdf_table(df_cap, style_th, style_td_num, c_primary))

    # 5. Gráfico Top 15 Sub-Capítulos Stacked
    if opciones_pdf.get("subcap", True):
        img_subcap_stacked = generar_grafico_subcap_stacked_pdf(df_gastos_base)
        if img_subcap_stacked:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Distribución por Sub-Capítulo", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_subcap_stacked)
            
            df_sub_full = df_gastos_base.groupby('SUBCAPITULO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
            total_sub = df_sub_full['COSTO TOTAL'].sum()
            df_sub = df_sub_full.head(15).copy()
            df_sub['% DEL TOTAL'] = (df_sub['COSTO TOTAL'] / total_sub * 100) if total_sub > 0 else 0
            df_sub.loc['Total Top 15'] = ['TOTAL TOP 15', df_sub['COSTO TOTAL'].sum(), df_sub['% DEL TOTAL'].sum()]
            agregar_pagina_con_orientacion("portrait")
            story.append(Paragraph('Datos: Top 15 Sub-Capítulos', style_h1))
            story.append(Spacer(1, 5))
            story.append(df_to_pdf_table(df_sub, style_th, style_td_num, c_primary))

    # 6. Gráfico Mapa de Árbol (Treemap)
    if opciones_pdf.get("treemap", True):
        img_treemap = generar_grafico_treemap_pdf(df_gastos_base)
        if img_treemap:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Relación Jerárquica: Mapa de Árbol", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_treemap)

    # 7. Gráfico Estructura Concéntrica (Sunburst)
    if opciones_pdf.get("sunburst", True):
        img_sunburst = generar_grafico_sunburst_pdf(df_gastos_base)
        if img_sunburst:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Estructura Concéntrica", style_h1))
            story.append(Spacer(1, 10))
            
            # Center the Sunburst image horizontally since it is square (325 width out of 684 frame)
            t_sun = Table([[img_sunburst]], colWidths=[684])
            t_sun.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t_sun)

    # 8. Gráfico de Contratos: Monto Ejecutado vs Pendiente
    df_contratos = df_gastos_base[df_gastos_base['TIPO'].isin(['CONTRATO', 'CONTRATISTA'])].copy()
    if opciones_pdf.get("contratos_graf", True):
        img_contratos_chart = generar_grafico_contratos(df_contratos)
        if img_contratos_chart:
            agregar_pagina_con_orientacion("landscape")
            story.append(Paragraph("Análisis de Contratos y Contratistas", style_h1))
            story.append(Spacer(1, 10))
            story.append(img_contratos_chart)

    # ----------------------------------------------------
    # TABLAS DE DETALLE (TODAS EN ORIENTACIÓN VERTICAL / PORTRAIT)
    # ----------------------------------------------------
    
    # 1. Tabla de Egresos
    if opciones_pdf.get("egresos_tabla", True):
        agregar_pagina_con_orientacion("portrait")
        story.append(Paragraph("Listado Detallado de Egresos (Gastos)", style_title))
        story.append(Spacer(1, 10))
        
        eg_headers = [
            Paragraph("<b>Fecha</b>", style_th),
            Paragraph("<b>Proveedor</b>", style_th),
            Paragraph("<b>Descripción</b>", style_th),
            Paragraph("<b>Moneda</b>", style_th),
            Paragraph("<b>Monto Orig.</b>", style_th),
            Paragraph("<b>Honorarios</b>", style_th),
            Paragraph("<b>Costo Total (USD)</b>", style_th),
            Paragraph("<b>Capítulo</b>", style_th)
        ]
        
        eg_rows = [eg_headers]
        df_gastos_sorted = df_gastos_base.sort_values('FECHA', ascending=False) if not df_gastos_base.empty else pd.DataFrame()
        
        sum_orig_eg = 0.0
        sum_hono_eg = 0.0
        sum_tot_eg = 0.0
        
        if not df_gastos_sorted.empty:
            for idx, row in df_gastos_sorted.iterrows():
                f_str = row['FECHA'].strftime('%d/%m/%Y') if not pd.isnull(row['FECHA']) else ''
                prov = str(row['PROVEEDOR'])
                desc = str(row['DESCRIPCION'])
                mon = str(row['MONEDA'])
                m_orig = float(row['MONTO ORIG'])
                hono = float(row['HONORARIOS'])
                cost_tot = float(row['COSTO TOTAL'])
                cap = str(row['CAPITULO'])
                
                sum_orig_eg += m_orig
                sum_hono_eg += hono
                sum_tot_eg += cost_tot
                
                if len(desc) > 35:
                    desc = desc[:32] + "..."
                if len(prov) > 18:
                    prov = prov[:15] + "..."
                if len(cap) > 15:
                    cap = cap[:12] + "..."
                    
                eg_rows.append([
                    Paragraph(f_str, style_td),
                    Paragraph(prov, style_td),
                    Paragraph(desc, style_td),
                    Paragraph(mon, style_td),
                    Paragraph(f"{m_orig:,.2f}", style_td_num),
                    Paragraph(f"${hono:,.2f}", style_td_num),
                    Paragraph(f"${cost_tot:,.2f}", style_td_num),
                    Paragraph(cap, style_td)
                ])
        
        # Agregar fila de TOTAL
        eg_rows.append([
            Paragraph("<b>TOTAL EGRESOS</b>", style_td_bold),
            Paragraph("", style_td),
            Paragraph("", style_td),
            Paragraph("", style_td),
            Paragraph(f"<b>{sum_orig_eg:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_hono_eg:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_tot_eg:,.2f}</b>", style_td_num_bold),
            Paragraph("", style_td)
        ])
                
        t_egresos = Table(eg_rows, colWidths=[55, 75, 100, 50, 55, 55, 60, 54], repeatRows=1)
        t_egresos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_primary),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_light_bg]), # Evitar pisar el totalizador
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f1f5f9")), # Fila totalizadora
            ('LINEABOVE', (0,-1), (-1,-1), 1.0, c_primary), # Divisor superior del total
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_egresos)

    # 2. Tabla de Ingresos
    if opciones_pdf.get("ingresos_tabla", True):
        agregar_pagina_con_orientacion("portrait")
        story.append(Paragraph("Listado Detallado de Ingresos", style_title))
        story.append(Spacer(1, 10))
        
        in_headers = [
            Paragraph("<b>Fecha</b>", style_th),
            Paragraph("<b>Pagador</b>", style_th),
            Paragraph("<b>Descripción</b>", style_th),
            Paragraph("<b>Moneda</b>", style_th),
            Paragraph("<b>Monto Orig.</b>", style_th),
            Paragraph("<b>Monto (USD)</b>", style_th),
            Paragraph("<b>Forma de Pago</b>", style_th)
        ]
        
        in_rows = [in_headers]
        df_ingresos_sorted = df_ingresos.sort_values('FECHA', ascending=False) if not df_ingresos.empty else pd.DataFrame()
        
        sum_orig_in = 0.0
        sum_usd_in = 0.0
        
        if not df_ingresos_sorted.empty:
            for idx, row in df_ingresos_sorted.iterrows():
                f_str = row['FECHA'].strftime('%d/%m/%Y') if not pd.isnull(row['FECHA']) else ''
                prov = str(row['PROVEEDOR'])
                desc = str(row['DESCRIPCION'])
                mon = str(row['MONEDA'])
                m_orig = float(row['MONTO ORIG'])
                m_usd = float(row['MONTO BASE USD'])
                fp = str(row['FORMA PAGO'])
                
                sum_orig_in += m_orig
                sum_usd_in += m_usd
                
                if len(desc) > 40:
                    desc = desc[:37] + "..."
                if len(prov) > 20:
                    prov = prov[:17] + "..."
                    
                in_rows.append([
                    Paragraph(f_str, style_td),
                    Paragraph(prov, style_td),
                    Paragraph(desc, style_td),
                    Paragraph(mon, style_td),
                    Paragraph(f"{m_orig:,.2f}", style_td_num),
                    Paragraph(f"${m_usd:,.2f}", style_td_num),
                    Paragraph(fp, style_td)
                ])
                
        # Agregar fila de TOTAL
        in_rows.append([
            Paragraph("<b>TOTAL INGRESOS</b>", style_td_bold),
            Paragraph("", style_td),
            Paragraph("", style_td),
            Paragraph("", style_td),
            Paragraph(f"<b>{sum_orig_in:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_usd_in:,.2f}</b>", style_td_num_bold),
            Paragraph("", style_td)
        ])
                
        t_ingresos = Table(in_rows, colWidths=[50, 75, 109, 50, 65, 65, 90], repeatRows=1)
        t_ingresos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_primary),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_light_bg]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f1f5f9")),
            ('LINEABOVE', (0,-1), (-1,-1), 1.0, c_primary),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_ingresos)

    # 3. Tabla de Contratos
    if opciones_pdf.get("contratos_tabla", True):
        agregar_pagina_con_orientacion("portrait")
        story.append(Paragraph("Resumen Consolidado de Contratos", style_title))
        story.append(Spacer(1, 10))
        
        con_headers = [
            Paragraph("<b>Subcontratista</b>", style_th),
            Paragraph("<b>Monto Contratado (USD)</b>", style_th),
            Paragraph("<b>Monto Ejecutado (USD)</b>", style_th),
            Paragraph("<b>Saldo Pendiente (USD)</b>", style_th),
            Paragraph("<b>% Ejecución</b>", style_th)
        ]
        con_rows = [con_headers]
        
        sum_tot_con = 0.0
        sum_pag_con = 0.0
        sum_sal_con = 0.0
        
        if not df_contratos.empty:
            contratos_grouped = df_contratos.groupby('PROVEEDOR').agg({
                'COSTO TOTAL': 'sum',
                'MONTO PAGADO': 'sum'
            }).reset_index()
            contratos_grouped['SALDO CONTRATO'] = contratos_grouped['COSTO TOTAL'] - contratos_grouped['MONTO PAGADO']
            contratos_grouped['% EJECUCIÓN'] = (contratos_grouped['MONTO PAGADO'] / contratos_grouped['COSTO TOTAL'] * 100.0).fillna(0.0)
            
            for idx, row in contratos_grouped.iterrows():
                prov = str(row['PROVEEDOR'])
                c_tot = float(row['COSTO TOTAL'])
                c_pag = float(row['MONTO PAGADO'])
                c_sal = float(row['SALDO CONTRATO'])
                pct_ej = float(row['% EJECUCIÓN'])
                
                sum_tot_con += c_tot
                sum_pag_con += c_pag
                sum_sal_con += c_sal
                
                con_rows.append([
                    Paragraph(prov, style_td),
                    Paragraph(f"${c_tot:,.2f}", style_td_num),
                    Paragraph(f"${c_pag:,.2f}", style_td_num),
                    Paragraph(f"${c_sal:,.2f}", style_td_num),
                    Paragraph(f"{pct_ej:.1f}%", style_td_num)
                ])
                
        # Agregar fila de TOTAL
        avg_pct_con = (sum_pag_con / sum_tot_con * 100.0) if sum_tot_con > 0 else 0.0
        con_rows.append([
            Paragraph("<b>TOTAL CONTRATOS</b>", style_td_bold),
            Paragraph(f"<b>${sum_tot_con:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_pag_con:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_sal_con:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>{avg_pct_con:.1f}%</b>", style_td_num_bold)
        ])
                
        t_contratos = Table(con_rows, colWidths=[140, 95, 95, 95, 79], repeatRows=1)
        t_contratos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_primary),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_light_bg]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f1f5f9")),
            ('LINEABOVE', (0,-1), (-1,-1), 1.0, c_primary),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_contratos)

    # 4. Tabla de Comparativa de Presupuesto Estimado
    if opciones_pdf.get("presupuestos_tabla", True):
        agregar_pagina_con_orientacion("portrait")
        story.append(Paragraph("Comparativa de Presupuesto Estimado", style_title))
        story.append(Spacer(1, 10))
        
        pres_headers = [
            Paragraph("<b>Capítulo</b>", style_th),
            Paragraph("<b>Monto Ejecutado (USD)</b>", style_th),
            Paragraph("<b>Monto Estimado (USD)</b>", style_th),
            Paragraph("<b>% Ejecución</b>", style_th),
            Paragraph("<b>Restante / Desviación (USD)</b>", style_th)
        ]
        pres_rows = [pres_headers]
        
        sum_ej_pres = 0.0
        sum_est_pres = 0.0
        sum_rest_pres = 0.0
        
        if not presupuestos_grouped.empty:
            for idx, row in presupuestos_grouped.iterrows():
                cap = str(row['CAPITULO'])
                ej = float(row['MONTO EJECUTADO'])
                est = float(row['MONTO ESTIMADO'])
                pct = float(row['PORCENTAJE_EJECUCION'])
                rest = float(row['RESTANTE'])
                
                sum_ej_pres += ej
                sum_est_pres += est
                sum_rest_pres += rest
                
                pres_rows.append([
                    Paragraph(cap, style_td),
                    Paragraph(f"${ej:,.2f}", style_td_num),
                    Paragraph(f"${est:,.2f}", style_td_num),
                    Paragraph(f"{pct:.1f}%", style_td_num),
                    Paragraph(f"${rest:,.2f}", style_td_num)
                ])
                
        # Agregar fila de TOTAL
        avg_pct_pres = (sum_ej_pres / sum_est_pres * 100.0) if sum_est_pres > 0 else 0.0
        pres_rows.append([
            Paragraph("<b>TOTAL PRESUPUESTO</b>", style_td_bold),
            Paragraph(f"<b>${sum_ej_pres:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_est_pres:,.2f}</b>", style_td_num_bold),
            Paragraph(f"<b>{avg_pct_pres:.1f}%</b>", style_td_num_bold),
            Paragraph(f"<b>${sum_rest_pres:,.2f}</b>", style_td_num_bold)
        ])
                
        t_pres = Table(pres_rows, colWidths=[140, 95, 95, 79, 95], repeatRows=1)
        t_pres.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), c_primary),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, c_light_bg]),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#f1f5f9")),
            ('LINEABOVE', (0,-1), (-1,-1), 1.0, c_primary),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_pres)
        
    doc.build(story, canvasmaker=NumberedCanvas)
    buf.seek(0)
    return buf.getvalue()

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Dashboard DI MATTEO DESIGN-DIMAQUINAS - Control de Obra",
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
if 'area_m2' not in st.session_state:
    st.session_state.area_m2 = 0.0
if 'presupuestos_estimados' not in st.session_state:
    st.session_state.presupuestos_estimados = {}
if 'areas_estimadas_capitulos' not in st.session_state:
    st.session_state.areas_estimadas_capitulos = {}
if 'reset_counter_presupuestos' not in st.session_state:
    st.session_state.reset_counter_presupuestos = 0
if 'confirmar_borrado_auditoria' not in st.session_state:
    st.session_state.confirmar_borrado_auditoria = False
if 'login_audit_pendiente' not in st.session_state:
    st.session_state.login_audit_pendiente = False

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
            "columnas_visibles_ingresos": st.session_state.get("columnas_visibles_ingresos"),
            "area_m2": st.session_state.get("area_m2", 0.0),
            "presupuestos_estimados": st.session_state.get("presupuestos_estimados", {}),
            "areas_estimadas_capitulos": st.session_state.get("areas_estimadas_capitulos", {})
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
            # st.session_state.usuario_actual = meta.get("usuario_actual")  # Evitar auto-login para control de acceso
            st.session_state.empresa_nombre = meta.get("empresa_nombre")
            st.session_state.obra_nombre = meta.get("obra_nombre")
            if "admin_pct_global" in meta:
                st.session_state.admin_pct_global = meta.get("admin_pct_global")
            if "columnas_visibles_gastos" in meta:
                st.session_state.columnas_visibles_gastos = meta.get("columnas_visibles_gastos")
            if "columnas_visibles_ingresos" in meta:
                st.session_state.columnas_visibles_ingresos = meta.get("columnas_visibles_ingresos")
            st.session_state.area_m2 = meta.get("area_m2", 0.0)
            st.session_state.presupuestos_estimados = meta.get("presupuestos_estimados", {})
            st.session_state.areas_estimadas_capitulos = meta.get("areas_estimadas_capitulos", {})
            
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

def registrar_auditoria(accion, detalles):
    if st.session_state.df_maestro is None:
        return
    usuario = st.session_state.usuario_actual if st.session_state.usuario_actual else "SISTEMA"
    nuevo_log = {
        'CLASE': 'AUDITORIA',
        'FECHA': pd.Timestamp.now(),
        'PROVEEDOR': usuario.upper(),
        'TIPO': accion.upper(),
        'DESCRIPCION': detalles.upper(),
        'MONEDA': 'USD',
        'TASA': 1.0,
        'MONTO ORIG': 0.0,
        'MONTO BASE USD': 0.0,
        'MONTO PAGADO': 0.0,
        'HONORARIOS': 0.0,
        'COSTO TOTAL': 0.0,
        'ESTADO': 'PAGADO',
        '% ADMIN': 0.0,
        'CAPITULO': '',
        'SUBCAPITULO': '',
        'LINK FACTURA': '',
        'LINK COMPROBANTE': ''
    }
    df_nuevo = pd.DataFrame([nuevo_log])
    st.session_state.df_maestro = pd.concat([st.session_state.df_maestro, df_nuevo], ignore_index=True)
    guardar_cache_local()

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
    cambios_desc = []
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        cambios_desc.append(f"Eliminó {len(indices_eliminados)} registros")
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        modificados_count = 0
        for idx in indices_comunes:
            orig_row = df_original_filtrado.loc[idx]
            edit_row = df_editado_filtrado.loc[idx]
            if not orig_row.equals(edit_row):
                modificados_count += 1
        if modificados_count > 0:
            cambios_desc.append(f"Modificó {modificados_count} registros")
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
        cambios_desc.append(f"Añadió {len(indices_nuevos)} nuevos registros")
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        if cambios_desc:
            registrar_auditoria("EDITOR MAESTRO", " | ".join(cambios_desc))
        else:
            guardar_cache_local()

def guardar_cambios_filtrados(df_original_filtrado, df_editado_filtrado, clase_default):
    df_maestro = st.session_state.df_maestro.copy()
    global_admin = st.session_state.get('admin_pct_global', 15.0)
    cambios_desc = []
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        cambios_desc.append(f"Eliminó {len(indices_eliminados)} registros")
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        modificados_count = 0
        for idx in indices_comunes:
            orig_row = df_original_filtrado.loc[idx]
            edit_row = df_editado_filtrado.loc[idx]
            if not orig_row.equals(edit_row):
                modificados_count += 1
        if modificados_count > 0:
            cambios_desc.append(f"Modificó {modificados_count} registros")
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
        cambios_desc.append(f"Añadió {len(indices_nuevos)} nuevos registros")
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Procesar y recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        if cambios_desc:
            registrar_auditoria(f"EDICIÓN {clase_default}S", " | ".join(cambios_desc))
        else:
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
        df_copy['FECHA'] = pd.to_datetime(df_copy['FECHA'], errors='coerce')
        df_copy['FECHA_STR'] = df_copy['FECHA'].dt.strftime('%Y-%m-%d').fillna('')
    else:
        df_copy['FECHA_STR'] = ''
        
    # Agrupar por fecha, proveedor, descripción limpia, tipo, moneda, tasa, estado, forma pago y subcapítulo
    group_cols = ['FECHA_STR', 'PROVEEDOR', 'DESCRIPCION_LIMPIA', 'TIPO', 'MONEDA', 'TASA', 'ESTADO', 'FORMA PAGO', 'SUBCAPITULO']
    
    # Rellenar nulos temporalmente para evitar que groupby descarte filas
    for col in group_cols:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].fillna('')
            
    grouped_rows = []
    for keys, group in df_copy.groupby(group_cols, dropna=False):
        fecha_str, proveedor, desc_limpia, tipo, moneda, tasa, estado, forma_pago, subcap = keys
        
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
            'ORIGINAL_INDICES': list(group.index),
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
                if st.session_state.df_maestro is not None:
                    registrar_auditoria("INICIO DE SESIÓN", "Accedió al sistema.")
                else:
                    st.session_state.login_audit_pendiente = True
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
                
                # Procesar login de auditoría pendiente si lo hay
                if st.session_state.get('login_audit_pendiente', False):
                    registrar_auditoria("INICIO DE SESIÓN", "Accedió al sistema.")
                    st.session_state.login_audit_pendiente = False
                
                registrar_auditoria("CARGA CSV", f"Importó {len(df_procesado)} registros de la base de datos.")
                st.success("✅ Base de datos cargada correctamente.")
                st.rerun()
                
        st.divider()
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem;'>O puedes comenzar con una base de datos en blanco</p>", unsafe_allow_html=True)
        if st.button("📄 Iniciar Base de Datos Vacía", use_container_width=True):
            # Crear estructura vacía
            columnas_base = ["CLASE","FECHA","PROVEEDOR","TIPO","CAPITULO","SUBCAPITULO","DESCRIPCION","MONEDA","TASA","MONTO ORIG","MONTO BASE USD","MONTO PAGADO","HONORARIOS","COSTO TOTAL","FORMA PAGO","LINK FACTURA","LINK COMPROBANTE","ESTADO", "% ADMIN"]
            df_vacio = pd.DataFrame(columns=columnas_base)
            st.session_state.df_maestro = procesar_csv(df_vacio)
            
            # Procesar login de auditoría pendiente si lo hay
            if st.session_state.get('login_audit_pendiente', False):
                registrar_auditoria("INICIO DE SESIÓN", "Accedió al sistema.")
                st.session_state.login_audit_pendiente = False
                
            registrar_auditoria("NUEVA BD", "Inició en blanco.")
            st.success("✅ Base de datos vacía iniciada con éxito.")
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

if st.sidebar.button("🔄 Cambiar de Proyecto / Cerrar Sesión", use_container_width=True):
    registrar_auditoria("CIERRE DE SESIÓN", "Bloqueó pantalla / Cambió de proyecto.")
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
        capitulo = "N/A"
        subcapitulo = "N/A"
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
            
            tasa = st.number_input("📈 Tasa de Cambio (Ref. BCV)", value=tasa_bcv, min_value=0.0, format="%.4f")
            estado = st.selectbox("✅ Estado", ["PAGADO", "PENDIENTE"])
            forma_pago = st.selectbox("💳 Forma de Pago", ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"])
            admin_pct = st.number_input("💼 % Administración Delegada", value=float(admin_global_val), step=0.5)
            
        st.markdown("---")
        distribuir_gasto = st.checkbox("🔀 Distribuir Gasto en Múltiples Capítulos / Sub-Capítulos", value=False)
        
        if distribuir_gasto:
            st.info("💡 Ingresa las fracciones correspondientes. La suma de los porcentajes debe ser exactamente **100%**.")
            df_distribucion_init = pd.DataFrame([
                {"Capítulo": "", "Sub-Capítulo": "", "Porcentaje (%)": 50.0},
                {"Capítulo": "", "Sub-Capítulo": "", "Porcentaje (%)": 50.0}
            ])
            opciones_cap = [c for c in lista_cap if "➕" not in c]
            opciones_sub = [s for s in lista_sub if "➕" not in s]
            
            df_distribucion = st.data_editor(
                df_distribucion_init,
                column_config={
                    "Capítulo": st.column_config.SelectboxColumn("Capítulo Destino", options=opciones_cap, required=True),
                    "Sub-Capítulo": st.column_config.SelectboxColumn("Sub-Capítulo Destino", options=opciones_sub, required=True),
                    "Porcentaje (%)": st.column_config.NumberColumn("Porcentaje (%)", min_value=0.0, max_value=100.0, step=1.0, required=True)
                },
                num_rows="dynamic",
                use_container_width=True,
                key="editor_distribucion_individual"
            )
            suma_pct_ind = df_distribucion["Porcentaje (%)"].sum()
            if suma_pct_ind != 100.0:
                st.error(f"⚠️ La suma de los porcentajes es {suma_pct_ind}%. Debe ser exactamente 100%.")
            else:
                st.success("✅ La distribución suma 100%.")
        else:
            col_cap1, col_cap2 = st.columns(2)
            with col_cap1:
                cap_sel = st.selectbox("🏗️ Capítulo", options=lista_cap)
                capitulo = st.text_input("✍️ Escriba el Nuevo Capítulo") if cap_sel == "➕ NUEVO CAPÍTULO" else cap_sel
            with col_cap2:
                sub_sel = st.selectbox("🧱 Sub-Capítulo", options=lista_sub)
                subcapitulo = st.text_input("✍️ Escriba el Nuevo Sub-Capítulo") if sub_sel == "➕ NUEVO SUB-CAPÍTULO" else sub_sel


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
        
        nuevos_registros = []
        
        if clase_registro == "GASTO" and distribuir_gasto:
            if suma_pct_ind != 100.0:
                st.error("No se puede guardar. Los porcentajes de distribución no suman 100%.")
                st.stop()
                
            for _, row in df_distribucion.iterrows():
                pct = row["Porcentaje (%)"] / 100.0
                if pct > 0:
                    reg = {
                        'CLASE': clase_registro,
                        'FECHA': pd.to_datetime(fecha_input),
                        'PROVEEDOR': proveedor.upper(),
                        'TIPO': tipo.upper(),
                        'CAPITULO': str(row["Capítulo"]).upper(),
                        'SUBCAPITULO': str(row["Sub-Capítulo"]).upper(),
                        'DESCRIPCION': descripcion.upper(),
                        'MONEDA': moneda,
                        'TASA': tasa,
                        'MONTO ORIG': monto * pct,
                        'MONTO BASE USD': monto_base_usd * pct,
                        'MONTO PAGADO': (monto_base_usd * pct) if estado == 'PAGADO' else 0,
                        'HONORARIOS': honorarios * pct,
                        'COSTO TOTAL': costo_total * pct,
                        'ESTADO': estado,
                        '% ADMIN': admin_pct
                    }
                    nuevos_registros.append(reg)
            registrar_auditoria(clase_registro, f"Añadió gasto dividido ($ {monto:,.2f} {moneda}) a {proveedor.upper()} en {len(nuevos_registros)} partes")
        else:
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
            nuevos_registros.append(nuevo_registro)
            registrar_auditoria(clase_registro, f"Añadió {clase_registro.lower()} de $ {monto:,.2f} {moneda} ($ {monto_base_usd:,.2f} USD) a {proveedor.upper()}")
            
        df_nuevo = pd.DataFrame(nuevos_registros)
        st.session_state.df_maestro = pd.concat([df_actual, df_nuevo], ignore_index=True)
        st.success("✅ Registro guardado con éxito.")
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

df_gastos_base['FECHA'] = pd.to_datetime(df_gastos_base['FECHA'], errors='coerce')
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

tab_graficos, tab_datos_graficos, tab_egresos, tab_distribucion, tab_ingresos, tab_deudas, tab_contratos, tab_presupuestos, tab_editor, tab_auditoria = st.tabs([
    "📊 GRÁFICOS", "📈 DATOS GRÁFICOS", "💸 EGRESOS", "🔀 DISTRIBUCIÓN MASIVA", "💰 INGRESOS", "🔴 DEUDAS", "📄 CONTRATOS", "🎯 PRESUPUESTOS", "🛠️ EDITOR MAESTRO", "📜 AUDITORÍA"
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
        st.info("💡 **VISTA DE REVISIÓN AGRUPADA:** Puedes editar Fecha, Proveedor, Descripción, Estado y Forma de Pago (los cambios se aplicarán a todas sus fracciones). Selecciona la casilla izquierda para Eliminar el grupo completo.")
        df_gastos_grouped = agrupar_gastos_divididos(df_gastos_sort)
        df_gastos_grouped.insert(0, "Seleccionar", False)
        
        cols_mostrar_grouped = ['Seleccionar', 'FECHA', 'PROVEEDOR', 'DESCRIPCION', 'MONEDA', 'TASA', 'MONTO ORIG', 'MONTO BASE USD', 'HONORARIOS', 'COSTO TOTAL', 'ESTADO', 'FORMA PAGO', 'TIPO', 'CAPITULO', 'SUBCAPITULO']
        
        # Necesitamos obtener listas dinámicas para selects igual que en la normal
        fp_gastos = sorted(list(set([str(fp).strip().upper() for fp in st.session_state.df_maestro['FORMA PAGO'].unique() if str(fp).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        for fp in ["TRANSFERENCIA", "EFECTIVO", "ZELLE", "OTRO"]:
            if fp not in fp_gastos:
                fp_gastos.append(fp)
                
        estados_gastos = sorted(list(set([str(e).strip().upper() for e in st.session_state.df_maestro['ESTADO'].unique() if str(e).strip() not in ['', 'NAN', 'NaN', 'None', 'NONE']])))
        for e in ["PAGADO", "PENDIENTE"]:
            if e not in estados_gastos:
                estados_gastos.append(e)

        df_gastos_grouped_edit = st.data_editor(
            df_gastos_grouped[cols_mostrar_grouped],
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Eliminar", default=False),
                "FECHA": st.column_config.DateColumn("📅 Fecha"),
                "PROVEEDOR": st.column_config.TextColumn("🏢 Proveedor"),
                "DESCRIPCION": st.column_config.TextColumn("📝 Descripción"),
                "ESTADO": st.column_config.SelectboxColumn("✅ Estado", options=estados_gastos),
                "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_gastos),
                "MONTO ORIG": st.column_config.NumberColumn("💰 Monto Orig.", format="%.2f", disabled=True),
                "MONEDA": st.column_config.TextColumn("Moneda", disabled=True),
                "TASA": st.column_config.NumberColumn("Tasa", format="%.4f", disabled=True),
                "MONTO BASE USD": st.column_config.NumberColumn("Monto Base USD", format="$%.2f", disabled=True),
                "HONORARIOS": st.column_config.NumberColumn("Honorarios", format="$%.2f", disabled=True),
                "COSTO TOTAL": st.column_config.NumberColumn("Costo Total", format="$%.2f", disabled=True),
                "TIPO": st.column_config.TextColumn("Tipo", disabled=True),
                "CAPITULO": st.column_config.TextColumn("Capítulo", disabled=True),
                "SUBCAPITULO": st.column_config.TextColumn("Sub-Capítulo", disabled=True),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
            key="editor_grouped"
        )
        
        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            if st.button("💾 Guardar Cambios Editados", type="primary", use_container_width=True):
                df_maestro_new = st.session_state.df_maestro.copy()
                cambios = 0
                for idx in df_gastos_grouped.index:
                    orig_row = df_gastos_grouped.loc[idx]
                    edit_row = df_gastos_grouped_edit.loc[idx]
                    
                    cambio_detectado = False
                    for col in ["FECHA", "PROVEEDOR", "DESCRIPCION", "ESTADO", "FORMA PAGO"]:
                        # Convert to string to compare safely due to NaT/NaN issues
                        if str(orig_row[col]) != str(edit_row[col]):
                            cambio_detectado = True
                            
                    if cambio_detectado:
                        orig_indices = orig_row['ORIGINAL_INDICES']
                        for o_idx in orig_indices:
                            for col in ["FECHA", "PROVEEDOR", "DESCRIPCION", "ESTADO", "FORMA PAGO"]:
                                if col == "FECHA":
                                    df_maestro_new.at[o_idx, col] = pd.to_datetime(edit_row[col])
                                else:
                                    df_maestro_new.at[o_idx, col] = str(edit_row[col]).upper() if pd.notnull(edit_row[col]) else ''
                        cambios += 1
                        
                if cambios > 0:
                    st.session_state.df_maestro = df_maestro_new
                    registrar_auditoria("GASTO", f"Actualizó {cambios} grupos de gastos divididos")
                    guardar_cache_local()
                    st.success(f"✅ Se actualizaron {cambios} grupos de gastos.")
                    st.rerun()
                else:
                    st.warning("No se detectaron cambios en los textos editables.")
                    
        with col_g2:
            seleccionados_idx = df_gastos_grouped_edit[df_gastos_grouped_edit["Seleccionar"] == True].index
            if len(seleccionados_idx) > 0:
                if st.button(f"🗑️ Eliminar {len(seleccionados_idx)} Gasto(s) Seleccionado(s)", type="primary", use_container_width=True):
                    df_maestro_new = st.session_state.df_maestro.copy()
                    indices_a_eliminar = []
                    for idx in seleccionados_idx:
                        indices_a_eliminar.extend(df_gastos_grouped.loc[idx]['ORIGINAL_INDICES'])
                    
                    df_maestro_new = df_maestro_new.drop(index=indices_a_eliminar)
                    st.session_state.df_maestro = df_maestro_new
                    registrar_auditoria("GASTO", f"Eliminó {len(seleccionados_idx)} grupos consolidados ({len(indices_a_eliminar)} fracciones internas)")
                    guardar_cache_local()
                    st.success(f"✅ Se eliminaron {len(seleccionados_idx)} grupos ({len(indices_a_eliminar)} fracciones).")
                    st.rerun()
            else:
                st.button("🗑️ Selecciona la casilla para Eliminar", disabled=True, use_container_width=True)
                
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

        lista_cap_edit = sorted(list(set([str(c).strip() for c in st.session_state.df_maestro['CAPITULO'].unique() if str(c).strip() not in ['', 'NAN', 'NaN']])))
        lista_sub_edit = sorted(list(set([str(s).strip() for s in st.session_state.df_maestro['SUBCAPITULO'].unique() if str(s).strip() not in ['', 'NAN', 'NaN']])))

        column_config_gastos = {
            "FECHA": st.column_config.DateColumn("📅 Fecha"),
            "MONEDA": st.column_config.SelectboxColumn("💵 Moneda", options=monedas_gastos, required=True),
            "TASA": st.column_config.NumberColumn("📈 Tasa", format="%.4f", min_value=0.0),
            "MONTO ORIG": st.column_config.NumberColumn("💰 Monto Orig.", format="%.2f", min_value=0.0, disabled=True),
            "% DISTRIBUCIÓN": st.column_config.NumberColumn("📊 % Distribución", format="%g%%", min_value=0.0, max_value=100.0, step=0.1),
            "% ADMIN": st.column_config.NumberColumn("💼 % Admin", format="%.2f", min_value=0.0),
            "HONORARIOS": st.column_config.NumberColumn("💼 Honorarios (USD)", format="$%.2f", disabled=True),
            "COSTO TOTAL": st.column_config.NumberColumn("🔴 Costo Total (USD)", format="$%.2f", disabled=True),
            "ESTADO": st.column_config.SelectboxColumn("✅ Estado", options=estados_gastos, required=True),
            "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_gastos, required=True),
            "CAPITULO": st.column_config.SelectboxColumn("🏗️ Capítulo", options=lista_cap_edit, required=True),
            "SUBCAPITULO": st.column_config.SelectboxColumn("🧱 Sub-Capítulo", options=lista_sub_edit, required=True),
        }
        import re
        def get_group_key(row):
            desc = str(row.get('DESCRIPCION', ''))
            desc_limpia = re.sub(r' \(\d+(\.\d+)?\%\)$', '', desc).strip().upper()
            return f"{row.get('FECHA', '')}_{row.get('PROVEEDOR', '')}_{desc_limpia}_{row.get('TIPO', '')}_{row.get('MONEDA', '')}_{row.get('TASA', '')}_{row.get('ESTADO', '')}_{row.get('FORMA PAGO', '')}_{row.get('SUBCAPITULO', '')}"

        if not df_gastos.empty:
            df_gastos['GROUP_KEY'] = df_gastos.apply(get_group_key, axis=1)
            group_totals = df_gastos.groupby('GROUP_KEY')['MONTO ORIG'].sum().to_dict()
        else:
            group_totals = {}

        if not df_gastos_sort.empty:
            df_gastos_sort['GROUP_KEY'] = df_gastos_sort.apply(get_group_key, axis=1)
            df_gastos_sort = df_gastos_sort.sort_values(by=['FECHA', 'GROUP_KEY'], ascending=[False, True])
            def calc_pct(row):
                total = group_totals.get(row['GROUP_KEY'], float(row['MONTO ORIG']))
                if total > 0:
                    return round((float(row['MONTO ORIG']) / total) * 100.0, 2)
                return 100.0
            df_gastos_sort['% DISTRIBUCIÓN'] = df_gastos_sort.apply(calc_pct, axis=1)
        else:
            df_gastos_sort['% DISTRIBUCIÓN'] = pd.Series(dtype='float64')

        if '% DISTRIBUCIÓN' not in cols_mostrar_gastos:
            idx_monto = cols_mostrar_gastos.index('MONTO ORIG') if 'MONTO ORIG' in cols_mostrar_gastos else len(cols_mostrar_gastos)
            cols_mostrar_gastos.insert(idx_monto + 1, '% DISTRIBUCIÓN')

        for col in cols_mostrar_gastos:
            if col not in st.session_state.columnas_visibles_gastos and col != '% DISTRIBUCIÓN':
                column_config_gastos[col] = None

        orden_columnas = st.session_state.columnas_visibles_gastos.copy()
        if '% DISTRIBUCIÓN' not in orden_columnas:
            if 'MONTO ORIG' in orden_columnas:
                idx = orden_columnas.index('MONTO ORIG')
                orden_columnas.insert(idx + 1, '% DISTRIBUCIÓN')
            else:
                orden_columnas.append('% DISTRIBUCIÓN')

        df_gastos_editado = st.data_editor(
            df_gastos_sort[cols_mostrar_gastos],
            num_rows="dynamic",
            use_container_width=True,
            height=400,
            disabled=['HONORARIOS', 'COSTO TOTAL'],
            column_order=orden_columnas,
            column_config=column_config_gastos,
            key=f"editor_gastos_{st.session_state.reset_counter_gastos}"
        )
        
        col_save_g = st.columns([1, 1])
        with col_save_g[0]:
            if st.button("💾 Guardar Cambios de Egresos", type="primary", use_container_width=True):
                # Validar y procesar cambios en % DISTRIBUCIÓN
                filas_cambiadas_pct = {}
                for idx in df_gastos_editado.index:
                    if idx in df_gastos_sort.index:
                        old_pct = df_gastos_sort.loc[idx, '% DISTRIBUCIÓN']
                        new_pct = df_gastos_editado.loc[idx, '% DISTRIBUCIÓN']
                        if pd.notnull(old_pct) and pd.notnull(new_pct) and abs(float(old_pct) - float(new_pct)) > 0.01:
                            filas_cambiadas_pct[idx] = float(new_pct)
                
                if filas_cambiadas_pct:
                    grupos_afectados = set([df_gastos_sort.loc[idx, 'GROUP_KEY'] for idx in filas_cambiadas_pct.keys()])
                    errores = []
                    
                    for g_key in grupos_afectados:
                        indices_grupo = df_gastos[df_gastos['GROUP_KEY'] == g_key].index
                        suma_pct = 0.0
                        for idx in indices_grupo:
                            if idx in filas_cambiadas_pct:
                                suma_pct += filas_cambiadas_pct[idx]
                            else:
                                row = df_gastos.loc[idx]
                                total = group_totals.get(g_key, float(row['MONTO ORIG']))
                                pct = round((float(row['MONTO ORIG']) / total) * 100.0, 2) if total > 0 else 100.0
                                suma_pct += pct
                                
                        if abs(suma_pct - 100.0) > 0.05:
                            errores.append(f"El grupo con fecha {g_key.split('_')[0]} suma {suma_pct:.1f}%.")
                            
                    if errores:
                        st.error("⚠️ **Error de Distribución:** No se puede guardar. La suma de los porcentajes debe ser exactamente 100% para cada gasto dividido. Asegúrate de tener a la vista (filtrados) todas las partes del gasto que deseas modificar.\n" + "\n".join(errores))
                        st.stop()
                        
                    for idx, new_pct in filas_cambiadas_pct.items():
                        g_key = df_gastos_sort.loc[idx, 'GROUP_KEY']
                        total = group_totals.get(g_key, 0.0)
                        nuevo_monto = total * (new_pct / 100.0)
                        
                        df_gastos_editado.loc[idx, 'MONTO ORIG'] = nuevo_monto
                        tasa = float(df_gastos_editado.loc[idx, 'TASA'])
                        moneda = df_gastos_editado.loc[idx, 'MONEDA']
                        monto_base_usd = nuevo_monto / tasa if moneda != "USD" and tasa > 0 else nuevo_monto
                        df_gastos_editado.loc[idx, 'MONTO BASE USD'] = monto_base_usd
                        
                        admin = float(df_gastos_editado.loc[idx, '% ADMIN'])
                        honorarios = monto_base_usd * (admin / 100.0)
                        df_gastos_editado.loc[idx, 'HONORARIOS'] = honorarios
                        df_gastos_editado.loc[idx, 'COSTO TOTAL'] = monto_base_usd + honorarios
                        
                        desc = str(df_gastos_editado.loc[idx, 'DESCRIPCION'])
                        import re
                        desc_limpia = re.sub(r' \(\d+(\.\d+)?\%\)$', '', desc).strip()
                        df_gastos_editado.loc[idx, 'DESCRIPCION'] = f"{desc_limpia} ({new_pct:g}%)"

                guardar_cambios_filtrados(df_gastos_sort[cols_mostrar_gastos], df_gastos_editado, clase_default="GASTO")
                st.success("✅ Egresos actualizados con éxito.")
                st.rerun()
        with col_save_g[1]:
            if st.button("👁️ Mostrar Columnas Ocultas / Restablecer Vista", use_container_width=True, key="reset_egresos"):
                st.session_state.reset_counter_gastos += 1
                st.rerun()


with tab_distribucion:
    st.markdown("### 🔀 Herramienta de Distribución Masiva (Porcentajes)")
    st.info("Selecciona los egresos a los que deseas aplicarles una regla de distribución masiva. Ideal para facturas generales o compras de materiales combinados ingresados recientemente.")
    
    df_gastos_dist = df_gastos.copy()
    if not df_gastos_dist.empty:
        df_gastos_dist.insert(0, "Seleccionar", False)
        
        st.markdown("#### 1. Egresos Disponibles")
        cols_mostrar_dist = ["Seleccionar", "FECHA", "PROVEEDOR", "DESCRIPCION", "MONTO ORIG", "MONEDA", "COSTO TOTAL", "CAPITULO", "SUBCAPITULO"]
        
        # Keep only the columns that exist to avoid KeyError
        cols_existentes = [c for c in cols_mostrar_dist if c in df_gastos_dist.columns]
        
        edited_dist_df = st.data_editor(
            df_gastos_dist[cols_existentes].sort_values('FECHA', ascending=False),
            column_config={
                "Seleccionar": st.column_config.CheckboxColumn("Seleccionar", default=False),
                "FECHA": st.column_config.DateColumn("Fecha", disabled=True),
                "PROVEEDOR": st.column_config.TextColumn("Proveedor", disabled=True),
                "DESCRIPCION": st.column_config.TextColumn("Descripción", disabled=True),
                "MONTO ORIG": st.column_config.NumberColumn("Monto Orig.", format="%.2f", disabled=True),
                "MONEDA": st.column_config.TextColumn("Moneda", disabled=True),
                "COSTO TOTAL": st.column_config.NumberColumn("Costo Total (USD)", format="%.2f", disabled=True),
                "CAPITULO": st.column_config.TextColumn("Capítulo Actual", disabled=True),
                "SUBCAPITULO": st.column_config.TextColumn("Sub-Capítulo Actual", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            key="editor_seleccionar_distribucion",
            height=300
        )
        
        # Filtramos los seleccionados
        seleccionados_idx = edited_dist_df[edited_dist_df["Seleccionar"] == True].index
        
        st.markdown("#### 2. Definir Regla de Porcentajes")
        st.write(f"Egresos seleccionados para distribuir: **{len(seleccionados_idx)}**")
        
        lista_cap_dist = sorted(list(set([str(c).strip() for c in st.session_state.df_maestro['CAPITULO'].unique() if str(c).strip() not in ['', 'NAN', 'NaN']])))
        lista_sub_dist = sorted(list(set([str(s).strip() for s in st.session_state.df_maestro['SUBCAPITULO'].unique() if str(s).strip() not in ['', 'NAN', 'NaN']])))
        
        df_reglas_init = pd.DataFrame([
            {"Capítulo": "", "Sub-Capítulo": "", "Porcentaje (%)": 50.0},
            {"Capítulo": "", "Sub-Capítulo": "", "Porcentaje (%)": 50.0}
        ])
        
        df_reglas = st.data_editor(
            df_reglas_init,
            column_config={
                "Capítulo": st.column_config.SelectboxColumn("Capítulo Destino", options=lista_cap_dist, required=True),
                "Sub-Capítulo": st.column_config.SelectboxColumn("Sub-Capítulo Destino", options=lista_sub_dist, required=True),
                "Porcentaje (%)": st.column_config.NumberColumn("Porcentaje (%)", min_value=0.0, max_value=100.0, step=1.0, required=True)
            },
            num_rows="dynamic",
            use_container_width=True,
            key="editor_reglas_distribucion"
        )
        
        suma_pct = df_reglas["Porcentaje (%)"].sum()
        
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            if suma_pct == 100.0:
                st.success("✅ La suma de los porcentajes es exactamente 100%. Listo para grabar.")
            else:
                st.error(f"⚠️ La suma actual es {suma_pct}%. Debe ser exactamente 100% para poder grabar.")
                
        with col_btn2:
            if suma_pct == 100.0 and len(seleccionados_idx) > 0:
                if st.button("🔵 Grabar Distribución Masiva", type="primary", use_container_width=True):
                    nuevos_registros_masivos = []
                    df_actual = st.session_state.df_maestro
                    
                    for idx in seleccionados_idx:
                        fila_original = df_actual.loc[idx].copy()
                        for _, regla in df_reglas.iterrows():
                            pct = regla["Porcentaje (%)"] / 100.0
                            if pct > 0:
                                nueva_fila = fila_original.copy()
                                nueva_fila["CAPITULO"] = str(regla["Capítulo"]).upper()
                                nueva_fila["SUBCAPITULO"] = str(regla["Sub-Capítulo"]).upper()
                                for col_monto in ["MONTO ORIG", "MONTO BASE USD", "MONTO PAGADO", "HONORARIOS", "COSTO TOTAL"]:
                                    if col_monto in nueva_fila and pd.notnull(nueva_fila[col_monto]):
                                        nueva_fila[col_monto] = float(nueva_fila[col_monto]) * pct
                                nuevos_registros_masivos.append(nueva_fila)
                                
                    df_actual = df_actual.drop(index=seleccionados_idx)
                    df_nuevos_masivos = pd.DataFrame(nuevos_registros_masivos)
                    df_actual = pd.concat([df_actual, df_nuevos_masivos], ignore_index=True)
                    
                    st.session_state.df_maestro = df_actual
                    guardar_cache_local()
                    st.success(f"¡Distribución completada! Se reemplazaron {len(seleccionados_idx)} egresos por {len(df_nuevos_masivos)} registros fraccionados.")
                    st.rerun()
            else:
                st.button("🔴 Grabar (Completar 100% o Seleccionar)", type="secondary", disabled=True, use_container_width=True)
                
    else:
        st.warning("No hay egresos registrados aún para distribuir.")

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

    column_config_ing = {
        "FECHA": st.column_config.DateColumn("📅 Fecha"),
        "MONEDA": st.column_config.SelectboxColumn("💵 Moneda", options=monedas_ingresos, required=True),
        "TASA": st.column_config.NumberColumn("📈 Tasa", format="%.4f", min_value=0.0),
        "MONTO ORIG": st.column_config.NumberColumn("💰 Monto", format="%.2f", min_value=0.0),
        "MONTO BASE USD": st.column_config.NumberColumn("💵 Monto USD", format="$%.2f", disabled=True),
        "FORMA PAGO": st.column_config.SelectboxColumn("💳 Forma de Pago", options=fp_ingresos, required=True),
    }
    for col in cols_mostrar_ing:
        if col not in st.session_state.columnas_visibles_ingresos:
            column_config_ing[col] = None

    df_ingresos_editado = st.data_editor(
        df_ingresos_sort[cols_mostrar_ing],
        num_rows="dynamic",
        use_container_width=True,
        height=400,
        disabled=['MONTO BASE USD'],
        column_order=st.session_state.columnas_visibles_ingresos,
        column_config=column_config_ing,
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
    cambios_desc = []
    
    # 1. Identificar filas eliminadas (están en original pero no en editado)
    indices_eliminados = df_original_filtrado.index.difference(df_editado_filtrado.index)
    if not indices_eliminados.empty:
        df_maestro = df_maestro.drop(indices_eliminados)
        cambios_desc.append(f"Eliminó {len(indices_eliminados)} contratos")
        
    # 2. Identificar filas comunes y actualizar valores
    indices_comunes = df_original_filtrado.index.intersection(df_editado_filtrado.index)
    if not indices_comunes.empty:
        modificados_count = 0
        for idx in indices_comunes:
            orig_row = df_original_filtrado.loc[idx]
            edit_row = df_editado_filtrado.loc[idx]
            if not orig_row.equals(edit_row):
                modificados_count += 1
        if modificados_count > 0:
            cambios_desc.append(f"Modificó {modificados_count} contratos")
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
        cambios_desc.append(f"Añadió {len(indices_nuevos)} nuevos contratos")
        
    # Limpiar y resetear index para mantener la base de datos limpia y ordenada
    df_maestro = df_maestro.reset_index(drop=True)
    
    # Recalcular todo
    df_maestro_procesado = procesar_csv(df_maestro)
    if df_maestro_procesado is not None:
        st.session_state.df_maestro = df_maestro_procesado
        if cambios_desc:
            registrar_auditoria("EDICIÓN CONTRATOS", " | ".join(cambios_desc))
        else:
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
    st.markdown("### 🎯 Comparativa y Control de Presupuesto Estimado")
    st.markdown(
        "En esta pestaña puedes comparar el **Monto Ejecutado** (acumulado de todos tus gastos) con un **Monto Estimado** que tú definas para cada capítulo. "
        "Esto te permite proyectar costos según lo que falte por construir y calcular el costo por metro cuadrado ($/m²)."
    )

    # Inyectar estilos personalizados para que el input del área parezca una tarjeta de métrica premium
    st.markdown("""
        <style>
        /* Estilos específicos para el input de área en la cabecera (excluyendo el sidebar) */
        div.stNumberInput:not([data-testid="stSidebar"] *) {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(10px) !important;
            -webkit-backdrop-filter: blur(10px) !important;
            border: 1px solid rgba(226, 232, 240, 0.8) !important;
            border-radius: 16px !important;
            padding: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
            height: auto !important;
        }
        div.stNumberInput:not([data-testid="stSidebar"] *):hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05) !important;
        }
        div.stNumberInput:not([data-testid="stSidebar"] *) label {
            font-size: 0.85rem !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            color: #64748b !important;
            letter-spacing: 0.05em !important;
            margin-bottom: 5px !important;
        }
        div.stNumberInput:not([data-testid="stSidebar"] *) div[data-baseweb="input"] {
            border: none !important;
            background: transparent !important;
            box-shadow: none !important;
        }
        div.stNumberInput:not([data-testid="stSidebar"] *) input {
            font-size: 2rem !important;
            font-weight: 900 !important;
            color: #0f172a !important;
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 1. Agrupar gastos ejecutados por CAPITULO
    df_pres = df_gastos_base.copy()
    if not df_pres.empty:
        df_pres['CAPITULO'] = df_pres['CAPITULO'].astype(str).str.strip().str.upper().replace('', 'SIN CAPÍTULO')
        presupuestos_grouped = df_pres.groupby(['CAPITULO']).agg({
            'COSTO TOTAL': 'sum'
        }).reset_index().rename(columns={'COSTO TOTAL': 'MONTO EJECUTADO'})
    else:
        presupuestos_grouped = pd.DataFrame(columns=['CAPITULO', 'MONTO EJECUTADO'])

    # 2. Sincronizar diccionario de estimados y áreas en st.session_state
    presupuestos_estimados = st.session_state.get("presupuestos_estimados", {})
    areas_estimadas_capitulos = st.session_state.get("areas_estimadas_capitulos", {})
    cambios_est = False
    cambios_area = False
    for cap in presupuestos_grouped['CAPITULO'].unique():
        if cap not in presupuestos_estimados:
            # Por defecto inicializamos el estimado al ejecutado
            presupuestos_estimados[cap] = float(presupuestos_grouped.loc[presupuestos_grouped['CAPITULO'] == cap, 'MONTO EJECUTADO'].values[0])
            cambios_est = True
        if cap not in areas_estimadas_capitulos:
            areas_estimadas_capitulos[cap] = 0.0
            cambios_area = True
            
    if cambios_est or cambios_area:
        if cambios_est:
            st.session_state.presupuestos_estimados = presupuestos_estimados
        if cambios_area:
            st.session_state.areas_estimadas_capitulos = areas_estimadas_capitulos
        guardar_cache_local()

    # 3. Construir tabla comparativa y calcular totales previos
    presupuestos_grouped['MONTO ESTIMADO'] = presupuestos_grouped['CAPITULO'].map(lambda x: float(presupuestos_estimados.get(x, 0.0)))
    presupuestos_grouped['RESTANTE'] = presupuestos_grouped['MONTO ESTIMADO'] - presupuestos_grouped['MONTO EJECUTADO']
    
    # Calcular % avance/ejecución (evitar divisiones por cero)
    def calc_pct(row):
        est = row['MONTO ESTIMADO']
        ej = row['MONTO EJECUTADO']
        if est > 0:
            val = (ej / est) * 100
            return min(max(val, 0.0), 100.0)
        return 100.0 if ej > 0 else 100.0
    
    presupuestos_grouped['PORCENTAJE_EJECUCION'] = presupuestos_grouped.apply(calc_pct, axis=1)

    total_ejecutado = presupuestos_grouped['MONTO EJECUTADO'].sum() if not presupuestos_grouped.empty else 0.0
    total_estimado = presupuestos_grouped['MONTO ESTIMADO'].sum() if not presupuestos_grouped.empty else 0.0
    total_restante = total_estimado - total_ejecutado
    pct_avance_total = (total_ejecutado / total_estimado * 100) if total_estimado > 0 else 0.0

    # Mapear el área de cada capítulo y calcular costo unitario
    presupuestos_grouped['AREA_M2'] = presupuestos_grouped['CAPITULO'].map(lambda x: float(areas_estimadas_capitulos.get(x, 0.0)))
    
    # Filtrar capítulos con área física (> 0)
    df_fisico = presupuestos_grouped[presupuestos_grouped['AREA_M2'] > 0]

    # 4. Configuración del Área del Proyecto y Métricas Unitarias
    # El área total se calcula automáticamente sumando las áreas de los capítulos
    area = df_fisico['AREA_M2'].sum() if not df_fisico.empty else 0.0
    st.session_state.area_m2 = area

    col_area, col_real, col_est = st.columns(3)
    with col_area:
        st.metric(
            label="📐 ÁREA TOTAL DE CONSTRUCCIÓN (m²)",
            value=f"{area:,.2f} m²",
            delta="Suma de áreas de capítulos"
        )

    with col_real:
        if area > 0:
            m2_real_total = total_ejecutado / area
            st.metric(
                label="💵 COSTO REAL EJECUTADO por m²",
                value=f"$ {m2_real_total:,.2f} /m²",
                delta="Gastado hasta el momento"
            )
        else:
            st.metric(
                label="💵 COSTO REAL EJECUTADO por m²",
                value="N/A",
                delta="Ingrese área para calcular"
            )

    with col_est:
        if area > 0:
            m2_est_total = total_estimado / area
            st.metric(
                label="🎯 COSTO TOTAL PROYECTADO por m²",
                value=f"$ {m2_est_total:,.2f} /m²",
                delta="Presupuesto estimado total"
            )
        else:
            st.metric(
                label="🎯 COSTO TOTAL PROYECTADO por m²",
                value="N/A",
                delta="Ingrese área para calcular"
            )

    # Calcular costo por m2 específico por capítulo
    def fmt_ejecutado_m2(row):
        area_cap = row['AREA_M2']
        if area_cap > 0:
            val = row['MONTO EJECUTADO'] / area_cap
            return f"$ {val:,.2f} /m²"
        return "Global"

    def fmt_estimado_m2(row):
        area_cap = row['AREA_M2']
        if area_cap > 0:
            val = row['MONTO ESTIMADO'] / area_cap
            return f"$ {val:,.2f} /m²"
        return "Global"

    presupuestos_grouped['EJECUTADO_M2'] = presupuestos_grouped.apply(fmt_ejecutado_m2, axis=1)
    presupuestos_grouped['ESTIMADO_M2'] = presupuestos_grouped.apply(fmt_estimado_m2, axis=1)

    # 5. Renderizar Editor de Datos para el Monto Estimado
    st.markdown("#### 📝 Modificar Presupuesto Estimado")
    st.info("💡 Haz doble clic en cualquier celda de la columna **Monto Estimado (USD)**, **% Ejecución** o **Área Capítulo (m²)** para editarlas y haz clic en **Guardar Cambios**.")

    # Estilos CSS inyectados para resaltar el campo de edición activo y agrandar la tabla completa
    st.markdown("""
        <style>
        /* Estilo global de la tabla de presupuestos */
        div[data-testid="stDataEditor"] {
            --gdg-font-size: 16px !important;
            --gdg-header-font-size: 14px !important;
            --gdg-row-height: 40px !important;
            --gdg-font-family: "Segoe UI Semibold", "Arial Bold", -apple-system, sans-serif !important;
        }
        
        /* Estilo para el campo de edición activo dentro del editor de datos */
        div[data-testid="stDataEditor"] input,
        div[data-testid="stDataEditor"] textarea,
        .glide-grid-editor,
        .gdg-input {
            background-color: #e0f2fe !important; /* Fondo azul tenue */
            color: #1e3a8a !important; /* Números más oscuros (azul marino) */
            font-size: 20px !important; /* Tamaño más grande */
            font-weight: 900 !important; /* Más oscuro/grueso */
            border: 2px solid #2563eb !important;
            border-radius: 8px !important;
            text-align: center !important;
        }
        </style>
    """, unsafe_allow_html=True)

    columnas_editables = ['CAPITULO', 'MONTO EJECUTADO', 'MONTO ESTIMADO', 'PORCENTAJE_EJECUCION', 'RESTANTE', 'AREA_M2', 'EJECUTADO_M2', 'ESTIMADO_M2']

    df_editable_input = presupuestos_grouped[columnas_editables].copy()

    # Configuración de columnas
    config_cols = {
        "CAPITULO": st.column_config.TextColumn("🏗️ Capítulo", disabled=True),
        "MONTO EJECUTADO": st.column_config.NumberColumn("🔴 Monto Ejecutado (USD)", format="$%.2f", disabled=True),
        "MONTO ESTIMADO": st.column_config.NumberColumn("🎯 Monto Estimado (USD)", format="$%.2f", min_value=0.0),
        "PORCENTAJE_EJECUCION": st.column_config.NumberColumn("🔵 ✍️ % EJECUCIÓN (EDITABLE)", format="%.1f%%", min_value=0.1, max_value=100.0, step=0.1, help="Porcentaje de avance del capítulo. Si cambias este porcentaje, se recalculará automáticamente el Monto Estimado."),
        "RESTANTE": st.column_config.NumberColumn("⏳ Restante / Desviación (USD)", format="$%.2f", disabled=True, help="Monto Estimado - Monto Ejecutado. Valores negativos indican que se ha sobrepasado el estimado."),
        "AREA_M2": st.column_config.NumberColumn("🟢 ✍️ ÁREA CAPÍTULO (m² - EDITABLE)", format="%.2f", min_value=0.0, help="Área de construcción de este capítulo. Si es 0.0, se considera costo global/fijo."),
        "EJECUTADO_M2": st.column_config.TextColumn("💵 Ejecutado USD/m²", disabled=True),
        "ESTIMADO_M2": st.column_config.TextColumn("📐 Estimado USD/m²", disabled=True),
    }

    df_presupuestos_editado = st.data_editor(
        df_editable_input,
        column_config=config_cols,
        hide_index=True,
        use_container_width=True,
        key=f"editor_presupuestos_{st.session_state.reset_counter_presupuestos}"
    )

    # 6. Botones de acción
    col_save_p = st.columns([1, 1])
    with col_save_p[0]:
        if st.button("💾 Guardar Cambios de Presupuesto", type="primary", use_container_width=True):
            # Guardar los nuevos estimados identificando qué cambió y las áreas de capítulos
            for idx, row in df_presupuestos_editado.iterrows():
                cap = row['CAPITULO']
                monto_ej = float(row['MONTO EJECUTADO'])
                
                orig_row = df_editable_input.iloc[idx]
                orig_pct = float(orig_row['PORCENTAJE_EJECUCION'])
                orig_est = float(orig_row['MONTO ESTIMADO'])
                
                new_pct = float(row['PORCENTAJE_EJECUCION'])
                new_est = float(row['MONTO ESTIMADO'])
                new_area = float(row['AREA_M2'])
                
                # Si el porcentaje de ejecución cambió
                if abs(new_pct - orig_pct) > 0.01:
                    if new_pct > 0:
                        est_val = monto_ej / (new_pct / 100.0)
                    else:
                        est_val = monto_ej
                # Si el monto estimado cambió
                elif abs(new_est - orig_est) > 0.01:
                    est_val = new_est
                else:
                    est_val = orig_est
                    
                st.session_state.presupuestos_estimados[cap] = float(est_val)
                st.session_state.areas_estimadas_capitulos[cap] = float(new_area)
                
            registrar_auditoria("PRESUPUESTO", "Actualizó montos estimados y áreas de capítulos.")
            st.success("✅ Presupuestos y áreas de capítulos actualizados con éxito.")
            st.rerun()
    with col_save_p[1]:
        if st.button("👁️ Restablecer Vista de Presupuesto", use_container_width=True, key="reset_presupuestos"):
            st.session_state.reset_counter_presupuestos += 1
            st.rerun()

    # 7. Resumen de Métricas Globales
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 📊 Resumen General del Presupuesto")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("🔴 TOTAL EJECUTADO", f"$ {total_ejecutado:,.2f}", delta="Costo Real Acumulado", delta_color="off")
    col_m2.metric("🎯 TOTAL ESTIMADO", f"$ {total_estimado:,.2f}", delta="Proyección de Costos", delta_color="off")
    col_m3.metric("⏳ RESTANTE / MARGEN", f"$ {total_restante:,.2f}", delta="Disponible" if total_restante >= 0 else "Excedido", delta_color="normal" if total_restante >= 0 else "inverse")
    col_m4.metric("📈 AVANCE CONTABLE TOTAL", f"{pct_avance_total:.1f}%", delta="Porcentaje de Ejecución", delta_color="normal" if pct_avance_total <= 100 else "inverse")

    # 8. Gráfico Visual Comparativo
    if not presupuestos_grouped.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 Gráfico Comparativo: Progreso del Presupuesto por Capítulo")
        
        df_chart_pres = presupuestos_grouped.sort_values('MONTO ESTIMADO', ascending=True).copy()
        
        df_chart_pres['Ejecutado (Real)'] = df_chart_pres['MONTO EJECUTADO']
        df_chart_pres['Restante (Margen)'] = df_chart_pres['RESTANTE'].apply(lambda x: max(x, 0.0))
        df_chart_pres['Exceso (Desviación)'] = df_chart_pres['RESTANTE'].apply(lambda x: abs(min(x, 0.0)))
        
        df_melted = df_chart_pres.melt(
            id_vars=['CAPITULO'],
            value_vars=['Ejecutado (Real)', 'Restante (Margen)', 'Exceso (Desviación)'],
            var_name='Estado',
            value_name='Monto (USD)'
        )
        
        fig = px.bar(
            df_melted,
            y='CAPITULO',
            x='Monto (USD)',
            color='Estado',
            orientation='h',
            labels={'CAPITULO': 'Capítulo', 'Monto (USD)': 'Monto (USD)', 'Estado': 'Estatus del Presupuesto'},
            color_discrete_map={
                'Ejecutado (Real)': '#ef4444',       # Rojo
                'Restante (Margen)': '#3b82f6',      # Azul
                'Exceso (Desviación)': '#7f1d1d'     # Rojo Oscuro (Desviación)
            }
        )
        
        fig.update_layout(
            barmode='stack',
            hovermode="y unified",
            margin=dict(t=40, b=20, l=40, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)

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
        # Selector de jerarquía global
        col_sel1, col_sel2 = st.columns([1.5, 2.5])
        with col_sel1:
            orden_jerarquia = st.selectbox(
                "🔍 Dirección de la Jerarquía (Árbol y Concéntrico):", 
                ["Capítulo -> Sub-Capítulo", "Sub-Capítulo -> Capítulo"]
            )
            
            if orden_jerarquia == "Capítulo -> Sub-Capítulo":
                ruta_jerarquia = ['CAPITULO', 'SUBCAPITULO']
            else:
                ruta_jerarquia = ['SUBCAPITULO', 'CAPITULO']
                
            graf_hier = df_gastos[df_gastos['COSTO TOTAL'] > 0].copy()
            
        # Gráficos detallados ordenados uno debajo de otro
        # 1. Gráfico de Evolución Mensual
        graf_mes = df_gastos.groupby('MES_AÑO')['COSTO TOTAL'].sum().reset_index()
        fig_mes = px.bar(graf_mes, x='MES_AÑO', y='COSTO TOTAL', 
                         title="Evolución de Gastos por Período",
                         color_discrete_sequence=['#3b82f6'])
        fig_mes.update_layout(margin=dict(t=40, b=20, l=40, r=20))
        st.plotly_chart(fig_mes, use_container_width=True)
        
        # 2. Gráfico Top Proveedores (Barras Horizontales)
        graf_prov = df_gastos.groupby('PROVEEDOR')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=True).tail(10)
        fig_prov = px.bar(graf_prov, x='COSTO TOTAL', y='PROVEEDOR', orientation='h',
                          title="Top 10 Proveedores (Costo Total)",
                          color='COSTO TOTAL', color_continuous_scale='Blues')
        fig_prov.update_layout(margin=dict(t=40, b=20, l=40, r=20), coloraxis_showscale=False)
        st.plotly_chart(fig_prov, use_container_width=True)
        
        # 3. Gráfico de Capítulos - Barra Apilada (Stacked) por Tipo de Gasto
        graf_cap = df_gastos.groupby(['CAPITULO', 'TIPO'])['COSTO TOTAL'].sum().reset_index()
        fig_cap = px.bar(graf_cap, x='CAPITULO', y='COSTO TOTAL', color='TIPO',
                         title="Distribución por Capítulo (Composición por Tipo de Gasto)",
                         labels={'CAPITULO': 'Capítulo', 'COSTO TOTAL': 'Costo Total (USD)', 'TIPO': 'Tipo de Gasto'},
                         color_discrete_sequence=px.colors.qualitative.Plotly)
        fig_cap.update_layout(margin=dict(t=45, b=20, l=40, r=20), barmode='stack', hovermode="x unified")
        fig_cap.update_xaxes(categoryorder='total descending')
        st.plotly_chart(fig_cap, use_container_width=True)
        
        # 4. Gráfico de Sub-Capítulos - Barra Apilada (Stacked) por Tipo de Gasto
        graf_subcap = df_gastos.groupby(['SUBCAPITULO', 'TIPO'])['COSTO TOTAL'].sum().reset_index()
        fig_subcap = px.bar(graf_subcap, x='SUBCAPITULO', y='COSTO TOTAL', color='TIPO',
                            title="Distribución por Sub-Capítulo (Composición por Tipo de Gasto)",
                            labels={'SUBCAPITULO': 'Sub-Capítulo', 'COSTO TOTAL': 'Costo Total (USD)', 'TIPO': 'Tipo de Gasto'},
                            color_discrete_sequence=px.colors.qualitative.Safe)
        fig_subcap.update_layout(margin=dict(t=45, b=20, l=40, r=20), barmode='stack', hovermode="x unified")
        fig_subcap.update_xaxes(categoryorder='total descending')
        st.plotly_chart(fig_subcap, use_container_width=True)
        
        # 5. Gráfico por Tipo de Gasto (Donut)
        graf_tipo = df_gastos.groupby('TIPO')['COSTO TOTAL'].sum().reset_index()
        fig_tipo = px.pie(graf_tipo, values='COSTO TOTAL', names='TIPO', hole=0.4, 
                          title="Distribución Total por Tipo de Gasto",
                          color_discrete_sequence=px.colors.sequential.Plotly3)
        fig_tipo.update_layout(margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_tipo, use_container_width=True)
        
        # 6. Estructura Concéntrica (Sunburst)
        if not graf_hier.empty:
            fig_sun = px.sunburst(
                graf_hier, 
                path=ruta_jerarquia, 
                values='COSTO TOTAL',
                title=f"Estructura Concéntrica ({orden_jerarquia})",
                color='COSTO TOTAL',
                color_continuous_scale='Mint',
                labels={'parent': 'Categoría Padre', 'id': 'Categoría', 'COSTO TOTAL': 'Costo Total (USD)'}
            )
            fig_sun.update_traces(
                texttemplate="<b>%{label}</b><br>💵 %{value:$,.2f}<br>📊 %{percentParent:.1%}",
                hovertemplate="<b>%{label}</b><br>Costo Total: %{value:$,.2f}<br>Porcentaje del Padre: %{percentParent:.2%}<br>Porcentaje del Total: %{percentRoot:.2%}<extra></extra>"
            )
            fig_sun.update_layout(margin=dict(t=50, b=20, l=20, r=20))
            st.plotly_chart(fig_sun, use_container_width=True)
            
        # 4. Mapa de Árbol (Treemap) - de ancho completo abajo de las columnas
        st.markdown("---")
        st.subheader("🌳 Relación Jerárquica del Presupuesto (Mapa de Árbol)")
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
            fig_tree.update_traces(
                texttemplate="<b>%{label}</b><br>💵 %{value:$,.2f}<br>📊 %{percentParent:.1%} (padre)<br>🌐 %{percentRoot:.1%} (total)",
                textposition="middle center",
                hovertemplate="<b>%{label}</b><br>Costo Total: %{value:$,.2f}<br>Porcentaje del Padre: %{percentParent:.2%}<br>Porcentaje del Total: %{percentRoot:.2%}<extra></extra>"
            )
            fig_tree.update_layout(margin=dict(t=50, b=20, l=20, r=20))
            st.plotly_chart(fig_tree, use_container_width=True)
            
            st.info("💡 **Consejo de navegación:** En el Mapa de Árbol, puedes hacer **clic** en cualquier bloque superior para ver su desglose interno, y hacer clic en la barra superior para regresar.")
        else:
            st.warning("No hay datos suficientes con costos mayores a cero para graficar la relación jerárquica.")
    else:
        st.warning("No hay datos suficientes para generar gráficos.")

with tab_datos_graficos:
    st.markdown("### 📈 Datos Numéricos de los Gráficos")
    st.info("Aquí puedes ver el detalle numérico exacto de cada gráfico mostrado en la pestaña anterior para un análisis profundo o para exportar los datos a CSV.")
    
    if not df_gastos.empty:
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            st.markdown("#### Evolución Mensual")
            df_mes = df_gastos.groupby('MES_AÑO')['COSTO TOTAL'].sum().reset_index()
            df_mes.loc['Total'] = ['TOTAL', df_mes['COSTO TOTAL'].sum()]
            st.dataframe(df_mes.style.format({'COSTO TOTAL': formatear_usd}), use_container_width=True)
            
            st.markdown("#### Top 10 Proveedores")
            df_prov = df_gastos.groupby('PROVEEDOR')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False).head(10)
            df_prov.loc['Total'] = ['TOTAL', df_prov['COSTO TOTAL'].sum()]
            st.dataframe(df_prov.style.format({'COSTO TOTAL': formatear_usd}), use_container_width=True)
            
        with col_d2:
            st.markdown("#### Distribución por Capítulo")
            df_cap = df_gastos.groupby('CAPITULO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
            df_cap.loc['Total'] = ['TOTAL', df_cap['COSTO TOTAL'].sum()]
            st.dataframe(df_cap.style.format({'COSTO TOTAL': formatear_usd}), use_container_width=True)
            
            st.markdown("#### Distribución por Tipo de Gasto")
            df_tipo = df_gastos.groupby('TIPO')['COSTO TOTAL'].sum().reset_index().sort_values('COSTO TOTAL', ascending=False)
            df_tipo.loc['Total'] = ['TOTAL', df_tipo['COSTO TOTAL'].sum()]
            st.dataframe(df_tipo.style.format({'COSTO TOTAL': formatear_usd}), use_container_width=True)
            
        st.markdown("---")
        st.markdown("#### Detalle Completo: Capítulo, Sub-Capítulo y Tipo de Gasto")
        df_det = df_gastos.groupby(['CAPITULO', 'SUBCAPITULO', 'TIPO'])['COSTO TOTAL'].sum().reset_index().sort_values(['CAPITULO', 'COSTO TOTAL'], ascending=[True, False])
        df_det.loc['Total'] = ['TOTAL', '', '', df_det['COSTO TOTAL'].sum()]
        st.dataframe(df_det.style.format({'COSTO TOTAL': formatear_usd}), use_container_width=True)
    else:
        st.warning("No hay datos de gastos suficientes para mostrar tablas numéricas.")

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

with tab_auditoria:
    st.markdown("### 📜 Historial de Actividades (Auditoría)")
    st.info("💡 Este historial registra todas las acciones importantes realizadas en la plataforma para control y auditoría contable.")
    
    df_auditoria = df_app[df_app['CLASE'] == 'AUDITORIA'].copy()
    if not df_auditoria.empty:
        # Convertir FECHA a datetime para ordenar de forma segura
        df_auditoria['FECHA_DT'] = pd.to_datetime(df_auditoria['FECHA'], errors='coerce')
        df_auditoria = df_auditoria.sort_values('FECHA_DT', ascending=False)
        
        st.dataframe(
            df_auditoria[['FECHA', 'PROVEEDOR', 'TIPO', 'DESCRIPCION']],
            column_config={
                "FECHA": st.column_config.DatetimeColumn("📅 Fecha y Hora", format="DD/MM/YYYY HH:mm:ss"),
                "PROVEEDOR": st.column_config.TextColumn("👤 Usuario / Auditor"),
                "TIPO": st.column_config.TextColumn("🎬 Acción"),
                "DESCRIPCION": st.column_config.TextColumn("📝 Detalles de la Actividad")
            },
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        # Botón para borrar el historial
        st.markdown("<br>", unsafe_allow_html=True)
        col_clear1, col_clear2 = st.columns([1, 3])
        with col_clear1:
            if st.button("🗑️ Borrar Historial de Auditoría", type="secondary", use_container_width=True):
                st.session_state.confirmar_borrado_auditoria = True
                
        if st.session_state.confirmar_borrado_auditoria:
            st.warning("⚠️ ¿Está seguro de que desea borrar todo el historial de modificaciones? Esta acción no se puede deshacer y quedará registrada en el nuevo historial.")
            col_conf1, col_conf2 = st.columns([1, 1])
            with col_conf1:
                if st.button("🔴 Sí, Borrar Todo", type="primary", use_container_width=True):
                    # Filtrar fuera todas las de auditoria
                    df_maestro_sin_aud = st.session_state.df_maestro[st.session_state.df_maestro['CLASE'] != 'AUDITORIA'].copy()
                    st.session_state.df_maestro = df_maestro_sin_aud
                    st.session_state.confirmar_borrado_auditoria = False
                    # Registrar log inicial de borrado
                    registrar_auditoria("HISTORIAL BORRADO", "Un usuario eliminó todo el historial anterior de la base de datos.")
                    st.success("✅ Historial de auditoría eliminado con éxito.")
                    st.rerun()
            with col_conf2:
                if st.button("Cancelar", use_container_width=True):
                    st.session_state.confirmar_borrado_auditoria = False
                    st.rerun()
    else:
        st.write("No hay registros en el historial de auditoría.")

# --- FASE 6: EXPORTADORES Y GUARDADO ---
st.sidebar.markdown("<br><h2 style='color:#1e3a8a; font-weight:800;'><i class='fa-solid fa-download'></i> Exportar Datos</h2>", unsafe_allow_html=True)

# Preparar CSV para descarga
csv_data = df_app.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="💾 Respaldar Archivo Csv",
    data=csv_data,
    file_name=f"MAESTRO_{st.session_state.obra_nombre}_{datetime.date.today().strftime('%Y%m%d')}.csv",
    mime='text/csv',
    use_container_width=True
)

# Inicializar selección de PDF en session_state si no existe
if "pdf_elements" not in st.session_state:
    st.session_state.pdf_elements = pd.DataFrame([
        {"Elemento": "📊 Flujo de Caja General", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "🍩 Distribución por Tipo de Gasto", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "🔨 Progreso Presupuesto Capítulo", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "📦 Egresos por Capítulo", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "🏷️ Top 15 Sub-Capítulos", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "🌳 Mapa de Árbol (Treemap)", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "🎯 Estructura Concéntrica", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "💼 Contratos: Ejecutado vs Pendiente", "Tipo": "Gráfico", "Imprimir": True},
        {"Elemento": "📝 Listado Detallado de Egresos", "Tipo": "Tabla", "Imprimir": True},
        {"Elemento": "💵 Listado Detallado de Ingresos", "Tipo": "Tabla", "Imprimir": True},
        {"Elemento": "🤝 Resumen Consolidado Contratos", "Tipo": "Tabla", "Imprimir": True},
        {"Elemento": "📈 Comparativa Presupuesto Estimado", "Tipo": "Tabla", "Imprimir": True},
    ])

# UI para editar elementos a imprimir
st.sidebar.markdown("### 📋 Configurar Reporte PDF")
edited_pdf_df = st.sidebar.data_editor(
    st.session_state.pdf_elements,
    column_config={
        "Imprimir": st.column_config.CheckboxColumn("Imprimir", default=True),
        "Elemento": st.column_config.TextColumn("Elemento", disabled=True),
        "Tipo": st.column_config.TextColumn("Tipo", disabled=True),
    },
    disabled=["Elemento", "Tipo"],
    hide_index=True,
    use_container_width=True,
    key="pdf_elements_editor"
)
st.session_state.pdf_elements = edited_pdf_df

# Construir diccionario de opciones
selected_elements = set(edited_pdf_df[edited_pdf_df["Imprimir"] == True]["Elemento"].tolist())

opciones_pdf = {
    "flujo_caja": "📊 Flujo de Caja General" in selected_elements,
    "tipo_gasto": "🍩 Distribución por Tipo de Gasto" in selected_elements,
    "progreso_cap": "🔨 Progreso Presupuesto Capítulo" in selected_elements,
    "egresos_cap": "📦 Egresos por Capítulo" in selected_elements,
    "subcap": "🏷️ Top 15 Sub-Capítulos" in selected_elements,
    "treemap": "🌳 Mapa de Árbol (Treemap)" in selected_elements,
    "sunburst": "🎯 Estructura Concéntrica" in selected_elements,
    "contratos_graf": "💼 Contratos: Ejecutado vs Pendiente" in selected_elements,
    "egresos_tabla": "📝 Listado Detallado de Egresos" in selected_elements,
    "ingresos_tabla": "💵 Listado Detallado de Ingresos" in selected_elements,
    "contratos_tabla": "🤝 Resumen Consolidado Contratos" in selected_elements,
    "presupuestos_tabla": "📈 Comparativa Presupuesto Estimado" in selected_elements,
}

# Preparar PDF Maestro para descarga
try:
    pdf_data = generar_pdf_maestro(
        df_app=df_app,
        empresa_nombre=st.session_state.empresa_nombre,
        obra_nombre=st.session_state.obra_nombre,
        usuario_actual=st.session_state.usuario_actual,
        admin_pct=admin_pct,
        opciones_pdf=opciones_pdf
    )
    st.sidebar.download_button(
        label="📄 Descargar Reporte PDF Maestro",
        data=pdf_data,
        file_name=f"REPORTE_MAESTRO_{st.session_state.obra_nombre}_{datetime.date.today().strftime('%Y%m%d')}.pdf",
        mime='application/pdf',
        use_container_width=True
    )
except Exception as e:
    st.sidebar.error(f"Error al generar PDF: {e}")

st.sidebar.markdown("<br><p style='text-size:0.8rem; color:gray;'>App Profesional desarrollada por DI MATTEO DESIGN-DIMAQUINAS C.A.</p>", unsafe_allow_html=True)


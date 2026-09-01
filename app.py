import re
import sqlite3
import random
from datetime import datetime
import streamlit as st

# Configuración de página web ancha y moderna
st.set_page_config(
    page_title="Control de Jugadores y Cartones - Bingo",
    page_icon="🎴",
    layout="wide"
)

DB_NAME = "bingo_ventas_escritorio.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            cliente TEXT,
            numeros TEXT,
            cantidad INTEGER,
            estado TEXT DEFAULT 'Pendiente por Cancelar',
            referencia TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Estilos CSS personalizados para mantener el tono oscuro y elegante de tu app original
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stTextInput input, .stNumberInput input { background-color: #1e293b; color: white; border: 1px solid #334155; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #1e293b; color: #94a3b8; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #0284c7 !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# Cabecera superior
st.markdown("### 🎴 Control de Jugadores y Cartones")

col_head1, col_head2, col_head3 = st.columns([3, 1.5, 1.5])
with col_head1:
    busqueda = st.text_input("🔍 Buscar...", placeholder="Cliente, número o ref...", label_visibility="collapsed")
with col_head3:
    precio_unitario = st.number_input("💲 Precio por cartón:", min_value=1.0, value=350.0, step=10.0)

# Obtener datos de la base de datos
def obtener_ventas():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, fecha, cliente, numeros, cantidad, estado, referencia FROM ventas")
    filas = c.fetchall()
    conn.close()
    return filas

filas_db = obtener_ventas()
cartones_ocupados = set()
for _, _, _, numeros, _, _, _ in filas_db:
    for n in re.findall(r"\b\d+\b", numeros):
        cartones_ocupados.add(int(n))

# Pestañas principales
tab_resumen, tab_ventas, tab_disp = st.tabs(["📊 Resumen General", "📋 Ventas y Registro", "🎟️ Matriz de Disponibles (1-630)"])

with tab_resumen:
    st.markdown("#### Resumen General de la Partida")
    tot_cartones_vendidos = len(cartones_ocupados)
    recaudacion_total = tot_cartones_vendidos * precio_unitario
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Cartones Ocupados", f"{tot_cartones_vendidos} / 630")
    col_m2.metric("Cartones Libres", f"{630 - tot_cartones_vendidos}")
    col_m3.metric("Recaudación Estimada", f"Bs. {recaudacion_total:,.2f}")

with tab_ventas:
    # Botonera de acciones rápidas superior
    with st.expander("➕ Opciones de Registro y Asignación Rápida", expanded=True):
        col_btn1, col_btn2, col_btn3 = st.columns(3)
        
        with col_btn1:
            st.markdown("##### ➕ Registrar Nuevo Cliente")
            with st.form("form_nuevo"):
                cli_input = st.text_input("Nombre del Cliente")
                nums_input = st.text_input("Cartones (ej: 12, 45, 100)")
                ref_input = st.text_input("Referencia de Pago (6 dígitos, opcional)", max_chars=6)
                submitted = st.form_submit_button("Guardar Registro")
                
                if submitted:
                    nums_val = [n for n in re.findall(r"\b\d+\b", nums_input) if 1 <= int(n) <= 630]
                    if not nums_val:
                        st.error("Debe indicar al menos un cartón válido (1-630).")
                    else:
                        estado_reg = "Cancelado" if ref_input.strip() else "Pendiente por Cancelar"
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), cli_input.strip() or "Sin Nombre", ", ".join(nums_val), len(nums_val), estado_reg, ref_input.strip()))
                        conn.commit()
                        conn.close()
                        st.success("¡Cliente registrado con éxito!")
                        st.rerun()

        with col_btn2:
            st.markdown("##### 🎲 Asignación Rápida al Azar")
            cant_azar = st.number_input("Cantidad de cartones al azar", min_value=1, max_value=630, value=1)
            if st.button("🎲 Generar y Asignar"):
                disponibles = [n for n in range(1, 631) if n not in cartones_ocupados]
                if len(disponibles) < cant_azar:
                    st.error(f"Solo quedan {len(disponibles)} cartones disponibles.")
                else:
                    seleccionados = sorted(random.sample(disponibles, cant_azar))
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), "Cliente Rápido", ", ".join(map(str, seleccionados)), cant_azar, "Pendiente por Cancelar", ""))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Se asignaron {cant_azar} cartones al azar!")
                    st.rerun()

        with col_btn3:
            st.markdown("##### 🔥 Zona de Peligro")
            if st.button("🗑️ Borrar Todos los Registros", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM ventas")
                conn.commit()
                conn.close()
                st.warning("Se ha borrado toda la base de datos.")
                st.rerun()

    st.divider()

    # Filtrar filas según la barra de búsqueda
    filas_filtradas = []
    for r in filas_db:
        id_r, fecha, cliente, numeros, cantidad, estado, referencia = r
        texto_fila = f"{cliente} {numeros} {referencia}".lower()
        if not busqueda or busqueda.lower() in texto_fila:
            filas_filtradas.append(r)

    # Separar en pendientes y cancelados
    pendientes = [r for r in filas_filtradas if r[5] != "Cancelado"]
    cancelados = [r for r in filas_filtradas if r[5] == "Cancelado"]

    tot_pend_cant = sum(len(re.findall(r"\b\d+\b", r[3])) for r in pendientes)
    tot_canc_cant = sum(len(re.findall(r"\b\d+\b", r[3])) for r in cancelados)

    col_tp1, col_tp2 = st.columns(2)
    with col_tp1:
        st.markdown(f"⏳ **Pendientes por Cancelar** (Total: {tot_pend_cant} cartones | Bs. {tot_pend_cant * precio_unitario:,.2f})")
    with col_tp2:
        st.markdown(f"✅ **Cancelados** (Total: {tot_canc_cant} cartones | Bs. {tot_canc_cant * precio_unitario:,.2f})")

    col_t1, col_t2 = st.columns(2)

    with col_t1:
        for r in pendientes:
            id_r, _, cliente, numeros, _, estado, referencia = r
            with st.container(border=True):
                st.write(f"**👤 {cliente}**")
                st.caption(f"Cartones: {numeros}")
                ref_txt = referencia if referencia else "Sin Ref"
                st.text(f"Ref: {ref_txt} | Estado: {estado}")
                
                c_e1, c_e2 = st.columns(2)
                with c_e1:
                    nueva_ref = st.text_input(f"Actualizar Ref #{id_r}", value=referencia, max_chars=6, key=f"ref_{id_r}")
                    if st.button("Guardar Ref", key=f```python
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    nuevo_estado = "Cancelado" if nueva_ref.strip() else "Pendiente por Cancelar"
                    c.execute("UPDATE ventas SET referencia=?, estado=? WHERE id=?", (nueva_ref.strip(), nuevo_estado, id_r))
                    conn.commit()
                    conn.close()
                    st.rerun()
                with c_e2:
                    if st.button("🗑️ Eliminar", key=f"del_{id_r}"):
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("DELETE FROM ventas WHERE id=?", (id_r,))
                        conn.commit()
                        conn.close()
                        st.rerun()

    with col_t2:
        for r in cancelados:
            id_r, _, cliente, numeros, _, estado, referencia = r
            with st.container(border=True):
                st.write(f"**👤 {cliente}**")
                st.caption(f"Cartones: {numeros}")
                st.text(f"Ref: {referencia} | Estado: {estado}")
                if st.button("🗑️ Eliminar", key=f"del_c_{id_r}"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("DELETE FROM ventas WHERE id=?", (id_r,))
                    conn.commit()
                    conn.close()
                    st.rerun()

with tab_disp:
    st.markdown("#### Matriz de Cartones (1 al 630)")
    st.caption("🟢 Verde: Libre  |  🔴 Rojo: Ocupado")
    
    # Dibujar la matriz en filas de 18 columnas de forma visual limpia
    cols_por_fila = 18
    for i in range(0, 630, cols_por_fila):
        cols = st.columns(cols_por_fila)
        for j in range(cols_por_fila):
            num = i + j + 1
            if num <= 630:
                with cols[j]:
                    if num in cartones_ocupados:
                        st.markdown(f"<div style='background-color:#b91c1c; color:white; text-align:center; padding:4px; border-radius:3px; font-weight:bold; font-size:11px;'>{num}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background-color:#166534; color:white; text-align:center; padding:4px; border-radius:3px; font-weight:bold; font-size:11px;'>{num}</div>", unsafe_allow_html=True)
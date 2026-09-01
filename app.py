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
            st.markdown("##### ➕ Registrar Manual")
            with st.form("form_nuevo"):
                cli_input = st.text_input("Nombre del Cliente (Solo letras)")
                nums_input = st.text_input("Cartones (Solo números, ej: 12, 45, 100)")
                ref_input = st.text_input("Referencia (6 dígitos, opcional)", max_chars=6)
                submitted = st.form_submit_button("Guardar Registro")
                
                if submitted:
                    if any(char.isdigit() for char in cli_input):
                        st.error("El nombre del cliente no debe contener números.")
                    elif re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nums_input):
                        st.error("El campo de cartones solo debe contener números separados por comas.")
                    else:
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
            st.markdown("##### 📥 Importar desde WhatsApp")
            with st.form("form_whatsapp"):
                texto_wpp = st.text_area("Pega el mensaje de WhatsApp aquí", placeholder="Ej:\nMaria Perez\n12, 45, 100 ref 123456")
                btn_wpp = st.form_submit_button("Procesar y Registrar")
                
                if btn_wpp:
                    if not texto_wpp.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        # Separar por líneas
                        lineas = [l.strip() for l in texto_wpp.split('\n') if l.strip()]
                        
                        nombre_cliente = ""
                        cuerpo_texto = texto_wpp

                        if len(lineas) >= 2:
                            # 1ra Línea: Se asigna directamente como el nombre del contacto o número telefónico de WhatsApp
                            nombre_cliente = lineas[0]
                            # El resto de líneas se usa para buscar cartones y referencias
                            cuerpo_texto = " ".join(lineas[1:])
                        else:
                            # Si se pegó en una sola línea, se toma una porción o se asume genérico
                            nombre_cliente = "Cliente WhatsApp"

                        # Limpiar símbolos molestos o marcas de hora de la línea del nombre si los trae
                        nombre_cliente = re.sub(r'\[\d{1,2}:\d{2}.*?\]', '', nombre_cliente).strip()
                        nombre_cliente = re.sub(r'\d{1,2}:\d{2}\s*(?:p\.?\s*m\.?|a\.?\s*m\.?)?', '', nombre_cliente, flags=re.IGNORECASE).strip()

                        if not nombre_cliente:
                            nombre_cliente = "Cliente WhatsApp"

                        # Extraer cartones válidos (1 a 630) del cuerpo del mensaje
                        nums_wpp = [n for n in re.findall(r"\b\d+\b", cuerpo_texto) if 1 <= int(n) <= 630]
                        
                        # Buscar referencia de pago móvil (6 dígitos exactos)
                        ref_wpp_match = re.search(r"\b\d{6}\b", cuerpo_texto)
                        ref_wpp = ref_wpp_match.group(0) if ref_wpp_match else ""

                        if not nums_wpp:
                            st.error("No se detectaron cartones válidos (1-630) en el mensaje.")
                        else:
                            estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                      (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(nums_wpp), len(nums_wpp), estado_reg, ref_wpp))
                            conn.commit()
                            conn.close()
                            st.success(f"¡Registrado! Cliente: {nombre_cliente} | Cartones: {len(nums_wpp)}")
                            st.rerun()

        with col_btn3:
            st.markdown("##### 🎲 Al Azar y 🗑️ Borrar")
            cant_azar = st.number_input("Cartones al azar", min_value=1, max_value=630, value=1)
            if st.button("🎲 Asignar al Azar"):
                disponibles = [n for n in range(1, 631) if n not in cartones_ocupados]
                if len(disponibles) < cant_azar:
                    st.error(f"Solo quedan {len(disponibles)} libres.")
                else:
                    seleccionados = sorted(random.sample(disponibles, cant_azar))
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), "Cliente Rápido", ", ".join(map(str, seleccionados)), cant_azar, "Pendiente por Cancelar", ""))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Asignados {cant_azar} cartones!")
                    st.rerun()
            
            if st.button("🗑️ Borrar Todo", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM ventas")
                conn.commit()
                conn.close()
                st.warning("Base de datos limpia.")
                st.rerun()

    st.divider()

    # Filtrar filas según la barra de búsqueda
    filas_filtradas = []
    for r in filas_db:
        id_r, fecha, cliente, numeros, cantidad, estado, referencia = r
        texto_fila = f"{cliente} {numeros} {referencia}".lower()
        if not busqueda or busqueda.lower() in texto_fila:
            filas_filtradas.append(r)

    st.markdown("#### 📋 Listado General de Registros")

    # Mostrar todos los registros apilados uno encima del otro con su monto en bolívares
    for r in filas_filtradas:
        id_r, _, cliente, numeros, cantidad, estado, referencia = r
        cant_cartones = len(re.findall(r"\b\d+\b", numeros))
        monto_total = cant_cartones * precio_unitario
        
        with st.container(border=True):
            c_info, c_acciones = st.columns([3, 1])
            
            with c_info:
                st.write(f"**👤 {cliente}** — *{estado}*")
                st.caption(f"Cartones: {numeros} ({cant_cartones} unid.)")
                ref_txt = referencia if referencia else "Sin Referencia"
                st.text(f"Ref: {ref_txt}")
                st.markdown(f"💰 **Total a Pagar: Bs. {monto_total:,.2f}**")
            
            with c_acciones:
                with st.expander("✏️ Editar"):
                    with st.form(key=f"form_edit_{id_r}"):
                        nuevo_cliente = st.text_input("Cliente", value=cliente)
                        nuevos_nums = st.text_input("Cartones", value=numeros)
                        nueva_ref = st.text_input("Ref (6 dig)", value=referencia, max_chars=6)
                        nuevo_estado = st.selectbox("Estado", ["Pendiente por Cancelar", "Cancelado"], index=0 if estado != "Cancelado" else 1)
                        
                        if st.form_submit_button("Guardar"):
                            if re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nuevos_nums):
                                st.error("Los cartones solo llevan números.")
                            else:
                                nums_val_edit = [n for n in re.findall(r"\b\d+\b", nuevos_nums) if 1 <= int(n) <= 630]
                                if not nums_val_edit:
                                    st.error("Cartones inválidos.")
                                else:
                                    conn = sqlite3.connect(DB_NAME)
                                    c = conn.cursor()
                                    c.execute("UPDATE ventas SET cliente=?, numeros=?, cantidad=?, estado=?, referencia=? WHERE id=?",
                                              (nuevo_cliente.strip(), ", ".join(nums_val_edit), len(nums_val_edit), nuevo_estado, nueva_ref.strip(), id_r))
                                    conn.commit()
                                    conn.close()
                                    st.rerun()

                if st.button("🗑️ Eliminar", key=f"del_{id_r}"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("DELETE FROM ventas WHERE id=?", (id_r,))
                    conn.commit()
                    conn.close()
                    st.rerun()

with tab_disp:
    st.markdown("#### Matriz de Cartones (1 al 630)")
    st.caption("🟢 Verde: Libre  |  🔴 Rojo: Ocupado")
    
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

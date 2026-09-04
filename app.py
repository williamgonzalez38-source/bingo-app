import re
import sqlite3
import random
from datetime import datetime
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components

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

# Estilos CSS para barra lateral ultra compacta (100px) y botones de alerta pequeños
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; padding-top: 0.5rem; }
    .stTextInput input, .stNumberInput input { background-color: #1e293b; color: white; border: 1px solid #334155; height: 32px; }
    
    /* Barra lateral ultra angosta (100px) */
    section[data-testid="stSidebar"] { 
        background-color: #0b1120; 
        min-width: 100px !important; 
        max-width: 100px !important; 
    }
    
    /* Botones cuadrados pequeños y centrados en la barra lateral */
    section[data-testid="stSidebar"] div.stButton > button {
        width: 34px !important;
        height: 34px !important;
        min-height: 34px !important;
        padding: 0px !important;
        font-size: 14px !important;
        border-radius: 6px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        margin: 0 auto 5px auto !important;
    }
    </style>
""", unsafe_allow_html=True)

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

# Función para obtener la mejor fuente disponible en el sistema operativo
def obtener_fuente(size):
    candidatos = [
        "arialbd.ttf", "Arial Bold.ttf", "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "DejaVuSans-Bold.ttf"
    ]
    for c in candidatos:
        try:
            return ImageFont.truetype(c, size)
        except:
            continue
    return ImageFont.load_default()

# Función para generar la imagen con números ocupados en tono translúcido/atenuado (#e2e8f0)
def generar_imagen_base64(libres):
    cols = 20  # 20 columnas exactas por fila
    total_items = 630
    rows = (total_items + cols - 1) // cols
    
    col_w = 42    
    row_h = 28    
    margin_x = 25
    margin_y = 25
    header_h = 70
    
    img_w = (cols * col_w) + (margin_x * 2)
    img_h = (rows * row_h) + (margin_y * 2) + header_h
    
    # Fondo general blanco puro
    img = Image.new("RGB", (img_w, img_h), color="#FFFFFF")
    draw = ImageDraw.Draw(img)
    
    font_title = obtener_fuente(20)
    font_grid = obtener_fuente(16)
        
    draw.rectangle([0, 0, img_w, header_h], fill="#1e293b")
    draw.text((margin_x, 15), "🎴 CARTONES DISPONIBLES (1 - 630)", fill="#FFFFFF", font=font_title)
    
    start_x = margin_x
    start_y = header_h + margin_y
    
    for n in range(1, 630 + 1):
        r = (n - 1) // cols
        c = (n - 1) % cols
        
        x = start_x + (c * col_w)
        y = start_y + (r * row_h)
        
        text = str(n)
        
        if n in libres:
            draw.text((x, y), text, fill="#000000", font=font_grid)
        else:
            draw.text((x, y), text, fill="#e2e8f0", font=font_grid)
        
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# Menú lateral ultra angosta con botones cuadrados compactos y tooltips
with st.sidebar:
    st.markdown("### 🧭 Menú")
    st.markdown("---")
    
    if "menu_activo" not in st.session_state:
        st.session_state["menu_activo"] = "📋 Ventas y Registro"

    if st.button("📊", use_container_width=True, help="Resumen General"):
        st.session_state["menu_activo"] = "📊 Resumen General"
        st.rerun()
        
    if st.button("📋", use_container_width=True, help="Ventas y Registro"):
        st.session_state["menu_activo"] = "📋 Ventas y Registro"
        st.rerun()
        
    if st.button("🎟️", use_container_width=True, help="Matriz (1-630)"):
        st.session_state["menu_activo"] = "🎟️ Matriz (1-630)"
        st.rerun()

menu_seleccionado = st.session_state["menu_activo"]

# Cabecera superior: Buscador, Precio y el botón funcional para copiar imagen al portapapeles con 1 clic
st.markdown("### 🎴 Control de Jugadores y Cartones")

col_head1, col_head2, col_head3, col_head4 = st.columns([2.2, 1.2, 1.2, 1.4])
with col_head1:
    busqueda = st.text_input("🔍 Buscar...", placeholder="Cliente, número o ref...", label_visibility="collapsed")
with col_head3:
    precio_unitario = st.number_input("💲 Precio:", min_value=1.0, value=350.0, step=10.0, label_visibility="collapsed")
with col_head4:
    libres_actuales = [n for n in range(1, 631) if n not in cartones_ocupados]
    img_b64 = generar_imagen_base64(libres_actuales)
    
    html_code = """
    <div style="margin: 0; padding: 0;">
        <button id="btnCopiarImg" onclick="copiarImagen()" style="
            background-color: #2563eb;
            color: white;
            border: none;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: bold;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            text-align: center;
            font-family: sans-serif;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
            transition: background 0.2s;
        ">📋 Copiar Imagen</button>
        <p id="msgEstado" style="font-size: 10px; color: #94a3b8; text-align: center; margin: 4px 0 0 0; font-family: sans-serif;"></p>
    </div>

    <script>
    async function copiarImagen() {
        const btn = document.getElementById('btnCopiarImg');
        const msg = document.getElementById('msgEstado');
        
        try {
            const base64Data = "REPLACE_ME_B64";
            const res = await fetch('data:image/png;base64,' + base64Data);
            const blob = await res.blob();
            
            await navigator.clipboard.write([
                new ClipboardItem({ 'image/png': blob })
            ]);
            
            btn.style.backgroundColor = '#16a34a';
            btn.innerText = '¡Copiada con éxito!';
            msg.innerText = '¡Ya puedes ir a WhatsApp y presionar Ctrl + V!';
            
            setTimeout(() => {
                btn.style.backgroundColor = '#2563eb';
                btn.innerText = '📋 Copiar Imagen';
                msg.innerText = '';
            }, 3500);
        } catch (err) {
            console.error(err);
            btn.style.backgroundColor = '#dc2626';
            btn.innerText = 'Error al copiar';
            msg.innerText = 'Intenta usar un navegador compatible (Chrome/Edge)';
        }
    }
    </script>
    """.replace("REPLACE_ME_B64", img_b64)
    
    components.html(html_code, height=65)

if menu_seleccionado == "📊 Resumen General":
    st.markdown("#### Resumen General de la Partida")
    tot_cartones_vendidos = len(cartones_ocupados)
    recaudacion_total = tot_cartones_vendidos * precio_unitario
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Cartones Ocupados", f"{tot_cartones_vendidos} / 630")
    col_m2.metric("Cartones Libres", f"{630 - tot_cartones_vendidos}")
    col_m3.metric("Recaudación Estimada", f"Bs. {recaudacion_total:,.2f}")

elif menu_seleccionado == "📋 Ventas y Registro":
    with st.expander("➕ Opciones de Registro Rápido", expanded=True):
        
        st.markdown("##### ➕ Registrar Manual")
        with st.form("form_nuevo"):
            col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
            with col_f1:
                cli_input = st.text_input("Nombre del Cliente")
            with col_f2:
                nums_input = st.text_input("Cartones (Ej: 12, 45, 100)")
            with col_f3:
                ref_input = st.text_input("Referencia (6 dígitos)", max_chars=6)
            
            submitted = st.form_submit_button("Guardar Registro")
            
            if submitted:
                nums_val = [int(n) for n in re.findall(r"\b\d+\b", nums_input) if 1 <= int(n) <= 630]
                if not cli_input.strip():
                    st.error("Debe indicar el nombre del cliente.")
                elif not nums_val:
                    st.error("Debe indicar al menos un cartón válido (1-630).")
                else:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("SELECT id, numeros, referencia FROM ventas WHERE LOWER(TRIM(cliente)) = LOWER(TRIM(?))", (cli_input.strip(),))
                    cliente_existente = c.fetchone()
                    conn.close()

                    if cliente_existente:
                        if "pendientes_pendientes_wpp" not in st.session_state:
                            st.session_state["pendientes_pendientes_wpp"] = []
                        
                        st.session_state["pendientes_pendientes_wpp"].append({
                            "tipo": "pendiente_nombre_duplicado",
                            "cliente": cli_input.strip(),
                            "nuevos_asignados": [n for n in nums_val if n not in cartones_ocupados],
                            "nuevos_no_disponibles": [n for n in nums_val if n in cartones_ocupados],
                            "ref": ref_input.strip()
                        })
                        st.warning(f"⚠️ El cliente '{cli_input.strip()}' ya existe. Se ha registrado la alerta en su tarjeta abajo.")
                    else:
                        estado_reg = "Cancelado" if ref_input.strip() else "Pendiente por Cancelar"
                        nums_str = ", ".join(map(str, sorted(set(nums_val))))
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), cli_input.strip(), nums_str, len(set(nums_val)), estado_reg, ref_input.strip()))
                        conn.commit()
                        conn.close()
                        st.success("¡Cliente registrado con éxito!")
                        st.rerun()

        st.divider()

        col_inf1, col_inf2 = st.columns(2)
        
        with col_inf1:
            st.markdown("##### 📥 Importar Selección Múltiple de WhatsApp")

            if "wpp_version" not in st.session_state:
                st.session_state["wpp_version"] = 0

            key_text_area = f"input_wpp_area_{st.session_state['wpp_version']}"

            with st.form("form_whatsapp"):
                texto_wpp_unificado = st.text_area(
                    "Pega aquí la selección de WhatsApp (uno o varios contactos)", 
                    key=key_text_area,
                    placeholder="Pega aquí el texto copiado de WhatsApp..."
                )
                
                col_btn_w1, col_btn_w2 = st.columns(2)
                with col_btn_w1:
                    btn_wpp = st.form_submit_button("Procesar e Integrar en el Listado", use_container_width=True)
                with col_btn_w2:
                    btn_borrar_wpp = st.form_submit_button("🗑️ Borrar", use_container_width=True)
                
                if btn_borrar_wpp:
                    st.session_state["wpp_version"] += 1
                    st.rerun()
                
                if btn_wpp:
                    if not texto_wpp_unificado.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        lineas = texto_wpp_unificado.split('\n')
                        
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("SELECT numeros FROM ventas")
                        filas_actuales = c.fetchall()
                        ocupados_en_memoria = set()
                        for f_nums, in filas_actuales:
                            for n in re.findall(r"\b\d+\b", f_nums):
                                ocupados_en_memoria.add(int(n))

                        pendientes_cola = []

                        for linea in lineas:
                            linea_s = linea.strip()
                            if not linea_s:
                                continue

                            nombre_cliente = ""
                            cuerpo_mensaje = ""

                            match_chat = re.search(r'\[.*?\]\s*([^:]+):\s*(.*)', linea_s)
                            if match_chat:
                                nombre_cliente = match_chat.group(1).strip()
                                cuerpo_mensaje = match_chat.group(2).strip()
                            else:
                                match_simple = re.search(r'^([^:]+):\s*(.*)', linea_s)
                                if match_simple and not linea_s.startswith("http") and len(match_simple.group(1).split()) <= 4:
                                    nombre_cliente = match_simple.group(1).strip()
                                    cuerpo_mensaje = match_simple.group(2).strip()
                                else:
                                    nombre_cliente = "Cliente WhatsApp"
                                    cuerpo_mensaje = linea_s

                            ref_wpp_match = re.search(r"\b\d{6}\b", cuerpo_mensaje)
                            ref_wpp = ref_wpp_match.group(0) if ref_wpp_match else ""

                            texto_lower = cuerpo_mensaje.lower()
                            
                            palabras_clave_azar = ["azar", "aleatorio", "ocupados", "si no", "o al azar"]
                            pide_azar = any(palabra in texto_lower for palabra in palabras_clave_azar)

                            todos_numeros = [int(n) for n in re.findall(r"\b\d+\b", cuerpo_mensaje)]
                            candidatos_num = [n for n in todos_numeros if 1 <= n <= 630 and len(str(n)) <= 3]
                            
                            if ref_wpp:
                                candidatos_num = [n for n in candidatos_num if str(n) != ref_wpp]

                            cantidad_azar_solicitada = 0
                            if "azar" in texto_lower or "aleatorio" in texto_lower:
                                for palabra in ["azar", "aleatorio"]:
                                    if palabra in texto_lower:
                                        idx_palabra = texto_lower.find(palabra)
                                        texto_antes = texto_lower[:idx_palabra]
                                        nums_antes = [int(n) for n in re.findall(r"\b\d+\b", texto_antes)]
                                        if nums_antes:
                                            cantidad_azar_solicitada = nums_antes[-1]
                                            if cantidad_azar_solicitada in candidatos_num:
                                                candidatos_num.remove(cantidad_azar_solicitada)
                                        elif len(candidatos_num) == 1 and candidatos_num[0] <= 20:
                                            cantidad_azar_solicitada = candidatos_num[0]
                                            candidatos_num = []
                                        break

                            cartones_asignados = []
                            cartones_no_disponibles = []

                            for num_req in candidatos_num:
                                if num_req not in ocupados_en_memoria:
                                    cartones_asignados.append(num_req)
                                else:
                                    cartones_no_disponibles.append(num_req)

                            c.execute("SELECT id FROM ventas WHERE LOWER(TRIM(cliente)) = LOWER(TRIM(?))", (nombre_cliente,))
                            cliente_db_existente = c.fetchone()

                            if cliente_db_existente:
                                pendientes_cola.append({
                                    "tipo": "pendiente_nombre_duplicado",
                                    "cliente": nombre_cliente,
                                    "nuevos_asignados": cartones_asignados,
                                    "nuevos_no_disponibles": cartones_no_disponibles,
                                    "ref": ref_wpp
                                })
                            elif cartones_no_disponibles and pide_azar:
                                pendientes_cola.append({
                                    "tipo": "pendiente_azar_condicional",
                                    "cliente": nombre_cliente,
                                    "solicitados": candidatos_num,
                                    "ocupados": cartones_no_disponibles,
                                    "libres": cartones_asignados,
                                    "ref": ref_wpp
                                })
                            elif pide_azar and len(candidatos_num) == 0 and cantidad_azar_solicitada > 0:
                                pendientes_cola.append({
                                    "tipo": "pendiente_azar",
                                    "cliente": nombre_cliente,
                                    "cantidad": cantidad_azar_solicitada,
                                    "ref": ref_wpp
                                })
                            else:
                                if cartones_asignados and not cartones_no_disponibles:
                                    for n in cartones_asignados:
                                        ocupados_en_memoria.add(n)

                                    estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                                    c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                              (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(map(str, sorted(cartones_asignados))), len(cartones_asignados), estado_reg, ref_wpp))
                                
                                elif cartones_asignados and cartones_no_disponibles:
                                    for n in cartones_asignados:
                                        ocupados_en_memoria.add(n)

                                    estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                                    c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                              (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(map(str, sorted(cartones_asignados))), len(cartones_asignados), estado_reg, ref_wpp))
                                    
                                    pendientes_cola.append({
                                        "tipo": "solo_no_disponibles",
                                        "cliente": nombre_cliente,
                                        "no_disponibles": cartones_no_disponibles,
                                        "ref": ref_wpp
                                    })
                                elif cartones_no_disponibles and not cartones_asignados:
                                    pendientes_cola.append({
                                        "tipo": "solo_no_disponibles",
                                        "cliente": nombre_cliente,
                                        "no_disponibles": cartones_no_disponibles,
                                        "ref": ref_wpp
                                    })

                        conn.commit()
                        conn.close()

                        st.session_state["wpp_version"] += 1
                        if "pendientes_pendientes_wpp" not in st.session_state:
                            st.session_state["pendientes_pendientes_wpp"] = []
                        st.session_state["pendientes_pendientes_wpp"].extend(pendientes_cola)
                        
                        st.success("¡Chats procesados correctamente!")
                        st.rerun()

        with col_inf2:
            st.markdown("##### 🎲 Al Azar Manual y 🗑️ Borrar Base")
            with st.container(border=True):
                cant_azar = st.number_input("Cartones al azar", min_value=1, max_value=630, value=1)
                if st.button("🎲 Asignar al Azar", use_container_width=True):
                    conn_tmp = sqlite3.connect(DB_NAME)
                    c_tmp = conn_tmp.cursor()
                    c_tmp.execute("SELECT numeros FROM ventas")
                    filas_actuales = c_tmp.fetchall()
                    conn_tmp.close()
                    
                    ocupados_actuales = set()
                    for f_nums, in filas_actuales:
                        for n in re.findall(r"\b\d+\b", f_nums):
                            ocupados_actuales.add(int(n))
                    
                    disponibles_reales = [n for n in range(1, 631) if n not in ocupados_actuales]
                    
                    if len(disponibles_reales) < cant_azar:
                        st.error(f"Solo quedan {len(disponibles_reales)} cartones libres.")
                    else:
                        seleccionados = sorted(random.sample(disponibles_reales, cant_azar))
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), "Cliente Rápido", ", ".join(map(str, seleccionados)), cant_azar, "Pendiente por Cancelar", ""))
                        conn.commit()
                        conn.close()
                        st.success(f"¡Asignados y guardados {cant_azar} cartones al azar!")
                        st.rerun()
                
                st.markdown("---")
                if st.button("🗑️ Borrar Toda la Base", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("DELETE FROM ventas")
                    conn.commit()
                    conn.close()
                    if "pendientes_pendientes_wpp" in st.session_state:
                        st.session_state["pendientes_pendientes_wpp"] = []
                    st.success("¡Base de datos borrada por completo con éxito!")
                    st.rerun()

    st.divider()

    # Recargar filas de base de datos actualizadas tras inserciones automáticas
    filas_db = obtener_ventas()
    filas_filtradas = []
    for r in filas_db:
        id_r, _, cliente, numeros, _, _, referencia = r
        texto_fila = f"{cliente} {numeros} {referencia}".lower()
        if not busqueda or busqueda.lower() in texto_fila:
            filas_filtradas.append(r)

    st.markdown("#### 📋 Listado General de Registros y Alertas Simplificadas")

    notificaciones_pendientes = st.session_state.get("pendientes_pendientes_wpp", [])

    for r in filas_filtradas:
        id_r, _, cliente, numeros, cantidad, estado, referencia = r
        cant_cartones = len(re.findall(r"\b\d+\b", numeros))
        monto_total = cant_cartones * precio_unitario
        
        notif_asociadas = [n_item for n_item in notificaciones_pendientes if n_item.get("cliente", "").strip().lower() == cliente.strip().lower()]

        with st.container(border=True):
            c_info, c_acciones = st.columns([3, 1])
            
            with c_info:
                st.write(f"**👤 {cliente}** — *{estado}*")
                st.caption(f"Cartones: {numeros} ({cant_cartones} unid.)")
                ref_txt = referencia if referencia else "Sin Referencia"
                st.text(f"Ref: {ref_txt}")
                st.markdown(f"💰 **Total a Pagar: Bs. {monto_total:,.2f}**")
                
                # --- BOTONES DE ALERTA PEQUEÑOS Y SIMPLIFICADOS EN LÍNEA ---
                for notif_asociada in notif_asociadas:
                    tipo_n = notif_asociada["tipo"]
                    
                    if tipo_n == "pendiente_nombre_duplicado":
                        if notif_asociada.get('nuevos_asignados'):
                            st.markdown("---")
                            cols_b1, cols_b2 = st.columns([2, 1])
                            with cols_b1:
                                st.caption(f"⚠️ Libres a sumar: `{notif_asociada['nuevos_asignados']}`")
                            with cols_b2:
                                if st.button("➕ Sumar", key=f"sumar_dup_{id_r}_{random.randint(100,999)}", use_container_width=True):
                                    conn = sqlite3.connect(DB_NAME)
                                    c = conn.cursor()
                                    nums_db_lista = [int(n) for n in re.findall(r"\b\d+\b", numeros)]
                                    cartones_combinados = sorted(list(set(nums_db_lista + notif_asociada['nuevos_asignados'])))
                                    nums_combinados_str = ", ".join(map(str, cartones_combinados))
                                    ref_final = referencia if referencia else notif_asociada['ref']
                                    estado_reg = "Cancelado" if ref_final else "Pendiente por Cancelar"
                                    
                                    c.execute("UPDATE ventas SET numeros=?, cantidad=?, estado=?, referencia=? WHERE id=?",
                                              (nums_combinados_str, len(cartones_combinados), estado_reg, ref_final, id_r))
                                    conn.commit()
                                    conn.close()
                                    
                                    notif_asociada['nuevos_asignados'] = []
                                    if not notif_asociada.get('nuevos_no_disponibles') and notif_asociada in st.session_state["pendientes_pendientes_wpp"]:
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                        if notif_asociada.get('nuevos_no_disponibles'):
                            st.markdown("---")
                            cols_o1, cols_o2 = st.columns([2, 1])
                            with cols_o1:
                                texto_copiable = ", ".join(map(str, notif_asociada['nuevos_no_disponibles']))
                                st.code(texto_copiable, language="text")
                            with cols_o2:
                                if st.button("❌ Cerrar", key=f"cerrar_dup_{id_r}_{random.randint(100,999)}", use_container_width=True):
                                    notif_asociada['nuevos_no_disponibles'] = []
                                    if not notif_asociada.get('nuevos_asignados') and notif_asociada in st.session_state["pendientes_pendientes_wpp"]:
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                    elif tipo_n == "solo_no_disponibles":
                        if notif_asociada.get('no_disponibles'):
                            st.markdown("---")
                            cols_s1, cols_s2 = st.columns([2, 1])
                            with cols_s1:
                                texto_copiable = ", ".join(map(str, notif_asociada['no_disponibles']))
                                st.code(texto_copiable, language="text")
                            with cols_s2:
                                if st.button("❌ Cerrar", key=f"cerrar_solo_{id_r}_{random.randint(100,999)}", use_container_width=True):
                                    if notif_asociada in st.session_state["pendientes_pendientes_wpp"]:
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                    elif tipo_n == "pendiente_azar":
                        st.markdown("---")
                        cols_az1, cols_az2 = st.columns([2, 1])
                        with cols_az1:
                            st.caption(f"🎲 Azar pedido: {notif_asociada['cantidad']} un.")
                        with cols_az2:
                            if st.button("🎲 Asignar", key=f"btn_azar_{id_r}", use_container_width=True):
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("SELECT numeros FROM ventas")
                                filas_actuales = c.fetchall()
                                ocupados_en_memoria = set()
                                for f_nums, in filas_actuales:
                                    for n in re.findall(r"\b\d+\b", f_nums):
                                        ocupados_en_memoria.add(int(n))
                                disponibles_reales = [n for n in range(1, 631) if n not in ocupados_en_memoria]

                                if len(disponibles_reales) < notif_asociada['cantidad']:
                                    st.error("No hay suficientes cartones.")
                                else:
                                    cartones_asignados = sorted(random.sample(disponibles_reales, notif_asociada['cantidad']))
                                    nums_db_lista = [int(n) for n in re.findall(r"\b\d+\b", numeros)]
                                    cartones_combinados = sorted(list(set(nums_db_lista + cartones_asignados)))
                                    nums_combinados_str = ", ".join(map(str, cartones_combinados))
                                    ref_final = referencia if referencia else notif_asociada['ref']
                                    estado_reg = "Cancelado" if ref_final else "Pendiente por Cancelar"

                                    c.execute("UPDATE ventas SET numeros=?, cantidad=?, estado=?, referencia=? WHERE id=?",
                                              (nums_combinados_str, len(cartones_combinados), estado_reg, ref_final, id_r))
                                    conn.commit()
                                    conn.close()

                                    st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                    elif tipo_n == "pendiente_azar_condicional":
                        st.markdown("---")
                        cols_con1, cols_con2 = st.columns([2, 1])
                        with cols_con1:
                            st.caption(f"⚠️ Ocupados: {notif_asociada['ocupados']}")
                        with cols_con2:
                            if st.button("🎲 Reemplazar", key=f"btn_cond_{id_r}", use_container_width=True):
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("SELECT numeros FROM ventas")
                                filas_actuales = c.fetchall()
                                ocupados_en_memoria = set()
                                for f_nums, in filas_actuales:
                                    for n in re.findall(r"\b\d+\b", f_nums):
                                        ocupados_en_memoria.add(int(n))

                                cartones_finales_aprobados = list(notif_asociada['libres'])
                                faltantes_cantidad = len(notif_asociada['ocupados'])
                                disponibles_reales = [n for n in range(1, 631) if n not in ocupados_en_memoria and n not in cartones_finales_aprobados]

                                if len(disponibles_reales) < faltantes_cantidad:
                                    st.error("No hay suficientes cartones.")
                                else:
                                    reemplazos_azar = sorted(random.sample(disponibles_reales, faltantes_cantidad))
                                    cartones_finales_aprobados = sorted(cartones_finales_aprobados + reemplazos_azar)
                                    
                                    nums_db_lista = [int(n) for n in re.findall(r"\b\d+\b", numeros)]
                                    cartones_combinados = sorted(list(set(nums_db_lista + cartones_finales_aprobados)))
                                    nums_combinados_str = ", ".join(map(str, cartones_combinados))
                                    ref_final = referencia if referencia else notif_asociada['ref']
                                    estado_reg = "Cancelado" if ref_final else "Pendiente por Cancelar"

                                    c.execute("UPDATE ventas SET numeros=?, cantidad=?, estado=?, referencia=? WHERE id=?",
                                              (nums_combinados_str, len(cartones_combinados), estado_reg, ref_final, id_r))
                                    conn.commit()
                                    conn.close()

                                    st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()
            
            with c_acciones:
                with st.expander("✏️"):
                    with st.form(key=f"form_edit_{id_r}"):
                        st.markdown("##### 🎴 Editar")
                        nuevos_nums = st.text_input("🔢 Números", value=numeros)
                        nuevo_cliente = st.text_input("👤 Cliente", value=cliente)
                        
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            nueva_ref = st.text_input("Ref", value=referencia, max_chars=6)
                        with col_e2:
                            nuevo_estado = st.selectbox("Estado", ["Pendiente por Cancelar", "Cancelado"], index=0 if estado != "Cancelado" else 1)
                        
                        if st.form_submit_button("Guardar", use_container_width=True):
                            nums_val_edit = [int(n) for n in re.findall(r"\b\d+\b", nuevos_nums) if 1 <= int(n) <= 630]
                            if not nuevo_cliente.strip():
                                st.error("Vacío.")
                            elif not nums_val_edit:
                                st.error("Inválidos.")
                            else:
                                conn = sqlite3.connect(DB_NAME)
                                c = conn.cursor()
                                c.execute("UPDATE ventas SET numeros=?, cantidad=?, estado=?, referencia=?, cliente=? WHERE id=?",
                                          (", ".join(map(str, sorted(set(nums_val_edit)))), len(set(nums_val_edit)), nuevo_estado, nueva_ref.strip(), nuevo_cliente.strip(), id_r))
                                conn.commit()
                                conn.close()
                                st.rerun()

                if st.button("🗑️", key=f"del_{id_r}"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("DELETE FROM ventas WHERE id=?", (id_r,))
                    conn.commit()
                    conn.close()
                    st.rerun()

    # Tarjetas de notificaciones huérfanas simplificadas para nuevos clientes
    clientes_en_db = [r[2].strip().lower() for r in filas_db]
    nuevas_notifs_huerfanas = [n for n in notificaciones_pendientes if n.get("cliente", "").strip().lower() not in clientes_en_db]

    if nuevas_notifs_huerfanas:
        st.markdown("---")
        st.markdown("#### 🆕 Novedades de Nuevos Clientes")
        
        for idx_h, n_huerfana in enumerate(nuevas_notifs_huerfanas):
            with st.container(border=True):
                st.markdown(f"**👤 Cliente:** `{n_huerfana['cliente']}`")
                tipo_nh = n_huerfana["tipo"]
                
                if tipo_nh == "pendiente_azar":
                    cols_ha1, cols_ha2 = st.columns([2, 1])
                    with cols_ha1:
                        st.caption(f"🎲 Azar pedido: {n_huerfana['cantidad']} un.")
                    with cols_ha2:
                        if st.button("✅ Asignar", key=f"btn_h_azar_{idx_h}", use_container_width=True):
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("SELECT numeros FROM ventas")
                            filas_actuales = c.fetchall()
                            ocupados_en_memoria = set()
                            for f_nums, in filas_actuales:
                                for n in re.findall(r"\b\d+\b", f_nums):
                                    ocupados_en_memoria.add(int(n))
                            disponibles_reales = [n for n in range(1, 631) if n not in ocupados_en_memoria]

                            if len(disponibles_reales) < n_huerfana['cantidad']:
                                st.error("No hay suficientes cartones.")
                            else:
                                cartones_asignados = sorted(random.sample(disponibles_reales, n_huerfana['cantidad']))
                                ref_wpp = n_huerfana['ref']
                                estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"

                                c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                          (datetime.now().strftime("%Y-%m-%d %H:%M"), n_huerfana['cliente'], ", ".join(map(str, cartones_asignados)), n_huerfana['cantidad'], estado_reg, ref_wpp))
                                conn.commit()
                                conn.close()

                                st.session_state["pendientes_pendientes_wpp"].remove(n_huerfana)
                                st.rerun()

                elif tipo_nh == "solo_no_disponibles":
                    if n_huerfana.get("no_disponibles"):
                        cols_hn1, cols_hn2 = st.columns([2, 1])
                        with cols_hn1:
                            texto_copiable = ", ".join(map(str, n_huerfana['no_disponibles']))
                            st.code(texto_copiable, language="text")
                        with cols_hn2:
                            if st.button("❌ Cerrar", key=f"cerrar_huerfana_{idx_h}", use_container_width=True):
                                if n_huerfana in st.session_state["pendientes_pendientes_wpp"]:
                                    st.session_state["pendientes_pendientes_wpp"].remove(n_huerfana)
                                st.rerun()

elif menu_seleccionado == "🎟️ Matriz (1-630)":
    st.markdown("#### Matriz de Cartones (1 al 630)")
    st.caption("✨ Vista previa con números ocupados en tono translúcido/atenuado")
    
    html_matriz = """
    <div style="background-color: #ffffff; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; overflow-x: auto;">
        <div style="display: grid; grid-template-columns: repeat(20, minmax(36px, 1fr)); gap: 6px; text-align: left;">
    """
    
    for num in range(1, 631):
        if num in cartones_ocupados:
            html_matriz += f"""
            <div style="
                font-family: Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                color: #e2e8f0;
                padding: 4px 0;
            ">{num}</div>
            """
        else:
            html_matriz += f"""
            <div style="
                font-family: Arial, sans-serif;
                font-weight: bold;
                font-size: 14px;
                color: #000000;
                padding: 4px 0;
            ">{num}</div>
            """
            
    html_matriz += """
        </div>
    </div>
    """
    
    components.html(html_matriz, height=750, scrolling=True)

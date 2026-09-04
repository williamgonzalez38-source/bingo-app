import re
import sqlite3
import random
from datetime import datetime
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import streamlit as st
import streamlit.components.v1 as components

# Importar pytesseract para lectura de imágenes (OCR)
try:
    import pytesseract
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

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

# Estilos CSS para barra lateral ultra compacta (100px) y campos compactos de referencia
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

# Obtener datos de la base de datos ordenados del más reciente al más antiguo (ID descendiente)
def obtener_ventas():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, fecha, cliente, numeros, cantidad, estado, referencia FROM ventas ORDER BY id DESC")
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

    if st.button("🗃️", use_container_width=True, help="Historial Definitivo"):
        st.session_state["menu_activo"] = "🗃️ Historial Definitivo"
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

elif menu_seleccionado == "🗃️ Historial Definitivo":
    st.markdown("#### 🗃️ Historial de Todos los Registros Definitivos")
    st.caption("Aquí puedes consultar de forma permanente todos los registros que se han ido guardando en el sistema.")

    filas_historial = obtener_ventas()
    if busqueda:
        filas_historial = [r for r in filas_historial if busqueda.lower() in f"{r[2]} {r[3]} {r[6]}".lower()]

    if not filas_historial:
        st.info("No hay registros definitivos guardados todavía.")
    else:
        total_acumulado_historial = 0
        for r in filas_historial:
            id_r, fecha_r, cliente_r, numeros_r, cantidad_r, estado_r, referencia_r = r
            monto_r = cantidad_r * precio_unitario
            total_acumulado_historial += monto_r

            with st.container(border=True):
                col_h1, col_h2, col_h3 = st.columns([2.5, 2, 1.5])
                with col_h1:
                    st.write(f"**👤 {cliente_r}** — *{estado_r}*")
                    st.caption(f"📅 Fecha: {fecha_r} | Ref: {referencia_r if referencia_r else 'Sin ref'}")
                with col_h2:
                    st.markdown(f"Cartones: `{numeros_r}`")
                    st.caption(f"Cantidad: {cantidad_r} unid.")
                with col_h3:
                    st.markdown(f"💰 **Bs. {monto_r:,.2f}**")
        
        st.divider()
        st.markdown(f"##### 💎 **Total General Histórico Recaudado: Bs. {total_acumulado_historial:,.2f}**")

elif menu_seleccionado == "🎟️ Matriz (1-630)":
    st.markdown("#### 🎟️ Matriz Visual de Cartones (1 al 630)")
    st.caption("Los números en color claro o atenuado ya se encuentran ocupados por algún jugador.")
    libres_grid = [n for n in range(1, 631) if n not in cartones_ocupados]
    img_b64_full = generar_imagen_base64(libres_grid)
    st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{img_b64_full}" style="max-width: 100%; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);"></div>', unsafe_allow_html=True)

elif menu_seleccionado == "📋 Ventas y Registro":
    with st.expander("➕ Opciones de Registro Rápido", expanded=True):
        
        # --- SECCIÓN: Lector OCR de Pago Móvil con Coincidencia Automática de Cliente ---
        st.markdown("##### 📸 Lector Automático de Pago Móvil (Captura)")
        with st.container(border=True):
            img_pago_subida = st.file_uploader("Sube la captura del pago móvil (PNG o JPG)", type=["png", "jpg", "jpeg"], key="uploader_pago_movil")
            
            if img_pago_subida:
                if not OCR_DISPONIBLE:
                    st.error("La librería 'pytesseract' no está instalada en el entorno.")
                else:
                    try:
                        imagen_pil = Image.open(img_pago_subida)
                        texto_extraido = pytesseract.image_to_string(imagen_pil)
                        
                        # Extraer referencia (últimos 6 dígitos)
                        matches_ref = re.findall(r"\b\d{6}\b", texto_extraido)
                        if not matches_ref:
                            matches_ref = re.findall(r"\b\d{4,8}\b", texto_extraido)
                        ref_detectada = matches_ref[-1][-6:] if matches_ref else ""
                        
                        # Buscar clientes pendientes en la BD para relacionarlos con el texto OCR
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("SELECT id, cliente, numeros, cantidad, referencia FROM ventas WHERE estado = 'Pendiente por Cancelar'")
                        pendientes_db = c.fetchall()
                        conn.close()
                        
                        cliente_encontrado = None
                        texto_lower = texto_extraido.lower()
                        for id_p, cli_p, nums_p, cant_p, ref_p in pendientes_db:
                            nombre_partes = cli_p.lower().split()
                            if any(parte in texto_lower for parte in nombre_partes if len(parte) > 2):
                                cliente_encontrado = (id_p, cli_p, nums_p, cant_p)
                                break
                        
                        if ref_detectada and cliente_encontrado:
                            id_c, nombre_c, nums_c, cant_c = cliente_encontrado
                            monto_c = cant_c * precio_unitario
                            
                            if "aprobaciones_ocr_pendientes" not in st.session_state:
                                st.session_state["aprobaciones_ocr_pendientes"] = []
                            
                            nueva_aprob = {"id": id_c, "cliente": nombre_c, "ref": ref_detectada, "monto": monto_c, "numeros": nums_c}
                            if nueva_aprob not in st.session_state["aprobaciones_ocr_pendientes"]:
                                st.session_state["aprobaciones_ocr_pendientes"].append(nueva_aprob)
                            
                            st.success(f"¡Coincidencia encontrada! Cliente: **{nombre_c}** | Ref: **{ref_detectada}** (Revisa abajo para dar el visto bueno)")
                        elif ref_detectada:
                            st.success(f"Referencia extraída: **{ref_detectada}** (No se asoció automáticamente a ningún pendiente, úsala en el formulario)")
                            st.session_state["ref_ocr_autocompletada"] = ref_detectada
                        else:
                            st.warning("No se pudo detectar la referencia en la imagen.")
                    except Exception as e:
                        st.error(f"Error al procesar la imagen: {e}")

        # --- PANEL DE APROBACIONES PENDIENTES OCR ---
        aprobaciones_pendientes = st.session_state.get("aprobaciones_ocr_pendientes", [])
        if aprobaciones_pendientes:
            st.markdown("---")
            st.markdown("##### 🔔 Aprobaciones Pendientes por Coincidencia OCR")
            for ap in list(aprobaciones_pendientes):
                with st.container(border=True):
                    col_ap1, col_ap2, col_ap3 = st.columns([2.5, 1.5, 1])
                    with col_ap1:
                        st.write(f"**👤 {ap['cliente']}** (Cartones: `{ap['numeros']}`)")
                        st.caption(f"Ref detectada: `{ap['ref']}` | Monto a Cancelar: **Bs. {ap['monto']:,.2f}**")
                    with col_ap2:
                        if st.button("✅ Dar Visto Bueno (Cancelar)", key=f"aprobar_ocr_{ap['id']}_{ap['ref']}", use_container_width=True):
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("UPDATE ventas SET referencia=?, estado='Cancelado' WHERE id=?", (ap['ref'], ap['id']))
                            conn.commit()
                            conn.close()
                            st.session_state["aprobaciones_ocr_pendientes"].remove(ap)
                            st.success(f"¡Pago de {ap['cliente']} aprobado y marcado como Cancelado!")
                            st.rerun()
                    with col_ap3:
                        if st.button("❌ Descartar", key=f"descartar_ocr_{ap['id']}_{ap['ref']}", use_container_width=True):
                            st.session_state["aprobaciones_ocr_pendientes"].remove(ap)
                            st.rerun()

        st.markdown("##### ➕ Registrar Manual")
        
        # Obtener referencia sugerida por OCR si existe
        ref_sugerida = st.session_state.get("ref_ocr_autocompletada", "")
        
        with st.form("form_nuevo"):
            col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
            with col_f1:
                cli_input = st.text_input("Nombre del Cliente")
            with col_f2:
                nums_input = st.text_input("Cartones (Ej: 12, 45, 100)")
            with col_f3:
                ref_input = st.text_input("Últimos 6 dígitos", value=ref_sugerida, max_chars=6)
            
            submitted = st.form_submit_button("Guardar Registro")
            
            if submitted:
                nums_val = [int(n) for n in re.findall(r"\b\d+\b", nums_input) if 1 <= int(n) <= 630]
                ref_limpia = ref_input.strip()[-6:] if ref_input.strip() else ""
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
                            "ref": ref_limpia
                        })
                        st.warning(f"⚠️ El cliente '{cli_input.strip()}' ya existe. Se ha registrado la alerta en su tarjeta abajo.")
                    else:
                        estado_reg = "Cancelado" if ref_limpia else "Pendiente por Cancelar"
                        nums_str = ", ".join(map(str, sorted(set(nums_val))))
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), cli_input.strip(), nums_str, len(set(nums_val)), estado_reg, ref_limpia))
                        conn.commit()
                        conn.close()
                        if "ref_ocr_autocompletada" in st.session_state:
                            del st.session_state["ref_ocr_autocompletada"]
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

                            ref_wpp_match = re.search(r"\b\d{6,}\b", cuerpo_mensaje)
                            if not ref_wpp_match:
                                ref_wpp_match = re.search(r"\b\d{4,6}\b", cuerpo_mensaje)
                            
                            ref_wpp = ""
                            if ref_wpp_match:
                                ref_completa = ref_wpp_match.group(0)
                                ref_wpp = ref_completa[-6:]

                            texto_lower = cuerpo_mensaje.lower()
                            
                            palabras_clave_azar = ["azar", "aleatorio", "ocupados", "si no", "o al azar"]
                            pide_azar = any(palabra in texto_lower for palabra in palabras_clave_azar)

                            todos_numeros = [int(n) for n in re.findall(r"\b\d+\b", cuerpo_mensaje)]
                            candidatos_num = [n for n in todos_numeros if 1 <= n <= 630 and len(str(n)) <= 3]
                            
                            if ref_wpp and int(ref_wpp) in candidatos_num:
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
                    if "aprobaciones_ocr_pendientes" in st.session_state:
                        st.session_state["aprobaciones_ocr_pendientes"] = []
                    st.success("¡Base de datos borrada por completo con éxito!")
                    st.rerun()

    st.divider()

    # Recargar filas de base de datos actualizadas (ordenadas del más nuevo al más antiguo)
    filas_db = obtener_ventas()
    filas_filtradas = []
    for r in filas_db:
        id_r, _, cliente, numeros, _, _, referencia = r
        texto_fila = f"{cliente} {numeros} {referencia}".lower()
        if not busqueda or busqueda.lower() in texto_fila:
            filas_filtradas.append(r)

    st.markdown("#### 📋 Listado Activo de Registros (Más Nuevos Arriba)")

    notificaciones_pendientes = st.session_state.get("pendientes_pendientes_wpp", [])

    for r in filas_filtradas:
        id_r, _, cliente, numeros, cantidad, estado, referencia = r
        cant_cartones = len(re.findall(r"\b\d+\b", numeros))
        monto_total = cant_cartones * precio_unitario
        
        notif_asociadas = [n_item for n_item in notificaciones_pendientes if n_item.get("cliente", "").strip().lower() == cliente.strip().lower()]

        with st.container(border=True):
            c_info, c_ref_input, c_acciones = st.columns([2.2, 1.8, 0.8])
            
            with c_info:
                st.write(f"**👤 {cliente}** — *{estado}*")
                st.caption(f"Cartones: {numeros} ({cant_cartones} unid.)")
                st.markdown(f"💰 **Total: Bs. {monto_total:,.2f}**")
                
                # --- ALERTA EXACTAMENTE ABAJO DEL MONTO EN BOLÍVARES ---
                for notif_asociada in notif_asociadas:
                    tipo_n = notif_asociada["tipo"]
                    
                    if tipo_n == "pendiente_nombre_duplicado":
                        if notif_asociada.get('nuevos_asignados'):
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
                                    if not notif_asociada.get('nuevos_no_disponibles'):
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                        if notif_asociada.get('nuevos_no_disponibles'):
                            cols_o1, cols_o2 = st.columns([2, 1])
                            with cols_o1:
                                texto_copiable = ", ".join(map(str, notif_asociada['nuevos_no_disponibles']))
                                st.markdown(f"🚫 **No disponible:** `{texto_copiable}`")
                            with cols_o2:
                                if st.button("❌ Borrar Notif.", key=f"cerrar_dup_{id_r}_{random.randint(100,999)}", use_container_width=True):
                                    notif_asociada['nuevos_no_disponibles'] = []
                                    if not notif_asociada.get('nuevos_asignados'):
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                    elif tipo_n == "solo_no_disponibles":
                        if notif_asociada.get('no_disponibles'):
                            cols_s1, cols_s2 = st.columns([2, 1])
                            with cols_s1:
                                texto_copiable = ", ".join(map(str, notif_asociada['no_disponibles']))
                                st.markdown(f"🚫 **No disponible:** `{texto_copiable}`")
                            with cols_s2:
                                if st.button("❌ Borrar Notif.", key=f"cerrar_solo_{id_r}_{random.randint(100,999)}", use_container_width=True):
                                    if notif_asociada in st.session_state["pendientes_pendientes_wpp"]:
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()

                    elif tipo_n == "pendiente_azar":
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
                                disponibles = [n for n in range(1, 631) if n not in ocupados_en_memoria]
                                if len(disponibles) < notif_asociada['cantidad']:
                                    st.error("No hay suficientes cartones libres.")
                                    conn.close()
                                else:
                                    seleccionados = sorted(random.sample(disponibles, notif_asociada['cantidad']))
                                    nums_db_lista = [int(n) for n in re.findall(r"\b\d+\b", numeros)]
                                    cartones_combinados = sorted(list(set(nums_db_lista + seleccionados)))
                                    nums_combinados_str = ", ".join(map(str, cartones_combinados))
                                    ref_final = referencia if referencia else notif_asociada['ref']
                                    estado_reg = "Cancelado" if ref_final else "Pendiente por Cancelar"
                                    
                                    c.execute("UPDATE ventas SET numeros=?, cantidad=?, estado=?, referencia=? WHERE id=?",
                                              (nums_combinados_str, len(cartones_combinados), estado_reg, ref_final, id_r))
                                    conn.commit()
                                    conn.close()
                                    
                                    if notif_asociada in st.session_state["pendientes_pendientes_wpp"]:
                                        st.session_state["pendientes_pendientes_wpp"].remove(notif_asociada)
                                    st.rerun()
            
            with c_ref_input:
                ref_ingresada = st.text_input("Ref (6 dígitos)", value=referencia, key=f"ref_input_{id_r}", max_chars=6, placeholder="Ej: 123456")
                nuevo_estado = "Cancelado" if ref_ingresada.strip() else "Pendiente por Cancelar"
                if ref_ingresada.strip() != referencia:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("UPDATE ventas SET referencia=?, estado=? WHERE id=?", (ref_ingresada.strip(), nuevo_estado, id_r))
                    conn.commit()
                    conn.close()
                    st.rerun()

            with c_acciones:
                st.write("")
                if st.button("🗑️", key=f"del_{id_r}", help="Eliminar registro"):
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("DELETE FROM ventas WHERE id=?", (id_r,))
                    conn.commit()
                    conn.close()
                    st.rerun()

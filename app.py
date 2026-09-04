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

# Estilos CSS para barra lateral ultra compacta (100px) y optimización máxima de espacio
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
            # Disponibles: Color negro puro y nítido
            draw.text((x, y), text, fill="#000000", font=font_grid)
        else:
            # No disponibles: Tono gris mucho más claro y translúcido (#e2e8f0)
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
    with st.expander("➕ Opciones de Registro y Asignación Rápida", expanded=True):
        
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
                nums_val = [n for n in re.findall(r"\b\d+\b", nums_input) if 1 <= int(n) <= 630]
                if not cli_input.strip():
                    st.error("Debe indicar el nombre del cliente.")
                elif not nums_val:
                    st.error("Debe indicar al menos un cartón válido (1-630).")
                else:
                    estado_reg = "Cancelado" if ref_input.strip() else "Pendiente por Cancelar"
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                              (datetime.now().strftime("%Y-%m-%d %H:%M"), cli_input.strip(), ", ".join(nums_val), len(nums_val), estado_reg, ref_input.strip()))
                    conn.commit()
                    conn.close()
                    st.success("¡Cliente registrado con éxito!")
                    st.rerun()

        st.divider()

        col_inf1, col_inf2 = st.columns(2)
        
        with col_inf1:
            st.markdown("##### 📥 Importar Directo desde WhatsApp")

            with st.form("form_whatsapp"):
                texto_wpp_unificado = st.text_area(
                    "Pega aquí todo lo resaltado en WhatsApp", 
                    placeholder="Pega aquí (Nombre del contacto arriba + mensaje abajo)..."
                )
                
                col_btn_w1, col_btn_w2 = st.columns(2)
                with col_btn_w1:
                    btn_wpp = st.form_submit_button("Procesar y Registrar", use_container_width=True)
                with col_btn_w2:
                    btn_borrar_wpp = st.form_submit_button("🗑️ Borrar", use_container_width=True)
                
                if btn_borrar_wpp:
                    st.rerun()
                
                if btn_wpp:
                    if not texto_wpp_unificado.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        # 1. Eliminar por completo cualquier formato de hora (ej: 12:34 p. m., 4:15 am, 14:30) del texto crudo
                        texto_sin_horas = re.sub(r'\b\d{1,2}:\d{2}\s*(?:p\.?\s*m\.?|a\.?\s*m\.?)?\b', '', texto_wpp_unificado, flags=re.IGNORECASE)
                        texto_sin_horas = re.sub(r'\b(?:ayer|hoy)\b', '', texto_sin_horas, flags=re.IGNORECASE)

                        # 2. Separar en líneas limpias
                        lineas_crudas = texto_sin_horas.split('\n')
                        lineas = [l.strip() for l in lineas_crudas if l.strip()]

                        nombre_cliente = ""
                        cuerpo_busqueda = texto_sin_horas

                        # 3. EXTRACCIÓN ESTRICTA DEL NOMBRE (Primera línea o primera palabra real)
                        if len(lineas) >= 1:
                            nombre_cliente = lineas[0]
                            if len(lineas) > 1:
                                cuerpo_busqueda = " ".join(lineas[1:])
                        else:
                            texto_limpio_total = re.sub(r'\s+', ' ', texto_sin_horas).strip()
                            match_primera_palabra = re.match(r"^([A-ZÁÉÍÓÚ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚ][a-záéíóúñ]+)?)", texto_limpio_total)
                            if match_primera_palabra:
                                posible_nombre = match_primera_palabra.group(1)
                                if posible_nombre.lower() not in ["buenas", "hola", "buenos", "tardes", "dias"]:
                                    nombre_cliente = posible_nombre
                                    cuerpo_busqueda = texto_limpio_total[len(posible_nombre):].strip()

                        if not nombre_cliente:
                            nombre_cliente = "Cliente WhatsApp"

                        # 4. Análisis de la acción y los números solicitados
                        texto_lower = cuerpo_busqueda.lower()
                        pide_azar = any(w in texto_lower for w in ["azar", "aleatorio", "cualquiera", "dame", "regalame", "mandame", "asigname", "ponme"])
                        
                        # Extraer todos los números enteros del cuerpo del mensaje
                        todos_numeros_cuerpo = [int(n) for n in re.findall(r"\b\d+\b", cuerpo_busqueda)]
                        
                        # Filtrar posibles cartones válidos (1 a 630)
                        nums_wpp = [str(n) for n in todos_numeros_cuerpo if 1 <= n <= 630]

                        # Detectar si está pidiendo una cantidad específica al azar (ej: "dame 5 cartones" o solo un número bajo que indique cantidad)
                        cantidad_solicitada = 0
                        if pide_azar or (len(todos_numeros_cuerpo) == 1 and todos_numeros_cuerpo[0] <= 100 and not any(n in cuerpo_busqueda for n in ["carton", "cartones"] and todos_numeros_cuerpo[0] > 20)):
                            for n_val in todos_numeros_cuerpo:
                                if n_val <= 630: # Asumimos que el número pequeño o indicado es la cantidad solicitada
                                    cantidad_solicitada = n_val
                                    break

                        # Si pide al azar de forma clara o la cantidad solicitada representa un bloque aleatorio
                        if (pide_azar and cantidad_solicitada > 0) or (len(nums_wpp) <= 1 and cantidad_solicitada > 1):
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
                            
                            if len(disponibles_reales) < cantidad_solicitada:
                                st.error(f"El cliente pide {cantidad_solicitada} cartones, pero solo quedan {len(disponibles_reales)} libres.")
                                nums_wpp = []
                            else:
                                nums_wpp = [str(n) for n in sorted(random.sample(disponibles_reales, cantidad_solicitada))]

                        if not nums_wpp:
                            st.error("No se detectaron cartones válidos (1-630) ni cantidad solicitada en el texto pegado.")
                        else:
                            # Búsqueda de referencia de pago de 6 dígitos en el texto original
                            ref_wpp_match = re.search(r"\b\d{6}\b", texto_wpp_unificado)
                            ref_wpp = ref_wpp_match.group(0) if ref_wpp_match else ""

                            estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                      (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(nums_wpp), len(nums_wpp), estado_reg, ref_wpp))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"¡Registrado! Contacto: {nombre_cliente} | Cartones: {len(nums_wpp)}")
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
                    st.warning("Base de datos limpia.")
                    st.rerun()

    st.divider()

    filas_filtradas = []
    for r in filas_db:
        id_r, _, cliente, numeros, _, _, referencia = r
        texto_fila = f"{cliente} {numeros} {referencia}".lower()
        if not busqueda or busqueda.lower() in texto_fila:
            filas_filtradas.append(r)

    st.markdown("#### 📋 Listado General de Registros")

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
                        st.markdown("##### 🎴 Editar Datos Principales")
                        nuevos_nums = st.text_input("🔢 Números de Cartón (Principal)", value=numeros, help="Modifica aquí los cartones asignados")
                        nuevo_cliente = st.text_input("👤 Nombre del Cliente", value=cliente)
                        
                        st.markdown("---")
                        st.markdown("###### ⚙️ Datos Adicionales")
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            nueva_ref = st.text_input("Ref (6 dig)", value=referencia, max_chars=6)
                        with col_e2:
                            nuevo_estado = st.selectbox("Estado", ["Pendiente por Cancelar", "Cancelado"], index=0 if estado != "Cancelado" else 1)
                        
                        if st.form_submit_button("Guardar Cambios", use_container_width=True):
                            nums_val_edit = [n for n in re.findall(r"\b\d+\b", nuevos_nums) if 1 <= int(n) <= 630]
                            if not nuevo_cliente.strip():
                                st.error("El cliente no puede estar vacío.")
                            elif not nums_val_edit:
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

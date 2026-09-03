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

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main { background-color: #0f172a; color: #f8fafc; }
    .stTextInput input, .stNumberInput input { background-color: #1e293b; color: white; border: 1px solid #334155; }
    section[data-testid="stSidebar"] { background-color: #0b1120; }
    
    /* Reducir tamaño y padding de los botones específicos de la barra lateral */
    section[data-testid="stSidebar"] div.stButton > button {
        padding: 4px 10px !important;
        font-size: 13px !important;
        min-height: 32px !important;
        border-radius: 5px !important;
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

# Función para generar la imagen con el diseño exacto de la referencia (libres grandes, ocupados pequeños)
def generar_imagen_base64(libres):
    cols = 20  # 20 columnas exactas
    total_items = 630
    rows = (total_items + cols - 1) // cols
    
    cell_w = 110  
    cell_h = 90   
    margin = 40
    header_h = 120
    
    img_w = (cols * cell_w) + (margin * 2)
    img_h = (rows * cell_h) + (margin * 2) + header_h
    
    # Fondo general blanco puro
    img = Image.new("RGB", (img_w, img_h), color="#FFFFFF")
    draw = ImageDraw.Draw(img)
    
    font_title = obtener_fuente(32)
    font_subtitle = obtener_fuente(20)
    
    # Fuentes para los números (Libres grandes y marcados; Ocupados pequeños y sutiles)
    font_grid_libres = obtener_fuente(60)
    font_grid_ocupados = obtener_fuente(22)
        
    draw.rectangle([0, 0, img_w, header_h], fill="#1e293b")
    draw.text((margin, 20), "🎴 CARTONES DISPONIBLES (1 - 630)", fill="#FFFFFF", font=font_title)
    draw.text((margin, 68), f"Disponibles: {len(libres)} / 630  |  Diseño optimizado para WhatsApp", fill="#94a3b8", font=font_subtitle)
    
    start_x = margin
    start_y = header_h + margin
    
    for n in range(1, 630 + 1):
        r = (n - 1) // cols
        c = (n - 1) % cols
        
        x1 = start_x + (c * cell_w) + 2
        y1 = start_y + (r * cell_h) + 2
        x2 = x1 + cell_w - 4
        y2 = y1 + cell_h - 4
        
        text = str(n)
        
        if n in libres:
            # Cuadro libre: Fondo blanco/claro, borde nítido y número grande
            draw.rectangle([x1, y1, x2, y2], fill="#f8fafc", outline="#94a3b8", width=2)
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font_grid_libres)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except:
                tw, th = 40, 40
                
            tx = x1 + ((x2 - x1) - tw) / 2
            ty = y1 + ((y2 - y1) - th) / 2 - 6
            
            draw.text((tx, ty), text, fill="#000000", font=font_grid_libres)
        else:
            # Cuadro ocupado: Fondo sutil y número pequeño gris (exacto a tu referencia)
            draw.rectangle([x1, y1, x2, y2], fill="#f1f5f9", outline="#e2e8f0", width=1)
            
            try:
                bbox = draw.textbbox((0, 0), text, font=font_grid_ocupados)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
            except:
                tw, th = 20, 20
                
            tx = x1 + ((x2 - x1) - tw) / 2
            ty = y1 + ((y2 - y1) - th) / 2
            
            draw.text((tx, ty), text, fill="#cbd5e1", font=font_grid_ocupados)
        
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

# Menú lateral fijo en la barra lateral con botones estilizados más compactos
with st.sidebar:
    st.markdown("### 🧭 Menú de Navegación")
    st.markdown("---")
    
    if "menu_activo" not in st.session_state:
        st.session_state["menu_activo"] = "📋 Ventas y Registro"

    if st.button("📊 Resumen General", use_container_width=True):
        st.session_state["menu_activo"] = "📊 Resumen General"
        st.rerun()
        
    if st.button("📋 Ventas y Registro", use_container_width=True):
        st.session_state["menu_activo"] = "📋 Ventas y Registro"
        st.rerun()
        
    if st.button("🎟️ Matriz (1-630)", use_container_width=True):
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
                    placeholder="Pega aquí (Nombre de WhatsApp arriba + mensaje de números abajo)..."
                )
                btn_wpp = st.form_submit_button("Procesar y Registrar")
                
                if btn_wpp:
                    if not texto_wpp_unificado.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        lineas_crudas = texto_wpp_unificado.split('\n')
                        lineas = []
                        for l in lineas_crudas:
                            l_limpia = l.strip()
                            if l_limpia:
                                if not re.fullmatch(r'\d{1,2}:\d{2}\s*(?:p\.?\s*m\.?|a\.?\s*m\.?)?', l_limpia, re.IGNORECASE):
                                    lineas.append(l_limpia)

                        nombre_cliente = "Cliente WhatsApp"
                        cuerpo_busqueda = texto_wpp_unificado

                        if len(lineas) >= 1:
                            posible_nombre = lineas[0]
                            posible_nombre = re.sub(r'\[\d{1,2}:\d{2}.*?\]', '', posible_nombre).strip()
                            if posible_nombre:
                                nombre_cliente = posible_nombre
                            if len(lineas) > 1:
                                cuerpo_busqueda = " ".join(lineas[1:])

                        nums_wpp = [n for n in re.findall(r"\b\d+\b", cuerpo_busqueda) if 1 <= int(n) <= 630]
                        if not nums_wpp:
                            nums_wpp = [n for n in re.findall(r"\b\d+\b", texto_wpp_unificado) if 1 <= int(n) <= 630]

                        ref_wpp_match = re.search(r"\b\d{6}\b", texto_wpp_unificado)
                        ref_wpp = ref_wpp_match.group(0) if ref_wpp_match else ""

                        if not nums_wpp:
                            st.error("No se detectaron cartones válidos (1-630) en el texto pegado.")
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

        with col_inf2:
            st.markdown("##### 🎲 Al Azar y 🗑️ Borrar")
            with st.container(border=True):
                cant_azar = st.number_input("Cartones al azar", min_value=1, max_value=630, value=1)
                if st.button("🎲 Asignar al Azar", use_container_width=True):
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
                
                st.markdown("---")
                if st.button("🗑️ Borrar Todo", type="primary", use_container_width=True):
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
    st.caption("✨ Visualización interactiva idéntica al diseño de tu referencia (libres destacados, ocupados sutiles)")
    
    # Matriz en pantalla replicando el mismo estilo visual de la referencia
    html_matriz = """
    <div style="background-color: #ffffff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; overflow-x: auto;">
        <div style="display: grid; grid-template-columns: repeat(20, minmax(42px, 1fr)); gap: 4px;">
    """
    
    for num in range(1, 631):
        if num in cartones_ocupados:
            html_matriz += f"""
            <div style="
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
                text-align: center;
                padding: 10px 0;
                font-family: Arial, sans-serif;
                font-weight: normal;
                font-size: 11px;
                color: #cbd5e1;
            ">{num}</div>
            """
        else:
            html_matriz += f"""
            <div style="
                background-color: #f8fafc;
                border: 2px solid #94a3b8;
                border-radius: 4px;
                text-align: center;
                padding: 10px 0;
                font-family: Arial, sans-serif;
                font-weight: 900;
                font-size: 18px;
                color: #000000;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);
            ">{num}</div>
            """
            
    html_matriz += """
        </div>
    </div>
    """
    
    components.html(html_matriz, height=750, scrolling=True)

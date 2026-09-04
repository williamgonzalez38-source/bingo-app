with col_inf1:
            st.markdown("##### 📥 Importar Directo desde WhatsApp")
            
            # Control de reseteo para el text_area dentro del formulario
            if "wpp_reset_counter" not in st.session_state:
                st.session_state["wpp_reset_counter"] = 0

            # Clave dinámica para recrear el text_area vacío cuando se pulse borrar
            wpp_key = f"input_texto_wpp_{st.session_state['wpp_reset_counter']}"

            with st.form("form_whatsapp"):
                texto_wpp_unificado = st.text_area(
                    "Pega aquí todo lo resaltado en WhatsApp", 
                    placeholder="Pega aquí (Nombre del contacto arriba + mensaje abajo)...",
                    key=wpp_key
                )
                
                col_btn_w1, col_btn_w2 = st.columns(2)
                with col_btn_w1:
                    btn_wpp = st.form_submit_button("Procesar y Registrar", use_container_width=True)
                with col_btn_w2:
                    btn_borrar_wpp = st.form_submit_button("🗑️ Borrar", use_container_width=True)
                
                if btn_borrar_wpp:
                    # Incrementamos el contador para generar una nueva instancia limpia del widget
                    st.session_state["wpp_reset_counter"] += 1
                    st.rerun()
                
                if btn_wpp:
                    if not texto_wpp_unificado.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        lineas_crudas = texto_wpp_unificado.split('\n')
                        lineas = []
                        for l in lineas_crudas:
                            l_limpia = l.strip()
                            if l_limpia:
                                if not re.fullmatch(r'[\d:\s]+(?:p\.?\s*m\.?|a\.?\s*m\.?)?', l_limpia, re.IGNORECASE):
                                    lineas.append(l_limpia)

                        # Detección ultra precisa del nombre del contacto de WhatsApp
                        nombre_cliente = "Cliente WhatsApp"
                        cuerpo_busqueda = texto_wpp_unificado

                        if len(lineas) >= 1:
                            posible_nombre = lineas[0]
                            posible_nombre = re.sub(r'\[\d{1,2}:\d{2}.*?\]', '', posible_nombre).strip()
                            posible_nombre = re.sub(r'^\+?[\d\s\-\(\)]+', '', posible_nombre).strip()
                            
                            if posible_nombre and not posible_nombre.isdigit() and len(posible_nombre) > 1:
                                nombre_cliente = posible_nombre
                            elif len(lineas) > 1:
                                posible_nombre_2 = re.sub(r'\[\d{1,2}:\d{2}.*?\]', '', lineas[1]).strip()
                                posible_nombre_2 = re.sub(r'^\+?[\d\s\-\(\)]+', '', posible_nombre_2).strip()
                                if posible_nombre_2 and not posible_nombre_2.isdigit() and len(posible_nombre_2) > 1:
                                    nombre_cliente = posible_nombre_2

                            if len(lineas) > 1:
                                cuerpo_busqueda = " ".join(lineas[1:])

                        # Detectar cartones o peticiones al azar
                        nums_wpp = [n for n in re.findall(r"\b\d+\b", cuerpo_busqueda) if 1 <= int(n) <= 630]
                        texto_lower = cuerpo_busqueda.lower()
                        pide_azar = any(w in texto_lower for w in ["azar", "aleatorio", "cualquiera", "dame", "regalame", "mandame", "asigname"]) or len(nums_wpp) <= 2 and any(c in texto_lower for c in ["carton", "cartones", "anotame", "inscribeme"])

                        cantidad_solicitada = 0
                        if pide_azar or len(nums_wpp) == 1 and int(nums_wpp[0]) <= 50:
                            for palabra in re.findall(r'\b\d+\b', cuerpo_busqueda):
                                val_num = int(palabra)
                                if val_num <= 100:
                                    cantidad_solicitada = val_num
                                    break

                        if cantidad_solicitada > 0 and (len(nums_wpp) <= 1 or pide_azar):
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
                            else:
                                nums_wpp = sorted(random.sample(disponibles_reales, cantidad_solicitada))

                        if not nums_wpp:
                            st.error("No se detectaron cartones válidos (1-630) ni cantidad solicitada en el texto pegado.")
                        else:
                            nums_wpp = [n for n in nums_wpp if 1 <= int(n) <= 630]
                            ref_wpp_match = re.search(r"\b\d{6}\b", texto_wpp_unificado)
                            ref_wpp = ref_wpp_match.group(0) if ref_wpp_match else ""

                            estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                      (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(map(str, nums_wpp)), len(nums_wpp), estado_reg, ref_wpp))
                            conn.commit()
                            conn.close()
                            
                            # Incrementamos contador para limpiar tras un registro exitoso
                            st.session_state["wpp_reset_counter"] += 1
                            st.success(f"¡Registrado! Contacto: {nombre_cliente} | Cartones: {len(nums_wpp)}")
                            st.rerun()

if btn_wpp:
                    if not texto_wpp_unificado.strip():
                        st.warning("El campo de texto está vacío.")
                    else:
                        bloques_mensajes = re.split(r'\n(?=\s*\[|\b[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+\s*:)', texto_wpp_unificado)
                        if not bloques_mensajes:
                            bloques_mensajes = [texto_wpp_unificado]

                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("SELECT numeros FROM ventas")
                        filas_actuales = c.fetchall()
                        ocupados_en_memoria = set()
                        for f_nums, in filas_actuales:
                            for n in re.findall(r"\b\d+\b", f_nums):
                                ocupados_en_memoria.add(int(n))

                        pendientes_cola = []
                        ultimo_cliente = "Cliente WhatsApp"

                        for bloque in bloques_mensajes:
                            bloque_s = bloque.strip()
                            if not bloque_s:
                                continue

                            texto_lower = bloque_s.lower()

                            nombre_cliente = ""
                            match_chat = re.search(r'\[.*?\]\s*([^:]+):', bloque_s)
                            if match_chat:
                                nombre_cliente = match_chat.group(1).strip()
                            else:
                                match_simple = re.search(r'^([a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+):', bloque_s)
                                if match_simple and len(match_simple.group(1).split()) <= 4:
                                    nombre_cliente = match_simple.group(1).strip()

                            if nombre_cliente:
                                ultimo_cliente = nombre_cliente
                            else:
                                nombre_cliente = ultimo_cliente

                            ref_wpp_match = re.search(r'(?:operación|operacion|ref|referencia)[:\s]*(\d{4,12})', texto_lower)
                            ref_wpp = ""
                            if ref_wpp_match:
                                ref_wpp = ref_wpp_match.group(1)[-6:]
                            else:
                                match_nums_largos = re.findall(r'\b\d{6,}\b', bloque_s)
                                if match_nums_largos:
                                    ref_wpp = match_nums_largos[0][-6:]

                            # Detectar si está pidiendo una cantidad específica al azar (ej: "dame 2", "dos cartones")
                            cantidad_azar_solicitada = 0
                            match_azar_cant = re.search(r'\b(\d+)\s*(?:cartones|carton|boletos|ticket)?\b', texto_lower)
                            
                            # Evitar confundir la referencia de 6 dígitos con cantidad de cartones
                            if match_azar_cant and int(match_azar_cant.group(1)) <= 50:
                                cantidad_azar_solicitada = int(match_azar_cant.group(1))

                            pide_azar = ("azar" in texto_lower or "aleatorio" in texto_lower or "más" in texto_lower or "mas" in texto_lower) and cantidad_azar_solicitada > 0

                            if pide_azar and cantidad_azar_solicitada > 0:
                                c.execute("SELECT id, numeros FROM ventas WHERE LOWER(TRIM(cliente)) = LOWER(TRIM(?))", (nombre_cliente,))
                                cliente_db_existente = c.fetchone()

                                libres_disponibles = [n for n in range(1, 631) if n not in ocupados_en_memoria]
                                if len(libres_disponibles) >= cantidad_azar_solicitada:
                                    cartones_asignados = sorted(random.sample(libres_disponibles, cantidad_azar_solicitada))
                                    for n in cartones_asignados:
                                        ocupados_en_memoria.add(n)

                                    if cliente_db_existente:
                                        # Si ya existe, lo mandamos a la cola de pendientes para sumar
                                        pendientes_cola.append({
                                            "tipo": "pendiente_nombre_duplicado",
                                            "cliente": nombre_cliente,
                                            "nuevos_asignados": cartones_asignados,
                                            "nuevos_no_disponibles": [],
                                            "ref": ref_wpp
                                        })
                                    else:
                                        estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(map(str, cartones_asignados)), len(cartones_asignados), estado_reg, ref_wpp))
                                else:
                                    pendientes_cola.append({
                                        "tipo": "pendiente_azar",
                                        "cliente": nombre_cliente,
                                        "cantidad": cantidad_azar_solicitada,
                                        "ref": ref_wpp
                                    })
                                continue

                            # Filtrado estricto para cartones específicos (números de 1 a 3 dígitos que no sean la referencia)
                            todos_numeros = [int(n) for n in re.findall(r"\b\d{1,3}\b", bloque_s)]
                            candidatos_num = []
                            seen_candidatos = set()
                            for n in todos_numeros:
                                if 1 <= n <= 630 and str(n) != ref_wpp and n not in seen_candidatos:
                                    seen_candidatos.add(n)
                                    candidatos_num.append(n)

                            cartones_asignados = []
                            cartones_no_disponibles = []

                            for num_req in candidatos_num:
                                if num_req not in ocupados_en_memoria:
                                    cartones_asignados.append(num_req)
                                else:
                                    cartones_no_disponibles.append(num_req)

                            if cartones_asignados or cartones_no_disponibles:
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
                                else:
                                    if cartones_asignados:
                                        for n in cartones_asignados:
                                            ocupados_en_memoria.add(n)

                                        estado_reg = "Cancelado" if ref_wpp else "Pendiente por Cancelar"
                                        c.execute("INSERT INTO ventas (fecha, cliente, numeros, cantidad, estado, referencia) VALUES (?, ?, ?, ?, ?, ?)",
                                                  (datetime.now().strftime("%Y-%m-%d %H:%M"), nombre_cliente, ", ".join(map(str, cartones_asignados)), len(cartones_asignados), estado_reg, ref_wpp))

                                    if cartones_no_disponibles:
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

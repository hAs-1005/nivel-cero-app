import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import datetime
import calendar
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client, Client

# --- 1. CONEXIÓN SEGURA ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Faltan las llaves en Secrets.")
    st.stop()

# --- 2. FUNCIONES DE APOYO ---

def registrar_usuario(user, pw, nombre):
    hashed_pw = stauth.Hasher([pw]).generate()[0]
    try:
        supabase.table("usuarios").insert({
            "username": user, "password_hash": hashed_pw, "name": nombre
        }).execute()
        return True
    except:
        return False

def obtener_usuarios_db():
    try:
        res = supabase.table("usuarios").select("*").execute()
        db_users = {}
        if res.data:
            for u in res.data:
                db_users[u['username']] = {'name': u['name'], 'password': u['password_hash']}
        return db_users
    except:
        return {}

def mostrar_graficos(df, habitos):
    if habitos and not df.empty:
        st.divider()
        st.subheader("📊 ANALÍTICA DE RENDIMIENTO")
        
        # --- ESTRATEGIA DE COLOR SINCRONIZADA ---
        # Creamos una paleta fija basada en los hábitos actuales
        paleta = px.colors.qualitative.Plotly  # Paleta estándar de colores distintos
        color_map = {habito: paleta[i % len(paleta)] for i, habito in enumerate(habitos)}
        
        # 1. Gráfico de Líneas (Evolución Semanal)
        df_plot = df.copy()
        df_plot['fecha'] = pd.to_datetime(df_plot['fecha'])
        df_plot['Semana'] = df_plot['fecha'].dt.isocalendar().week
        res_s = df_plot.groupby('Semana')[habitos].mean() * 100
        
        fig_line = px.line(res_s, markers=True, template="plotly_dark", 
                          title="Evolución Semanal (%)",
                          color_discrete_map=color_map) # USAR MAPA DE COLOR
        st.plotly_chart(fig_line, use_container_width=True)
        
        st.write("---")
        
        # 2. COMPARATIVA Y SCORE (En dos columnas)
        col_bar, col_pie = st.columns([2, 1])
        
        with col_bar:
            res_h = df[habitos].mean() * 100
            df_barras = pd.DataFrame({
                'Hábito': res_h.index,
                'Cumplimiento': res_h.values
            }).sort_values(by='Cumplimiento', ascending=False)
            
            # Gráfico de Barras Vertical
            fig_bar = px.bar(df_barras, x='Hábito', y='Cumplimiento',
                            template="plotly_dark", 
                            title="Comparativa de Consistencia",
                            color='Hábito', # Color basado en el nombre del hábito
                            color_discrete_map=color_map, # USAR MISMO MAPA DE COLOR
                            text_auto='.1f')
            
            fig_bar.update_layout(bargap=0.4, showlegend=False) 
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_pie:
            score = df[habitos].mean().mean() * 100
            fig_pie = go.Figure(go.Pie(labels=['Logrado', 'Pendiente'], values=[score, 100-score], 
                                 hole=.7, marker_colors=['#00ffcc', '#333333']))
            fig_pie.update_layout(template="plotly_dark", showlegend=False, title="Score Global",
                            annotations=[dict(text=f'{int(score)}%', showarrow=False, font_size=25)])
            st.plotly_chart(fig_pie, use_container_width=True)

# --- 3. INTERFAZ DE ACCESO ---
config_dict = {'usernames': obtener_usuarios_db()}
def obtener_ranking_global():
    try:
        # Traemos todos los registros de todos los usuarios
        res = supabase.table("registro_habitos").select("username, completado").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            # Calculamos el promedio de cumplimiento por usuario
            ranking = df.groupby("username")["completado"].mean() * 100
            return ranking.sort_values(ascending=False)
        return pd.Series()
    except:
        return pd.Series()
authenticator = stauth.Authenticate(config_dict, 'nivel_cero_v5', 'key_v5', cookie_expiry_days=30)

tab_login, tab_signup = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])

with tab_signup:
    st.subheader("Únete a Nivel Cero")
    new_user = st.text_input("Usuario (ID único):", key="reg_user")
    new_name = st.text_input("Tu Nombre real:", key="reg_name")
    new_pw = st.text_input("Contraseña:", type="password", key="reg_pw")
    if st.button("Registrarme ahora"):
        if new_user and new_pw and new_name:
            if registrar_usuario(new_user, new_pw, new_name):
                st.success("¡Cuenta creada exitosamente! Ya puedes iniciar sesión.")
                st.balloons()
            else:
                st.error("Error: El usuario ya existe.")
        else:
            st.warning("Completa todos los campos.")

with tab_login:
    name, authentication_status, username = authenticator.login('main')

# --- 4. PANEL PRINCIPAL ---
if authentication_status:
    st.set_page_config(page_title="Nivel Cero - Cloud Pro", layout="wide")

   # --- 4. FUNCIONES DE DATOS (DENTRO DEL LOGIN) ---
    def get_habitos(user):
        try:
            res = supabase.table("registro_habitos").select("*").eq("username", user).execute()
            if res.data and len(res.data) > 0:
                df = pd.DataFrame(res.data)
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                return df.pivot(index='fecha', columns='habito', values='completado').reset_index()
            return pd.DataFrame(columns=["fecha"])
        except:
            return pd.DataFrame(columns=["fecha"])

    def get_finanzas(user):
        try:
            res = supabase.table("finanzas").select("*").eq("username", user).execute()
            if res.data:
                return pd.DataFrame(res.data)
            return pd.DataFrame(columns=["fecha", "concepto", "monto", "tipo"])
        except:
            return pd.DataFrame(columns=["fecha", "concepto", "monto", "tipo"])

    # Carga de datos inicial
    data_db = get_habitos(username)
    finanzas_db = get_finanzas(username)
    habitos_lista = [c for c in data_db.columns if c != "fecha"]
    hoy = datetime.date.today()
    mes_act, año_act = hoy.month, hoy.year
    dias_mes = calendar.monthrange(año_act, mes_act)[1]

    # --- 5. SIDEBAR ---
    with st.sidebar:
        st.write(f"👷 Bienvenido, **{name}**")
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.divider()
        with st.expander("➕ Nuevo Hábito"):
            n_hab = st.text_input("Nombre del Hábito:")
            emo = st.text_input("Emoji:", value="✨")
            if st.button("Añadir a la Nube"):
                if n_hab:
                    supabase.table("registro_habitos").insert({"username": username, "fecha": str(hoy), "habito": f"{emo} {n_hab}", "completado": False}).execute()
                    st.rerun()
        
        if habitos_lista:
            st.divider()
            h_borrar = st.selectbox("🗑️ Eliminar Hábito", habitos_lista)
            if st.button("Confirmar Borrado"):
                supabase.table("registro_habitos").delete().eq("username", username).eq("habito", h_borrar).execute()
                st.rerun()

    st.title("📟 NIVEL CERO: HABIT TRACKER")
    st.header(f"🗓️ {calendar.month_name[mes_act].upper()} {año_act}")
    
    # --- MATRIZ DE HÁBITOS REFORMADA ---
    if not habitos_lista:
        st.info("Crea un hábito en la barra lateral.")
    else:
        # Reducimos un poco el espacio del nombre del hábito para darle más a los días
        # Usamos columnas más pequeñas para los días
        column_widths = [2.5] + [1] * dias_mes
        cols_h = st.columns(column_widths)
        
        # Encabezado de días
        for d in range(1, dias_mes + 1): 
            # Ponemos el número en pequeño para que no ocupe tanto espacio
            cols_h[d].caption(f"**{d}**")
        
        # Filas de hábitos
        for habito in habitos_lista:
            cols = st.columns(column_widths)
            # Usamos un contenedor para que el texto no se corte
            cols[0].markdown(f"<div style='font-size: 0.9rem; font-weight: bold;'>{habito}</div>", unsafe_allow_html=True)
            
            for d in range(1, dias_mes + 1):
                f_celda = datetime.date(año_act, mes_act, d)
                val = False
                
                match = data_db[data_db['fecha'] == f_celda]
                if not match.empty and habito in match.columns:
                    val = bool(match.iloc[0][habito])
                
                with cols[d]:
                    check = st.checkbox("", value=val, key=f"{habito}_{d}", label_visibility="collapsed")
                    if check != val:
                        try:
                            # 1. Enviamos el dato a Supabase
                            supabase.table("registro_habitos").upsert({
                                "username": username, "fecha": str(f_celda), 
                                "habito": habito, "completado": check
                            }, on_conflict="username,fecha,habito").execute()
                            
                            # 2. ¡CLAVE! Recargamos la app para que data_db se actualice y los gráficos cambien
                            st.rerun() 
                        except Exception as e:
                            st.error(f"Error: {e}")
    # Gráficos
    mostrar_graficos(data_db, habitos_lista)
    # --- 🏆 SECCIÓN DE COMPETENCIA (GAMIFICACIÓN) ---
    st.divider()
    st.header("🏆 LIGA NIVEL CERO")
    
    ranking_data = obtener_ranking_global()
    
    if not ranking_data.empty:
        col_rank, col_medalla = st.columns([2, 1])
        
        with col_rank:
            st.subheader("Cuadro de Honor")
            df_rank = ranking_data.reset_index()
            df_rank.columns = ['Usuario', 'Consistencia %']
            df_rank['Consistencia %'] = df_rank['Consistencia %'].map('{:.1f}%'.format)
            st.table(df_rank)

        with col_medalla:
            st.subheader("Tu Estatus")
            mi_score = ranking_data.get(username, 0)
            
            if mi_score >= 90:
                st.write("🏅 **Rango: Oro**")
                st.info("¡Eres una máquina! Estás en el nivel de élite.")
            elif mi_score >= 70:
                st.write("🥈 **Rango: Plata**")
                st.warning("Muy buena constancia, ¡sigue así!")
            elif mi_score >= 50:
                st.write("🥉 **Rango: Bronce**")
                st.write("Estás en el camino, pero falta apretar el paso.")
            else:
                st.write("👷 **Rango: Papel Higienico**")
                st.error("¡Cuidado! Tu consistencia está baja.")
    else:
        st.info("Aún no hay suficientes datos para generar el ranking.")

    # --- 6. FINANZAS CLOUD (VERSIÓN BLINDADA) ---
    st.divider()
    st.header("💰 FINANZAS CLOUD")
    f1, f2, f3 = st.columns(3)
    
    with f1:
        m_in = st.number_input("Ingreso:", min_value=0.0, key="fin_in")
        d_in = st.text_input("Fuente:", key="src_in")
        if st.button("➕ Ingreso"):
            if m_in > 0:
                try:
                    supabase.table("finanzas").insert({
                        "username": username, "monto": m_in, "concepto": d_in, 
                        "tipo": "Ingreso", "fecha": str(hoy)
                    }).execute()
                    st.success("✅ Ingreso registrado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")

    with f2:
        m_ga = st.number_input("Gasto:", min_value=0.0, key="fin_ga")
        d_ga = st.text_input("Concepto:", key="src_ga")
        if st.button("➖ Gasto"):
            if m_ga > 0:
                try:
                    supabase.table("finanzas").insert({
                        "username": username, "monto": m_ga, "concepto": d_ga, 
                        "tipo": "Gasto", "fecha": str(hoy)
                    }).execute()
                    st.success("✅ Gasto registrado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")

    with f3:
        m_ah = st.number_input("Ahorro:", min_value=0.0, key="fin_ah")
        if st.button("🎯 Ahorro"):
            if m_ah > 0:
                try:
                    # AQUÍ ESTABA EL ERROR (LÍNEA 197)
                    supabase.table("finanzas").insert({
                        "username": username, "monto": m_ah, "concepto": "Ahorro", 
                        "tipo": "Ahorro", "fecha": str(hoy)
                    }).execute()
                    st.success("✅ Ahorro registrado")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error de base de datos: {e}")

    # Cálculo de métricas (Protección contra datos vacíos)
    if not finanzas_db.empty:
        ti = finanzas_db[finanzas_db['tipo'] == 'Ingreso']['monto'].sum()
        tg = finanzas_db[finanzas_db['tipo'] == 'Gasto']['monto'].sum()
        ta = finanzas_db[finanzas_db['tipo'] == 'Ahorro']['monto'].sum()
        st.metric("Saldo Disponible Real", f"${ti - tg - ta:,.2f}")
        
        with st.expander("📂 Historial de Movimientos"):
            st.dataframe(finanzas_db[['fecha', 'concepto', 'monto', 'tipo']].sort_values(by='fecha', ascending=False), use_container_width=True)
    else:
        st.metric("Saldo Disponible Real", "$0.00")
        st.info("Aún no hay movimientos registrados.")

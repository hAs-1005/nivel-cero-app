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

# --- 2. LÓGICA DE USUARIOS DESDE LA NUBE ---
def registrar_usuario(user, pw, nombre):
    # Encriptamos la contraseña por seguridad de ingeniería
    hashed_pw = stauth.Hasher([pw]).generate()[0]
    try:
        supabase.table("usuarios").insert({
            "username": user, 
            "password_hash": hashed_pw, 
            "name": nombre
        }).execute()
        return True
    except Exception as e:
        return False

def obtener_usuarios_db():
    try:
        res = supabase.table("usuarios").select("*").execute()
        db_users = {}
        if res.data:
            for u in res.data:
                db_users[u['username']] = {
                    'name': u['name'],
                    'password': u['password_hash']
                }
        return db_users
    except:
        return {}

# Cargamos los usuarios registrados en Supabase
config_dict = {'usernames': obtener_usuarios_db()}

# Importante: Cambiamos el nombre de la cookie para refrescar la sesión
authenticator = stauth.Authenticate(
    config_dict,
    'nivel_cero_auto_registro', 'key_auto', cookie_expiry_days=30
)

# --- 3. INTERFAZ DE ACCESO (TABS) ---
tab_login, tab_signup = st.tabs(["🔑 Iniciar Sesión", "📝 Crear Cuenta"])

with tab_signup:
    st.subheader("Únete a Nivel Cero")
    new_user = st.text_input("Usuario (ID único):", key="reg_user")
    new_name = st.text_input("Tu Nombre real:", key="reg_name")
    new_pw = st.text_input("Contraseña:", type="password", key="reg_pw")
    if st.button("Registrarme ahora"):
        if new_user and new_pw and new_name:
            if registrar_usuario(new_user, new_pw, new_name):
                st.success("¡Cuenta creada exitosamente! Ahora ve a la pestaña de Iniciar Sesión.")
                st.balloons()
            else:
                st.error("Error: El usuario ya existe o hubo un problema con la base de datos.")
        else:
            st.warning("Por favor, completa todos los campos.")

with tab_login:
    name, authentication_status, username = authenticator.login('main')

# --- 4. CONTINUACIÓN DEL PROGRAMA ---
if authentication_status:
    # A partir de aquí mantienes todo tu código original (st.set_page_config, get_habitos, etc.)

if authentication_status:
    st.set_page_config(page_title="Nivel Cero - Cloud Pro", layout="wide")

    # --- FUNCIONES DE BASE DE DATOS ---
    def get_habitos(user):
        try:
            # Añadimos un bloque try/except para capturar el error exacto
            res = supabase.table("registro_habitos").select("*").eq("username", user).execute()
            
            # Verificamos que realmente haya datos antes de procesar
            if res.data and len(res.data) > 0:
                df = pd.DataFrame(res.data)
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                return df.pivot(index='fecha', columns='habito', values='completado').reset_index()
            
            return pd.DataFrame(columns=["fecha"])
        except Exception as e:
            # Esto nos dirá en la pantalla de la app QUÉ está fallando
            st.error(f"Error técnico de conexión: {e}")
            return pd.DataFrame(columns=["fecha"])
            
    def get_finanzas(user):
        res = supabase.table("finanzas").select("*").eq("username", user).execute()
        return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["fecha", "concepto", "monto", "tipo"])

    # Carga de datos
    data_db = get_habitos(username)
    finanzas_db = get_finanzas(username)
    habitos_lista = [c for c in data_db.columns if c != "fecha"]
    hoy = datetime.date.today()
    mes_act = hoy.month
    año_act = hoy.year
    dias_mes = calendar.monthrange(año_act, mes_act)[1]

    # --- SIDEBAR ACTUALIZADA ---
    with st.sidebar:
        st.write(f"👷 Ingeniero: **{name}**")
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.divider()
        
        with st.expander("➕ Nuevo Hábito"):
            n_hab = st.text_input("Nombre del hábito:")
            
            # Biblioteca rápida de sugerencias
            st.caption("Sugerencias:")
            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
            with col_e1: st.code("🏗️ 🧱 📏")
            with col_e2: st.code("📉 💰 💳")
            with col_e3: st.code("🏃 🥗 💧")
            with col_e4: st.code("📖 ✍️ 💻")
            
            # Entrada libre para cualquier emoji
            emo = st.text_input("Pega aquí tu Emoji (Win + . en PC):", value="✨")
            
            if st.button("Añadir a la Nube"):
                if n_hab:
                    # Insertamos en Supabase
                    supabase.table("registro_habitos").insert({
                        "username": username, 
                        "fecha": str(hoy), 
                        "habito": f"{emo} {n_hab}", 
                        "completado": False
                    }).execute()
                    st.success(f"Hábito '{n_hab}' creado")
                    st.rerun()
                else:
                    st.warning("Escribe un nombre para el hábito.")
        
        if habitos_lista:
            st.divider()
            h_borrar = st.selectbox("🗑️ Eliminar Hábito", habitos_lista)
            if st.button("Confirmar Borrado"):
                supabase.table("registro_habitos").delete().eq("username", username).eq("habito", h_borrar).execute()
                st.rerun()

    # --- MATRIZ ---
    st.title("📟 NIVEL CERO: DATABASE CONTROL")
    st.header(f"🗓️ {calendar.month_name[mes_act].upper()} {año_act}")

    if not habitos_lista:
        st.info("Agrega un hábito para comenzar.")
    else:
        cols_h = st.columns([3.5] + [1] * dias_mes)
        for d in range(1, dias_mes + 1): cols_h[d].write(f"**{d}**")
        
        for habito in habitos_lista:
            cols = st.columns([3.5] + [1] * dias_mes)
            cols[0].markdown(f"**{habito}**")
            for d in range(1, dias_mes + 1):
                f_celda = datetime.date(año_act, mes_act, d)
                val = False
                match = data_db[data_db['fecha'] == f_celda]
                if not match.empty and habito in match.columns:
                    val = bool(match.iloc[0][habito])
                
                with cols[d]:
                    check = st.checkbox("", value=val, key=f"{habito}_{d}")
                    if check != val:
                        supabase.table("registro_habitos").upsert({"username": username, "fecha": str(f_celda), "habito": habito, "completado": check}).execute()

    # --- ANALÍTICA ---
    if habitos_lista:
        st.divider()
        c_l, c_p = st.columns([2, 1])
        with c_l:
            df_plot = data_db.copy()
            df_plot['fecha'] = pd.to_datetime(df_plot['fecha'])
            df_plot['Semana'] = df_plot['fecha'].dt.isocalendar().week
            res_s = df_plot.groupby('Semana')[habitos_lista].mean() * 100
            st.plotly_chart(px.line(res_s, markers=True, template="plotly_dark", title="Rendimiento Semanal %"), use_container_width=True)
        with c_p:
            score = data_db[habitos_lista].values.mean() * 100
            fig_g = go.Figure(go.Pie(labels=['Logrado', 'Pendiente'], values=[score, 100-score], hole=.7, marker_colors=['#00ffcc', '#333333']))
            fig_g.update_layout(template="plotly_dark", showlegend=False, annotations=[dict(text=f'{int(score)}%', showarrow=False, font_size=30)])
            st.plotly_chart(fig_g, use_container_width=True)

    # --- FINANZAS ---
    st.divider()
    st.header("💰 GESTIÓN FINANCIERA CLOUD")
    f1, f2, f3 = st.columns(3)
    with f1:
        m_in = st.number_input("Monto Recibido:", min_value=0.0, key="fin_in")
        d_in = st.text_input("Fuente:", key="src_in")
        if st.button("➕ Ingreso"):
            supabase.table("finanzas").insert({"username": username, "monto": m_in, "concepto": d_in, "tipo": "Ingreso", "fecha": str(hoy)}).execute()
            st.rerun()
    with f2:
        m_ga = st.number_input("Monto Gasto:", min_value=0.0, key="fin_ga")
        d_ga = st.text_input("Concepto:", key="src_ga")
        if st.button("➖ Gasto"):
            supabase.table("finanzas").insert({"username": username, "monto": m_ga, "concepto": d_ga, "tipo": "Gasto", "fecha": str(hoy)}).execute()
            st.rerun()
    with f3:
        m_ah = st.number_input("Monto Ahorro:", min_value=0.0, key="fin_ah")
        f_ah = st.date_input("Fecha Objetivo:", value=hoy)
        if st.button("🎯 Ahorro"):
            supabase.table("finanzas").insert({"username": username, "monto": m_ah, "concepto": "Ahorro", "tipo": "Ahorro", "fecha": str(f_ah)}).execute()
            st.rerun()

    ti = finanzas_db[finanzas_db['tipo'] == 'Ingreso']['monto'].sum()
    tg = finanzas_db[finanzas_db['tipo'] == 'Gasto']['monto'].sum()
    ta = finanzas_db[finanzas_db['tipo'] == 'Ahorro']['monto'].sum()
    saldo = ti - tg - ta
    st.metric("Saldo Disponible Real", f"${saldo:,.2f}")

    if not finanzas_db.empty:
        with st.expander("📂 Historial Nube"):
            sel = st.multiselect("Eliminar movimientos:", finanzas_db.index)
            if st.button("Eliminar"):
                for s in sel: supabase.table("finanzas").delete().eq("id", int(finanzas_db.loc[s, 'id'])).execute()
                st.rerun()
            st.dataframe(finanzas_db, use_container_width=True)

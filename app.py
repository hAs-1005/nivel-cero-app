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
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 1. Gráfico de Líneas: Evolución Semanal
            df_plot = df.copy()
            df_plot['fecha'] = pd.to_datetime(df_plot['fecha'])
            df_plot['Semana'] = df_plot['fecha'].dt.isocalendar().week
            res_s = df_plot.groupby('Semana')[habitos].mean() * 100
            st.plotly_chart(px.line(res_s, markers=True, template="plotly_dark", 
                                  title="Evolución Semanal por Hábito (%)",
                                  labels={'value': '% Logro', 'Semana': 'Semana del Año'}), 
                          use_container_width=True)
            
            # 2. NUEVO: Gráfico de Barras - Comparativa Individual
            st.write("---")
            res_h = df[habitos].mean().sort_values(ascending=True) * 100
            fig_bar = px.bar(x=res_h.values, y=res_h.index, orientation='h',
                            template="plotly_dark", title="Podio de Consistencia por Hábito",
                            labels={'x': '% Total de Cumplimiento', 'y': 'Hábito'},
                            color=res_h.values, color_continuous_scale='Greens')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col2:
            # 3. Gráfico de Dona: Score Global del Mes
            score = df[habitos].mean().mean() * 100
            fig = go.Figure(go.Pie(labels=['Logrado', 'Pendiente'], values=[score, 100-score], 
                                 hole=.7, marker_colors=['#00ffcc', '#333333']))
            fig.update_layout(template="plotly_dark", showlegend=False, title="Score Global Mensual",
                            annotations=[dict(text=f'{int(score)}%', showarrow=False, font_size=30)])
            st.plotly_chart(fig, use_container_width=True)

# --- 3. INTERFAZ DE ACCESO ---
config_dict = {'usernames': obtener_usuarios_db()}
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

    def get_habitos(user):
        try:
            res = supabase.table("registro_habitos").select("*").eq("username", user).execute()
            if res.data and len(res.data) > 0:
                df = pd.DataFrame(res.data)
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                return df.pivot(index='fecha', columns='habito', values='completado').reset_index()
            return pd.DataFrame(columns=["fecha"])
        except: return pd.DataFrame(columns=["fecha"])

    def get_finanzas(user):
        try:
            res = supabase.table("finanzas").select("*").eq("username", user).execute()
            return pd.DataFrame(res.data) if res.data else pd.DataFrame(columns=["fecha", "concepto", "monto", "tipo"])
        except: return pd.DataFrame(columns=["fecha", "concepto", "monto", "tipo"])

    data_db = get_habitos(username)
    finanzas_db = get_finanzas(username)
    habitos_lista = [c for c in data_db.columns if c != "fecha"]
    hoy = datetime.date.today()
    mes_act, año_act = hoy.month, hoy.year
    dias_mes = calendar.monthrange(año_act, mes_act)[1]

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
    
    if not habitos_lista:
        st.info("Crea un hábito en la barra lateral para comenzar a trackear.")
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
                        supabase.table("registro_habitos").upsert({
                            "username": username, "fecha": str(f_celda), 
                            "habito": habito, "completado": check
                        }).execute()

    # Invocamos la analítica completa
    mostrar_graficos(data_db, habitos_lista)

    st.divider()
    st.header("💰 FINANZAS CLOUD")
    f1, f2, f3 = st.columns(3)
    with f1:
        m_in = st.number_input("Monto Ingreso:", min_value=0.0, key="fin_in")
        d_in = st.text_input("Fuente de ingreso:", key="src_in")
        if st.button("➕ Registrar Ingreso"):
            if m_in > 0:
                supabase.table("finanzas").insert({"username": username, "monto": m_in, "concepto": d_in, "tipo": "Ingreso", "fecha": str(hoy)}).execute()
                st.rerun()
    with f2:
        m_ga = st.number_input("Monto Gasto:", min_value=0.0, key="fin_ga")
        d_ga = st.text_input("Concepto del gasto:", key="src_ga")
        if st.button("➖ Registrar Gasto"):
            if m_ga > 0:
                supabase.table("finanzas").insert({"username": username, "monto": m_ga, "concepto": d_ga, "tipo": "Gasto", "fecha": str(hoy)}).execute()
                st.rerun()
    with f3:
        m_ah = st.number_input("Monto Ahorro:", min_value=0.0, key="fin_ah")
        if st.button("🎯 Registrar Ahorro"):
            if m_ah > 0:
                supabase.table("finanzas").insert({"username": username, "monto": m_ah, "concepto": "Ahorro", "tipo": "Ahorro", "fecha": str(hoy)}).execute()
                st.rerun()

    ti = finanzas_db[finanzas_db['tipo'] == 'Ingreso']['monto'].sum()
    tg = finanzas_db[finanzas_db['tipo'] == 'Gasto']['monto'].sum()
    ta = finanzas_db[finanzas_db['tipo'] == 'Ahorro']['monto'].sum()
    st.metric("Saldo Disponible Real", f"${ti - tg - ta:,.2f}")
    
    if not finanzas_db.empty:
        with st.expander("📂 Ver Historial de Movimientos"):
            st.dataframe(finanzas_db[['fecha', 'concepto', 'monto', 'tipo']], use_container_width=True)

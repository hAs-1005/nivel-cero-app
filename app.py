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

# --- 2. FUNCIONES DE APOYO (LÓGICA SEPARADA) ---

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
    """Función modular para los gráficos. Fácil de editar sin romper el resto."""
    if habitos and not df.empty:
        st.divider()
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de Líneas: Rendimiento Semanal
            df_plot = df.copy()
            df_plot['fecha'] = pd.to_datetime(df_plot['fecha'])
            df_plot['Semana'] = df_plot['fecha'].dt.isocalendar().week
            res_s = df_plot.groupby('Semana')[habitos].mean() * 100
            st.plotly_chart(px.line(res_s, markers=True, template="plotly_dark", 
                                  title="Rendimiento Semanal %", labels={'value': 'Logro %'}), 
                          use_container_width=True)
            
        with col2:
            # Gráfico de Dona: Score Global
            score = df[habitos].mean().mean() * 100
            fig = go.Figure(go.Pie(labels=['Logrado', 'Pendiente'], values=[score, 100-score], 
                                 hole=.7, marker_colors=['#00ffcc', '#333333']))
            fig.update_layout(template="plotly_dark", showlegend=False, title="Score Global",
                            annotations=[dict(text=f'{int(score)}%', showarrow=False, font_size=25)])
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
                st.success("¡Cuenta

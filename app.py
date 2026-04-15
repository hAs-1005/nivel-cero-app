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
    new_user = st.

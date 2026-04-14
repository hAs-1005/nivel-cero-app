import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import datetime
import calendar
import plotly.express as px
import plotly.graph_objects as go
import os

# --- 1. CONFIGURACIÓN DE SEGURIDAD (LOGIN) ---
# Definimos los usuarios autorizados
names = ['Usuario Maestro']
usernames = ['admin']
# Nota: En una app real, estas contraseñas deben estar encriptadas (hashed)
passwords = ['admin123'] 

authenticator = stauth.Authenticate(
    {'usernames': {
        usernames[0]: {'name': names[0], 'password': passwords[0]}
    }},
    'nivel_cero_cookie',
    'signature_key',
    cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login('main')

if authentication_status == False:
    st.error('Usuario o contraseña incorrectos')
elif authentication_status == None:
    st.warning('Por favor, ingresa tus credenciales para acceder.')
elif authentication_status:

    # --- 2. CONFIGURACIÓN VISUAL Y ARCHIVOS ---
    st.set_page_config(page_title="Nivel Cero - Pro System", layout="wide")
    
    st.markdown("""
        <style>
        .main { background-color: #0e1117; }
        .habito-label { font-weight: bold; color: #00ffcc; font-size: 16px; white-space: nowrap; }
        .stCheckbox { margin-bottom: -15px; }
        .finance-card { background-color: #1e2130; padding: 20px; border-radius: 10px; border-left: 5px solid #00ffcc; margin-bottom: 20px; }
        </style>
        """, unsafe_allow_html=True)

    # Archivos específicos para cada usuario
    DB_FILE = f"registro_habitos_{username}.csv"
    FINANCE_FILE = f"finanzas_dinamicas_{username}.csv"

    def cargar_datos():
        if os.path.exists(DB_FILE):
            df = pd.read_csv(DB_FILE)
            df['Fecha'] = pd.to_datetime(df['Fecha']).dt.date
            return df
        return pd.DataFrame(columns=["Fecha"])

    def cargar_finanzas():
        if os.path.exists(FINANCE_FILE):
            df = pd.read_csv(FINANCE_FILE)
            df['Fecha'] = pd.to_datetime(df['Fecha']).dt.date
            return df
        return pd.DataFrame(columns=["Fecha", "Concepto", "Monto", "Tipo"])

    def guardar(df, file):
        df.to_csv(file, index=False)

    # Carga de datos
    data = cargar_datos()
    finanzas = cargar_finanzas()
    hoy = datetime.date.today()
    mes_actual = hoy.month
    año_actual = hoy.year
    dias_del_mes = calendar.monthrange(año_actual, mes_actual)[1]
    habitos_lista = [c for c in data.columns if c != "Fecha"]

    # --- 3. BARRA LATERAL (GESTIÓN) ---
    with st.sidebar:
        st.write(f"🔐 Sesión iniciada como: **{name}**")
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.divider()
        st.header("⚙️ Configuración")
        
        with st.expander("➕ Añadir Hábito"):
            nuevo_nom = st.text_input("Nombre:")
            nuevo_emoji = st.selectbox("Emoji:", ["📚", "💪", "💰", "🍬", "🏗️", "🛹", "🎯", "🚿"])
            if st.button("Confirmar"):
                nombre_completo = f"{nuevo_emoji} {nuevo_nom}"
                if nuevo_nom and nombre_completo not in data.columns:
                    data[nombre_completo] = 0
                    guardar(data, DB_FILE)
                    st.rerun()

        if habitos_lista:
            st.divider()
            habito_a_borrar = st.selectbox("🗑️ Eliminar Hábito:", habitos_lista)
            if st.button("Eliminar"):
                data = data.drop(columns=[habito_a_borrar])
                guardar(data, DB_FILE)
                st.rerun()

    # --- 4. SECCIÓN DE HÁBITOS ---
    st.title(f"📟 PANEL DE CONTROL: {name.upper()}")
    st.header(f"🗓️ {calendar.month_name[mes_actual].upper()} {año_actual}")

    if not habitos_lista:
        st.info("Añade un hábito en la barra lateral para comenzar.")
    else:
        # Matriz
        cols_header = st.columns([3.5] + [1] * dias_del_mes)
        cols_header[0].write("**HÁBITO**")
        for d in range(1, dias_del_mes + 1):
            cols_header[d].write(f"**{d}**")

        for habito in habitos_lista:
            cols = st.columns([3.5] + [1] * dias_del_mes)
            cols[0].markdown(f"<div class='habito-label'>{habito}</div>", unsafe_allow_html=True)
            for d in range(1, dias_del_mes + 1):
                f_celda = datetime.date(año_actual, mes_actual, d)
                existe = data[data['Fecha'] == f_celda]
                val_init = bool(existe.iloc[0][habito]) if not existe.empty else False
                with cols[d]:
                    check = st.checkbox("", value=val_init, key=f"{habito}_{d}")
                    if existe.empty:
                        nueva = {col: 0 for col in data.columns}; nueva["Fecha"] = f_celda; nueva[habito] = 1 if check else 0
                        data = pd.concat([data, pd.DataFrame([nueva])], ignore_index=True)
                    else:
                        data.loc[data['Fecha'] == f_celda, habito] = 1 if check else 0

        if st.button("💾 GUARDAR REGISTRO"):
            guardar(data, DB_FILE)
            st.toast("Datos guardados")

    # --- 5. ANALÍTICA ---
    if not data.empty and len(habitos_lista) > 0:
        st.divider()
        col_l, col_p = st.columns([2, 1])
        with col_l:
            df_s = data.copy(); df_s['Fecha'] = pd.to_datetime(df_s['Fecha'])
            df_s['Semana'] = df_s['Fecha'].dt.isocalendar().week
            res_s = df_s.groupby('Semana')[habitos_lista].mean() * 100
            fig_l = px.line(res_s, markers=True, template="plotly_dark", title="Rendimiento Semanal %")
            st.plotly_chart(fig_l, use_container_width=True)
        with col_p:
            global_score = data[habitos_lista].values.mean() * 100
            fig_g = go.Figure(go.Pie(labels=['Logrado', 'Pendiente'], values=[global_score, 100-global_score], hole=.7))
            fig_g.update_layout(template="plotly_dark", showlegend=False, annotations=[dict(text=f'{int(global_score)}%', showarrow=False, font_size=30)])
            st.plotly_chart(fig_g, use_container_width=True)

    # --- 6. FINANZAS ---
    st.divider()
    st.header("💰 GESTIÓN FINANCIERA")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='finance-card'>", unsafe_allow_html=True)
        st.subheader("Ingresos")
        m_in = st.number_input("Monto ($)", min_value=0.0, key="m_in")
        d_in = st.text_input("Fuente:", key="d_in")
        if st.button("➕ Añadir"):
            finanzas = pd.concat([finanzas, pd.DataFrame([{"Fecha": hoy, "Concepto": d_in, "Monto": m_in, "Tipo": "Ingreso"}])], ignore_index=True)
            guardar(finanzas, FINANCE_FILE); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='finance-card'>", unsafe_allow_html=True)
        st.subheader("Gastos")
        m_ga = st.number_input("Monto ($)", min_value=0.0, key="m_ga")
        d_ga = st.text_input

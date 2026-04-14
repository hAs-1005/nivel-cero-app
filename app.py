import streamlit as st
import pandas as pd
import datetime
import calendar
import plotly.express as px
import plotly.graph_objects as go
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Nivel Cero - Control Total", layout="wide")

# --- ESTILO VISUAL (NEÓN & DARK) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .habito-label { font-weight: bold; color: #00ffcc; font-size: 16px; white-space: nowrap; }
    .stCheckbox { margin-bottom: -15px; }
    .finance-card { 
        background-color: #1e2130; 
        padding: 20px; 
        border-radius: 10px; 
        border-left: 5px solid #00ffcc; 
        margin-bottom: 20px; 
    }
    </style>
    """, unsafe_allow_html=True)

# --- GESTIÓN DE ARCHIVOS ---
DB_FILE = "registro_habitos.csv"
FINANCE_FILE = "finanzas_dinamicas.csv"

def cargar_datos():
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE)
        df['Fecha'] = pd.to_datetime(df['Fecha']).dt.date
        return df
    return pd.DataFrame(columns=["Fecha"]) # Lista vacía de inicio

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

# Colores para hábitos
colores_dict = {habito: px.colors.qualitative.Bold[i % len(px.colors.qualitative.Bold)] 
                for i, habito in enumerate(habitos_lista)}

# --- BARRA LATERAL (GESTIÓN DE HÁBITOS) ---
with st.sidebar:
    st.header("⚙️ Gestión de Hábitos")
    
    # Añadir Hábito
    with st.expander("➕ Añadir Nuevo"):
        nuevo_nom = st.text_input("Nombre:")
        nuevo_emoji = st.selectbox("Emoji:", ["📚", "💪", "💰", "🍬", "🏗️", "📓", "🔋", "🛹", "🎯", "🚿"])
        if st.button("Confirmar Hábito"):
            nombre_completo = f"{nuevo_emoji} {nuevo_nom}"
            if nuevo_nom and nombre_completo not in data.columns:
                data[nombre_completo] = 0
                guardar(data, DB_FILE)
                st.rerun()

    # Eliminar Hábito
    if habitos_lista:
        st.divider()
        st.subheader("🗑️ Eliminar Hábito")
        habito_a_borrar = st.selectbox("Selecciona:", habitos_lista)
        if st.button("Eliminar seleccionado"):
            data = data.drop(columns=[habito_a_borrar])
            guardar(data, DB_FILE)
            st.rerun()

# --- SECCIÓN 1: MATRIZ DE HÁBITOS ---
st.title("📟 NIVEL CERO: SISTEMA INTEGRAL")
st.header(f"🗓️ {calendar.month_name[mes_actual].upper()} {año_actual}")

if not habitos_lista:
    st.info("Comienza añadiendo un hábito en el panel de la izquierda ⬅️")
else:
    # Matriz interactiva
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

    if st.button("💾 GUARDAR REGISTRO DIARIO"):
        guardar(data, DB_FILE)
        st.toast("Datos guardados")

# --- SECCIÓN 2: ANALÍTICA ---
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

# --- SECCIÓN 3: FINANZAS DINÁMICAS ---
st.divider()
st.header("💰 GESTIÓN FINANCIERA")

c_ing, c_gas, c_aho = st.columns(3)

with c_ing:
    st.markdown("<div class='finance-card'>", unsafe_allow_html=True)
    st.subheader("Ingresos")
    m_in = st.number_input("Monto ($)", min_value=0.0, key="m_in")
    d_in = st.text_input("Fuente:", key="d_in")
    if st.button("➕ Añadir Ingreso"):
        finanzas = pd.concat([finanzas, pd.DataFrame([{"Fecha": hoy, "Concepto": d_in, "Monto": m_in, "Tipo": "Ingreso"}])], ignore_index=True)
        guardar(finanzas, FINANCE_FILE); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with c_gas:
    st.markdown("<div class='finance-card'>", unsafe_allow_html=True)
    st.subheader("Gastos")
    m_ga = st.number_input("Monto ($)", min_value=0.0, key="m_ga")
    d_ga = st.text_input("Concepto:", key="d_ga")
    f_ga = st.date_input("Fecha:", value=hoy, key="f_ga")
    if st.button("➖ Añadir Gasto"):
        finanzas = pd.concat([finanzas, pd.DataFrame([{"Fecha": f_ga, "Concepto": d_ga, "Monto": m_ga, "Tipo": "Gasto"}])], ignore_index=True)
        guardar(finanzas, FINANCE_FILE); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

with c_aho:
    st.markdown("<div class='finance-card'>", unsafe_allow_html=True)
    st.subheader("Ahorro")
    m_ah = st.number_input("Monto ($)", min_value=0.0, key="m_ah")
    f_ah = st.date_input("Fecha objetivo:", value=hoy, key="f_ah")
    if st.button("🎯 Fijar Ahorro"):
        finanzas = pd.concat([finanzas, pd.DataFrame([{"Fecha": f_ah, "Concepto": "Ahorro", "Monto": m_ah, "Tipo": "Ahorro"}])], ignore_index=True)
        guardar(finanzas, FINANCE_FILE); st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# --- BALANCE Y BORRADO DE REGISTROS ---
t_i = finanzas[finanzas['Tipo'] == 'Ingreso']['Monto'].sum()
t_g = finanzas[finanzas['Tipo'] == 'Gasto']['Monto'].sum()
t_a = finanzas[finanzas['Tipo'] == 'Ahorro']['Monto'].sum()
saldo = t_i - t_g - t_a

st.subheader(f"Balance: ${saldo:,.2f}")

if not finanzas.empty:
    with st.expander("📂 Gestionar Historial (Eliminar errores)"):
        # Mostramos tabla con índice para borrar
        df_display = finanzas.copy()
        borrar_idx = st.multiselect("Selecciona los registros a eliminar:", df_display.index)
        if st.button("Borrar seleccionados"):
            finanzas = finanzas.drop(borrar_idx)
            guardar(finanzas, FINANCE_FILE)
            st.rerun()
        st.dataframe(df_display, use_container_width=True)

# Termómetro
fig_t = go.Figure(go.Indicator(mode="gauge+number", value=saldo, 
    gauge={'shape': "bullet", 'axis': {'range': [None, max(t_i, 1000)]}, 'bar': {'color': "#00ffcc" if saldo > 0 else "red"}}))
fig_t.update_layout(height=150, template="plotly_dark")
st.plotly_chart(fig_t, use_container_width=True)
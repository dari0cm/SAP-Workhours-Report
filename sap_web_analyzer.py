import streamlit as st
import pandas as pd
import re
import ast
from datetime import datetime, date
import plotly.express as px

HORAS_TEORICAS_DIA = 8.0

st.set_page_config(
    page_title="Panel de Control Horas SAP",
    layout="wide"
)

st.title("⏱ Panel de Control de Horas SAP")
st.markdown("Análisis, simulación y seguimiento de jornada laboral")

# ---------------------------------------------------
# FUNCIONES
# ---------------------------------------------------

def asegurar_orden(fichajes):
    corregido = []
    for entrada, salida in fichajes:
        if entrada > salida:
            entrada, salida = salida, entrada
        corregido.append((entrada, salida))
    corregido.sort()
    return corregido


def calcular_horas(fichajes):
    total = 0
    for entrada, salida in fichajes:
        t1 = datetime.strptime(entrada, "%H:%M")
        t2 = datetime.strptime(salida, "%H:%M")
        total += (t2 - t1).seconds / 3600
    return round(total, 2)


def parsear_fichajes(texto):
    try:
        lista = ast.literal_eval(texto)
        return asegurar_orden(lista)
    except:
        return []


def parsear_sap(texto):
    dias = {}
    lineas = texto.splitlines()

    anio = None
    mes = None
    dentro = False

    for linea in lineas:

        mes_match = re.search(r'(\d{6})\s+(\d{2}\.\d{2}\.\d{4})', linea)
        if mes_match:
            anio = int(mes_match.group(2).split(".")[2])
            mes = int(mes_match.group(2).split(".")[1])

        if "Resultados individuales" in linea:
            dentro = True
            continue

        if "Resumen sumas" in linea:
            dentro = False

        if not dentro:
            continue

        dia_match = re.match(r'^(\d{2})\b', linea)

        if dia_match and anio and mes:
            dia = int(dia_match.group(1))
            fecha = datetime(anio, mes, dia).date()

            if fecha not in dias:
                dias[fecha] = {"fichajes": [], "festivo": False}

            if (
                ("Festivo" in linea) or
                ("LIBR" in linea) or
                (
                    not re.search(r'\d{2}:\d{2}', linea)
                    and re.search(r'[A-Za-z]', linea)
                )
            ):
                dias[fecha]["festivo"] = True

            horas = re.findall(r'(\d{2}:\d{2})\s+(\d{2}:\d{2})', linea)
            for entrada, salida in horas:
                dias[fecha]["fichajes"].append((entrada, salida))

    return dias


# ---------------------------------------------------
# ENTRADA DE INFORME SAP
# ---------------------------------------------------

st.subheader("📄 Pegar informe SAP")

texto_sap = st.text_area(
    "Pega aquí el informe exportado de SAP:",
    height=200
)

if st.button("Procesar informe"):
    st.session_state["dias"] = parsear_sap(texto_sap)

if "dias" not in st.session_state:
    st.session_state["dias"] = {}

# ---------------------------------------------------
# SIMULACIÓN DÍA ACTUAL
# ---------------------------------------------------

st.divider()
st.subheader("🧪 Simulación del día actual")

hoy = date.today()

if hoy not in st.session_state["dias"]:
    st.session_state["dias"][hoy] = {"fichajes": [], "festivo": False}

with st.container(border=True):

    st.markdown("### Añadir nuevo fichaje")

    col1, col2 = st.columns(2)

    with col1:
        hora_entrada_txt = st.text_input(
            "🟢 Hora de entrada (HH:MM)",
            value="08:00"
        )

    with col2:
        hora_salida_txt = st.text_input(
            "🔴 Hora de salida (HH:MM)",
            value="17:00"
        )


    if st.button("➕ Añadir fichaje", use_container_width=True):

        try:
            hora_entrada = datetime.strptime(hora_entrada_txt, "%H:%M").time()
            hora_salida = datetime.strptime(hora_salida_txt, "%H:%M").time()
    
            entrada_str = hora_entrada.strftime("%H:%M")
            salida_str = hora_salida.strftime("%H:%M")
    
            st.session_state["dias"][hoy]["fichajes"].append(
                (entrada_str, salida_str)
            )
    
            st.session_state["dias"][hoy]["fichajes"] = asegurar_orden(
                st.session_state["dias"][hoy]["fichajes"]
            )
    
            st.rerun()
    
        except ValueError:
            st.error("Formato inválido. Usa HH:MM en formato 24h (ejemplo: 08:30)")
    

# ---------------------------------------------------
# CONSTRUIR DATAFRAME
# ---------------------------------------------------

if st.session_state["dias"]:

    datos = []

    for dia in sorted(st.session_state["dias"]):

        fichajes = asegurar_orden(st.session_state["dias"][dia]["fichajes"])
        festivo = st.session_state["dias"][dia]["festivo"]

        horas_reales = calcular_horas(fichajes)
        horas_teoricas = 0 if festivo else HORAS_TEORICAS_DIA
        diferencia = horas_reales - horas_teoricas

        datos.append({
            "Fecha": dia,
            "Semana": dia.isocalendar()[1],
            "Mes": dia.strftime("%Y-%m"),
            "Festivo": festivo,
            "Fichajes": str(fichajes),
            "Horas reales": horas_reales,
            "Horas teóricas": horas_teoricas,
            "Diferencia": diferencia
        })

    df = pd.DataFrame(datos).sort_values("Fecha")
    df["Acumulado"] = df["Diferencia"].cumsum()

    # ---------------------------------------------------
    # TABLA DIARIA EDITABLE
    # ---------------------------------------------------

    st.divider()
    st.subheader("📅 Resumen diario")

    df_editado = st.data_editor(
        df,
        use_container_width=True,
        key="editor"
    )

    # Recalcular tras edición

    recalculado = []

    for _, fila in df_editado.iterrows():

        fichajes = parsear_fichajes(fila["Fichajes"])
        festivo = fila["Festivo"]

        horas_reales = calcular_horas(fichajes)
        horas_teoricas = 0 if festivo else HORAS_TEORICAS_DIA
        diferencia = horas_reales - horas_teoricas

        recalculado.append({
            "Fecha": fila["Fecha"],
            "Semana": fila["Semana"],
            "Mes": fila["Mes"],
            "Festivo": festivo,
            "Fichajes": str(fichajes),
            "Horas reales": horas_reales,
            "Horas teóricas": horas_teoricas,
            "Diferencia": diferencia
        })

    df_final = pd.DataFrame(recalculado).sort_values("Fecha")
    df_final["Acumulado"] = df_final["Diferencia"].cumsum()

    # ---------------------------------------------------
    # MÉTRICAS GENERALES
    # ---------------------------------------------------

    st.divider()
    st.subheader("📊 Resumen anual")

    total_reales = df_final["Horas reales"].sum()
    total_teoricas = df_final["Horas teóricas"].sum()
    total_diferencia = df_final["Diferencia"].sum()

    col1, col2, col3 = st.columns(3)

    col1.metric("Horas reales", round(total_reales, 2))
    col2.metric("Horas teóricas", round(total_teoricas, 2))
    col3.metric("Diferencia total", round(total_diferencia, 2))

    # ---------------------------------------------------
    # RESUMEN MENSUAL
    # ---------------------------------------------------

    resumen_mensual = df_final.groupby("Mes")["Diferencia"].sum().reset_index()

    st.subheader("📅 Resumen mensual")
    st.dataframe(resumen_mensual, use_container_width=True)

    # ---------------------------------------------------
    # GRÁFICOS
    # ---------------------------------------------------

    resumen_semanal = df_final.groupby("Semana")["Diferencia"].sum().reset_index()

    st.subheader("📈 Balance semanal")
    fig_semana = px.bar(
        resumen_semanal,
        x="Semana",
        y="Diferencia",
        color="Diferencia",
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig_semana, use_container_width=True)

    st.subheader("📊 Balance mensual")
    fig_mes = px.bar(
        resumen_mensual,
        x="Mes",
        y="Diferencia",
        color="Diferencia",
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig_mes, use_container_width=True)

    st.subheader("📉 Evolución acumulada")
    fig_acum = px.line(
        df_final,
        x="Fecha",
        y="Acumulado",
        markers=True
    )
    st.plotly_chart(fig_acum, use_container_width=True)

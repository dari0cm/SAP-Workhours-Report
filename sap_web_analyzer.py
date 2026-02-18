import ast
import calendar
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

HORAS_TEORICAS_DIA = 8.0


NOMBRES_DIAS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

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
    except Exception:
        return []


def extraer_fecha_ics(valor):
    valor = valor.strip()
    if "T" in valor:
        valor = valor.split("T", maxsplit=1)[0]
    if len(valor) >= 8 and valor[:8].isdigit():
        return datetime.strptime(valor[:8], "%Y%m%d").date()
    return None


def cargar_festivos_ics(base_path="."):
    festivos = defaultdict(set)
    archivos = sorted(Path(base_path).glob("*.ics"))

    for archivo in archivos:
        try:
            contenido = archivo.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        lineas_unidas = []
        for linea in contenido.splitlines():
            if linea.startswith(" ") and lineas_unidas:
                lineas_unidas[-1] += linea[1:]
            else:
                lineas_unidas.append(linea)

        dentro_evento = False
        fecha_evento = None
        nombre_evento = None

        for linea in lineas_unidas:
            if linea.startswith("BEGIN:VEVENT"):
                dentro_evento = True
                fecha_evento = None
                nombre_evento = None
                continue
            if linea.startswith("END:VEVENT"):
                if fecha_evento and nombre_evento:
                    festivos[fecha_evento].add(nombre_evento)
                elif fecha_evento:
                    festivos[fecha_evento].add("Festivo")
                dentro_evento = False
                fecha_evento = None
                nombre_evento = None
                continue

            if dentro_evento and linea.startswith("DTSTART"):
                try:
                    valor = linea.split(":", maxsplit=1)[1]
                except IndexError:
                    continue
                fecha = extraer_fecha_ics(valor)
                if fecha:
                    fecha_evento = fecha

            if dentro_evento and linea.startswith("SUMMARY"):
                try:
                    nombre_evento = linea.split(":", maxsplit=1)[1].strip()
                except IndexError:
                    nombre_evento = "Festivo"

    return dict(festivos), [archivo.name for archivo in archivos]


def construir_calendario_interactivo(year, month, festivos_ics, dias_info):
    cal = calendar.Calendar(firstweekday=0)
    semanas = cal.monthdayscalendar(year, month)

    z_valores = []
    textos = []
    hover_textos = []

    for semana in semanas:
        z_fila = []
        text_fila = []
        hover_fila = []

        for dia in semana:
            if dia == 0:
                z_fila.append(None)
                text_fila.append("")
                hover_fila.append("")
                continue

            fecha = date(year, month, dia)
            es_festivo = fecha in festivos_ics
            es_fin_semana = fecha.weekday() >= 5
            info_dia = dias_info.get(fecha, {})
            horas = info_dia.get("Horas reales", 0)

            if es_festivo:
                estado = 3
                icono = "🎉"
            elif es_fin_semana:
                estado = 1
                icono = "🛌"
            elif horas > 0:
                estado = 2
                icono = "✅"
            else:
                estado = 0
                icono = ""

            festivos_txt = ", ".join(sorted(festivos_ics.get(fecha, []))) or "Sin festivo"
            text_fila.append(f"{dia}<br><span style='font-size:11px'>{icono}</span>")

            hover_fila.append(
                "<br>".join([
                    f"<b>{NOMBRES_DIAS_ES[fecha.weekday()]} {fecha.strftime('%d/%m/%Y')}</b>",
                    f"Horas reales: {horas:.2f}",
                    f"Festivos: {festivos_txt}",
                ])
            )
            z_fila.append(estado)

        z_valores.append(z_fila)
        textos.append(text_fila)
        hover_textos.append(hover_fila)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_valores,
            x=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
            y=[f"Semana {i + 1}" for i in range(len(semanas))],
            text=textos,
            customdata=hover_textos,
            hovertemplate="%{customdata}<extra></extra>",
            colorscale=[
                [0.0, "#F4F6FB"],
                [0.25, "#DFE7FD"],
                [0.5, "#C7F9CC"],
                [0.75, "#FFD6A5"],
                [1.0, "#FFADAD"],
            ],
            showscale=False,
            xgap=6,
            ygap=6,
        )
    )

    fig.update_traces(texttemplate="%{text}")
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        yaxis_autorange="reversed",
    )

    return fig


def parsear_sap(texto):
    dias = {}
    lineas = texto.splitlines()

    anio = None
    mes = None
    dentro = False

    for linea in lineas:

        mes_match = re.search(r"(\d{6})\s+(\d{2}\.\d{2}\.\d{4})", linea)
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

        dia_match = re.match(r"^(\d{2})\b", linea)

        if dia_match and anio and mes:
            dia = int(dia_match.group(1))
            fecha = datetime(anio, mes, dia).date()

            if fecha not in dias:
                dias[fecha] = {"fichajes": [], "festivo": False}

            if (
                ("Festivo" in linea)
                or ("LIBR" in linea)
                or (
                    not re.search(r"\d{2}:\d{2}", linea)
                    and re.search(r"[A-Za-z]", linea)
                )
            ):
                dias[fecha]["festivo"] = True

            horas = re.findall(r"(\d{2}:\d{2})\s+(\d{2}:\d{2})", linea)
            for entrada, salida in horas:
                dias[fecha]["fichajes"].append((entrada, salida))

    return dias


festivos_ics, archivos_ics = cargar_festivos_ics()

if archivos_ics:
    st.caption(
        f"Calendarios .ics detectados ({len(archivos_ics)}): "
        + ", ".join(archivos_ics)
    )
else:
    st.warning("No se han encontrado archivos .ics en el repositorio.")

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

    if st.button("➕ Añadir fichaje", width='stretch'):

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
        festivo_sap = st.session_state["dias"][dia]["festivo"]
        festivo_ics = dia in festivos_ics
        fin_semana = dia.weekday() >= 5
        no_laborable = festivo_sap or festivo_ics or fin_semana

        horas_reales = calcular_horas(fichajes)
        horas_extraordinarias = horas_reales if (festivo_ics or fin_semana) else 0
        horas_normales = round(horas_reales - horas_extraordinarias, 2)
        horas_teoricas = 0 if no_laborable else HORAS_TEORICAS_DIA
        diferencia = round(horas_normales - horas_teoricas, 2)

        datos.append({
            "Fecha": dia,
            "Semana": dia.isocalendar()[1],
            "Mes": dia.strftime("%Y-%m"),
            "Festivo SAP": festivo_sap,
            "Festivo ICS": festivo_ics,
            "Fin de semana": fin_semana,
            "No laborable": no_laborable,
            "Fichajes": str(fichajes),
            "Horas reales": horas_reales,
            "Horas normales": horas_normales,
            "Horas extraordinarias": horas_extraordinarias,
            "Horas teóricas": horas_teoricas,
            "Diferencia": diferencia,
        })

    df = pd.DataFrame(datos).sort_values("Fecha")
    df["Acumulado"] = df["Diferencia"].cumsum()

    st.divider()
    st.subheader("📅 Resumen diario")

    df_editado = st.data_editor(
        df,
        width='stretch',
        key="editor"
    )

    recalculado = []

    for _, fila in df_editado.iterrows():

        fichajes = parsear_fichajes(fila["Fichajes"])

        fecha = fila["Fecha"]
        festivo_sap = bool(fila["Festivo SAP"])
        festivo_ics = fecha in festivos_ics
        fin_semana = fecha.weekday() >= 5
        no_laborable = festivo_sap or festivo_ics or fin_semana

        horas_reales = calcular_horas(fichajes)
        horas_extraordinarias = horas_reales if (festivo_ics or fin_semana) else 0
        horas_normales = round(horas_reales - horas_extraordinarias, 2)
        horas_teoricas = 0 if no_laborable else HORAS_TEORICAS_DIA
        diferencia = round(horas_normales - horas_teoricas, 2)

        recalculado.append({
            "Fecha": fecha,
            "Semana": fila["Semana"],
            "Mes": fila["Mes"],
            "Festivo SAP": festivo_sap,
            "Festivo ICS": festivo_ics,
            "Fin de semana": fin_semana,
            "No laborable": no_laborable,
            "Fichajes": str(fichajes),
            "Horas reales": horas_reales,
            "Horas normales": horas_normales,
            "Horas extraordinarias": horas_extraordinarias,
            "Horas teóricas": horas_teoricas,
            "Diferencia": diferencia,
        })

    df_final = pd.DataFrame(recalculado).sort_values("Fecha")
    df_final["Acumulado"] = df_final["Diferencia"].cumsum()

    st.divider()
    st.subheader("📊 Resumen anual")

    total_reales = df_final["Horas reales"].sum()
    total_normales = df_final["Horas normales"].sum()
    total_extra = df_final["Horas extraordinarias"].sum()
    total_teoricas = df_final["Horas teóricas"].sum()
    total_diferencia = df_final["Diferencia"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("Horas reales", round(total_reales, 2))
    col2.metric("Horas normales", round(total_normales, 2))
    col3.metric("Horas extraordinarias", round(total_extra, 2))
    col4.metric("Horas teóricas", round(total_teoricas, 2))
    col5.metric("Diferencia total", round(total_diferencia, 2))

    resumen_mensual = (
        df_final.groupby("Mes")[["Diferencia", "Horas extraordinarias"]]
        .sum()
        .reset_index()
    )

    st.subheader("📅 Resumen mensual")
    st.dataframe(resumen_mensual, width='stretch')

    resumen_semanal = df_final.groupby("Semana")["Diferencia"].sum().reset_index()

    st.subheader("📈 Balance semanal")
    fig_semana = px.bar(
        resumen_semanal,
        x="Semana",
        y="Diferencia",
        color="Diferencia",
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig_semana, width='stretch')

    st.subheader("📊 Balance mensual")
    fig_mes = px.bar(
        resumen_mensual,
        x="Mes",
        y="Diferencia",
        color="Diferencia",
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig_mes, width='stretch')

    st.subheader("🕒 Horas extraordinarias por mes")
    fig_extra = px.bar(
        resumen_mensual,
        x="Mes",
        y="Horas extraordinarias",
        color="Horas extraordinarias",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_extra, width='stretch')

    st.subheader("📉 Evolución acumulada")
    fig_acum = px.line(
        df_final,
        x="Fecha",
        y="Acumulado",
        markers=True
    )
    st.plotly_chart(fig_acum, width='stretch')

    st.divider()
    st.subheader("🗓️ Visor de calendario")

    meses_disponibles = sorted({(d.year, d.month) for d in df_final["Fecha"]} | {(f.year, f.month) for f in festivos_ics})
    if not meses_disponibles:
        meses_disponibles = [(hoy.year, hoy.month)]

    opciones = {
        f"{year}-{month:02d}": (year, month)
        for year, month in meses_disponibles
    }
    meses_keys = list(opciones.keys())

    if "cal_mes_index" not in st.session_state:
        st.session_state["cal_mes_index"] = len(meses_keys) - 1

    st.session_state["cal_mes_index"] = max(
        0,
        min(st.session_state["cal_mes_index"], len(meses_keys) - 1)
    )

    nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])
    with nav_col1:
        if st.button("⬅️ Mes anterior", width='stretch'):
            st.session_state["cal_mes_index"] = max(0, st.session_state["cal_mes_index"] - 1)
            st.rerun()
    with nav_col2:
        mes_sel_txt = st.selectbox(
            "Mes a visualizar",
            meses_keys,
            index=st.session_state["cal_mes_index"],
            key="cal_mes_selector",
        )
        st.session_state["cal_mes_index"] = meses_keys.index(mes_sel_txt)
    with nav_col3:
        if st.button("Mes siguiente ➡️", width='stretch'):
            st.session_state["cal_mes_index"] = min(len(meses_keys) - 1, st.session_state["cal_mes_index"] + 1)
            st.rerun()

    year_sel, month_sel = opciones[meses_keys[st.session_state["cal_mes_index"]]]

    dias_info = df_final.set_index("Fecha")[["Horas reales"]].to_dict("index")
    calendario_fig = construir_calendario_interactivo(year_sel, month_sel, festivos_ics, dias_info)

    st.caption("Leyenda: 🎉 Festivo .ics · 🛌 Fin de semana · ✅ Día con fichajes · Hover para ver detalles y nombre del festivo")
    st.plotly_chart(calendario_fig, width='stretch')

    festivos_mes = {
        fecha: nombres
        for fecha, nombres in festivos_ics.items()
        if fecha.year == year_sel and fecha.month == month_sel
    }

    if festivos_mes:
        st.markdown("**Festivos del mes (ICS):**")
        festivos_df = pd.DataFrame([
            {
                "Fecha": fecha.strftime("%d/%m/%Y"),
                "Festivo": " · ".join(sorted(nombres)),
            }
            for fecha, nombres in sorted(festivos_mes.items())
        ])
        st.dataframe(festivos_df, width='stretch', hide_index=True)

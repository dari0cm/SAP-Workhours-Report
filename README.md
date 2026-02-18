# SAP Workhours Report

Aplicación en **Streamlit** para analizar un informe de jornadas exportado desde SAP, simular fichajes diarios y visualizar balances de horas normales/extraordinarias con soporte de festivos desde archivos `.ics`.

## Qué hace el proyecto

- Parsea texto pegado de un informe SAP y extrae fichajes por día.
- Calcula:
  - horas reales,
  - horas normales,
  - horas extraordinarias,
  - horas teóricas,
  - diferencia diaria y acumulada.
- Detecta festivos desde archivos `.ics` del repositorio.
- Muestra un visor de calendario interactivo por mes con:
  - navegación mes anterior / siguiente,
  - hover por día,
  - nombre de festivos del `.ics`.
- Incluye gráficos semanales y mensuales con Plotly.

## Estructura mínima

- `sap_web_analyzer.py`: aplicación principal de Streamlit.
- `requirements.txt`: dependencias Python.
- `*.ics`: calendarios/festivos usados por la app.

## Requisitos

- Python 3.10+ recomendado.
- pip.

## Ejecutar en local

1. Clona el repositorio y entra en la carpeta del proyecto:

   ```bash
   git clone <url-del-repo>
   cd SAP-Workhours-Report
   ```

2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   En Windows (PowerShell):

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Lanza la aplicación:

   ```bash
   streamlit run sap_web_analyzer.py
   ```

5. Abre en el navegador la URL que muestra Streamlit (normalmente `http://localhost:8501`).

## Uso rápido

1. Pega el informe SAP en el cuadro de texto.
2. Pulsa **Procesar informe**.
3. (Opcional) Añade fichajes en la sección de simulación del día actual.
4. Revisa:
   - resumen diario editable,
   - métricas anuales,
   - gráficos,
   - visor de calendario interactivo.

## Notas

- Para que se muestren festivos, debe haber al menos un archivo `.ics` en la raíz del proyecto.
- Si no hay `.ics`, la app avisa y sigue funcionando con fines de semana y fichajes.

import yfinance as yf
import google.generativeai as genai
import os
import glob
from datetime import datetime

# ==========================================
# 1. CONECTAR CON GEMINI Y PREPARAR FECHAS
# ==========================================
# Coge la llave de la caja fuerte de GitHub
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Usamos el modelo más potente de Google
model = genai.GenerativeModel('gemini-1.5-pro')

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")

# ==========================================
# 2. DESCARGAR PRECIOS DE YAHOO FINANCE
# ==========================================
activos = {
    "S&P 500": "^GSPC", "Nasdaq 100": "^NDX", "DAX": "^GDAXI",
    "EUR/USD": "EURUSD=X", "DXY": "DX-Y.NYB", "Oro (Futuro)": "GC=F",
    "Petroleo WTI": "CL=F", "Bitcoin": "BTC-USD"
}

datos_texto = "DATOS DE MERCADO ACTUALES:\n"
print("Descargando precios...")
for nombre, ticker in activos.items():
    try:
        data = yf.Ticker(ticker)
        hist = data.history(period="2d")
        c_hoy = hist['Close'].iloc[-1]
        c_ayer = hist['Close'].iloc[-2]
        var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
        datos_texto += f"- {nombre}: {c_hoy:.2f} (Variación 24h: {var_pct:.2f}%)\n"
    except:
        datos_texto += f"- {nombre}: Datos no disponibles\n"

# ==========================================
# 3. HABLAR CON LA IA (EL PROMPT)
# ==========================================
print("Pensando y redactando el informe...")

prompt_sistema = f"""
Eres un analista senior de mercados de Goldman Sachs.
Tu único output será código HTML puro.

{datos_texto}
FECHA: {fecha_legible}

REGLAS ESTRICTAS:
1. Devuelve un bloque HTML de <!DOCTYPE html> a </html>.
2. NO uses bloques de código markdown (```html). Tu respuesta DEBE EMPEZAR con <!DOCTYPE html>.
3. Haz un informe estructurado: Resumen (4 bullets), Tabla de cotizaciones, y Lectura macroeconómica por activo.
4. Usa CSS incrustado (dark mode, fondo #0d1117, letras grises #c9d1d9, detalles azules #58a6ff). 
5. Estilo sobrio, sin consejos de inversión.
"""
# (NOTA: Aquí puedes pegar todo el CSS y las reglas hiper-detalladas de mi primer mensaje).

response = model.generate_content(prompt_sistema)
html_informe = response.text

# Limpiar markdown por si Gemini se equivoca y lo pone
if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]

# ==========================================
# 4. GUARDAR LOS ARCHIVOS
# ==========================================
os.makedirs("historico", exist_ok=True) 

# A) Guardar el informe de hoy (para el botón principal de la web)
with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe.strip())

# B) Guardar una copia en la Hemeroteca
with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe.strip())

# ==========================================
# 5. CREAR LA LANDING PAGE (PORTADA)
# ==========================================
# Leer qué informes antiguos hay
archivos_hist = sorted(glob.glob("historico/*.html"), reverse=True)
lista_enlaces = ""
for ruta in archivos_hist:
    nombre_archivo = os.path.basename(ruta)
    fecha_archivo = nombre_archivo.replace(".html", "")
    lista_enlaces += f'<li><a href="{ruta}">Briefing del {fecha_archivo}</a></li>\n'

# Diseñar la portada de tu web
landing_page = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8"><title>Portal Macro</title>
    <style>
        body {{ background: #0d1117; color: #c9d1d9; font-family: sans-serif; text-align: center; padding: 50px 20px; }}
        .btn {{ background: #1f6feb; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-size: 18px; display:inline-block; margin-bottom: 40px; }}
        .caja {{ background: #161b22; border: 1px solid #30363d; padding: 20px; max-width: 400px; margin: 0 auto; text-align: left; border-radius: 8px; }}
        a {{ color: #58a6ff; text-decoration: none; display: block; padding: 10px 0; border-bottom: 1px solid #30363d;}}
    </style>
</head>
<body>
    <h1>Mesa de Análisis Cuantitativo</h1>
    <a href="latest.html" class="btn">Leer Informe de Hoy ({fecha_legible})</a>
    <div class="caja">
        <h2>Hemeroteca</h2>
        {lista_enlaces}
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing_page.strip())

print("¡Todo listo! Archivos guardados.")

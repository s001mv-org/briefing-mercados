import yfinance as yf
from google import genai
import os
import glob
from datetime import datetime
from curl_cffi import requests

# ==========================================
# 1. CONEXIÓN A GEMINI (NUEVA SDK)
# ==========================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")

# ==========================================
# 2. DESCARGA DE DATOS CON curl_cffi
# ==========================================
activos = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "DAX": "^GDAXI",
    "EUR/USD": "EURUSD=X",
    "DXY": "DX-Y.NYB",
    "Oro (Futuro)": "GC=F",
    "Petroleo WTI": "CL=F",
    "Bitcoin": "BTC-USD"
}

# Sesión que imita un navegador real
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

datos_texto = f"DATOS DE MERCADO ACTUALES AL {fecha_legible}:\n"
print("📡 Descargando precios...")

for nombre, ticker in activos.items():
    try:
        ticker_obj = yf.Ticker(ticker, session=session)
        hist = ticker_obj.history(period="2d")
        
        if len(hist) >= 2:
            c_hoy = hist['Close'].iloc[-1]
            c_ayer = hist['Close'].iloc[-2]
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            simbolo = "🟢" if var_pct >= 0 else "🔴"
            datos_texto += f"- {nombre}: {c_hoy:.2f} ({simbolo} {var_pct:+.2f}%)\n"
            print(f"  ✓ {nombre}: {c_hoy:.2f}")
        else:
            datos_texto += f"- {nombre}: Datos insuficientes\n"
            print(f"  ⚠️ {nombre}: Datos insuficientes")
    except Exception as e:
        datos_texto += f"- {nombre}: No disponible temporalmente\n"
        print(f"  ❌ {nombre}: {str(e)[:60]}")

print("\n🧠 Generando informe con Gemini (modelo 2.5 Flash)...")

# ==========================================
# 3. PROMPT PROFESIONAL
# ==========================================
prompt_completo = f"""
{datos_texto}

Eres un analista senior de mercados financieros estilo Goldman Sachs. Genera un briefing profesional en HTML.

FECHA: {fecha_legible}

ESTRUCTURA OBLIGATORIA:
1. Header con título y fecha
2. Resumen ejecutivo (4-5 bullets)
3. Tabla de cotizaciones (8 activos con precio y variación)
4. Gráfico SVG de barras comparando variaciones 24h
5. Lectura por activo (2-3 frases cada uno)
6. Contexto geopolítico (2 callouts)
7. Calendario macro (tabla)
8. Análisis de riesgos (grid 2x2)
9. Footer con disclaimer

ESTILO CSS (dark mode Bloomberg):
- body: #0d1117, texto #c9d1d9
- bordes #30363d, acentos #58a6ff
- subidas #00d4aa, bajadas #ff4757
- tablas fondo #161b22, cabecera #21262d
- diseño responsive, max-width 1180px

REGLAS:
- Empieza DIRECTAMENTE con <!DOCTYPE html>
- NO recomendaciones de compra/venta
- NO inventes datos
- Tono profesional y probabilístico
- HTML autocontenible (CSS inline)
"""

# 🔥 CORRECCIÓN APLICADA AQUÍ: modelo actualizado a gemini-2.5-flash
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt_completo
)

html_informe = response.text

# Limpieza
if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]
html_informe = html_informe.strip()

print("✅ Informe HTML generado correctamente")

# ==========================================
# 4. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("historico", exist_ok=True)

with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print("  ✓ Guardado: latest.html")

with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"  ✓ Guardado: historico/{fecha_hoy}.html")

# ==========================================
# 5. CREAR LANDING PAGE
# ==========================================
print("📄 Generando landing page...")

archivos_hist = sorted(glob.glob("historico/*.html"), reverse=True)

lista_enlaces = ""
for ruta in archivos_hist[:20]:
    nombre_archivo = os.path.basename(ruta)
    fecha_archivo = nombre_archivo.replace(".html", "")
    fecha_formateada = fecha_archivo.replace("-", "/")
    lista_enlaces += f'<li><a href="{ruta}">📊 Briefing del {fecha_formateada}</a></li>\n'

landing_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Note | Análisis Institucional</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #0d1117;
            color: #c9d1d9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 700px;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 48px;
        }}
        .badge {{
            display: inline-block;
            background: #1f6feb;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
        }}
        h1 {{
            color: #f0f6fc;
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        .sub {{
            color: #8b949e;
            font-size: 16px;
        }}
        .btn-main {{
            display: block;
            background: #1f6feb;
            color: white;
            text-align: center;
            padding: 18px 24px;
            text-decoration: none;
            border-radius: 12px;
            font-weight: 600;
            font-size: 18px;
            transition: all 0.2s ease;
            margin-bottom: 32px;
            border: 1px solid #388bfd;
        }}
        .btn-main:hover {{
            background: #388bfd;
            transform: translateY(-2px);
        }}
        .historico {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 16px;
            overflow: hidden;
        }}
        .historico h2 {{
            background: #21262d;
            padding: 16px 20px;
            font-size: 16px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #f0f6fc;
            margin: 0;
            border-bottom: 1px solid #30363d;
        }}
        .historico ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .historico li {{
            border-bottom: 1px solid #21262d;
        }}
        .historico li:last-child {{
            border-bottom: none;
        }}
        .historico a {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 20px;
            color: #c9d1d9;
            text-decoration: none;
            font-size: 14px;
            transition: background 0.2s;
        }}
        .historico a:hover {{
            background: #1c2128;
            color: #58a6ff;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 24px;
            border-top: 1px solid #21262d;
            color: #6e7681;
            font-size: 12px;
        }}
        .footer a {{
            color: #58a6ff;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="badge">Análisis Institucional</div>
            <h1>Morning Note</h1>
            <p class="sub">Briefing diario de mercados · Macro · Riesgos · Flujos</p>
        </div>

        <a href="latest.html" class="btn-main">
            📈 Leer Informe de Hoy · {fecha_legible}
        </a>

        <div class="historico">
            <h2>📚 Hemeroteca</h2>
            <ul>
                {lista_enlaces if lista_enlaces else '<li style="padding: 20px; text-align: center; color: #6e7681;">No hay informes previos aún</li>'}
            </ul>
        </div>

        <div class="footer">
            <p>🤖 Generado automáticamente con Gemini AI + Yahoo Finance</p>
            <p>Información general · No es asesoramiento financiero</p>
        </div>
    </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing_page)

print("✅ Landing page guardada: index.html")
print("=" * 50)
print("🎉 ¡TODO LISTO! El informe se ha generado correctamente.")
print("=" * 50)

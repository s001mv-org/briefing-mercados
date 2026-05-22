import yfinance as yf
import google.generativeai as genai
import os
import glob
from datetime import datetime
import requests

# ==========================================
# 1. CONEXIÓN A GEMINI
# ==========================================
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash-latest')  # Más rápido y gratuito

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")

# ==========================================
# 2. DESCARGA DE DATOS (con anti-bloqueo)
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

# Simulamos ser un navegador Chrome para evitar bloqueos
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

datos_texto = f"DATOS DE MERCADO ACTUALES AL {fecha_legible}:\n"
print("📡 Descargando precios...")

for nombre, ticker in activos.items():
    try:
        data = yf.Ticker(ticker, session=session)
        hist = data.history(period="2d")
        
        if len(hist) >= 2:
            c_hoy = hist['Close'].iloc[-1]
            c_ayer = hist['Close'].iloc[-2]
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            simbolo = "🟢" if var_pct >= 0 else "🔴"
            datos_texto += f"- {nombre}: {c_hoy:.2f} ({simbolo} {var_pct:+.2f}%)\n"
            print(f"  ✓ {nombre}: {c_hoy:.2f} ({var_pct:+.2f}%)")
        else:
            datos_texto += f"- {nombre}: Datos insuficientes\n"
            print(f"  ⚠️ {nombre}: Datos insuficientes")
    except Exception as e:
        datos_texto += f"- {nombre}: No disponible\n"
        print(f"  ❌ {nombre}: Error - {str(e)[:50]}")

print("\n🧠 Generando informe con Gemini...")

# ==========================================
# 3. PROMPT PROFESIONAL (COMPLETO)
# ==========================================
prompt_completo = f"""
{datos_texto}

Eres un analista senior de mercados financieros estilo Goldman Sachs / JPMorgan. Genera un briefing profesional en HTML.

FECHA: {fecha_legible}

ESTRUCTURA OBLIGATORIA DEL HTML:
1. Header con título "Morning Note Institucional" y fecha
2. Resumen ejecutivo (4-5 bullets con hechos y lecturas)
3. Tabla de cotizaciones con los 8 activos (precio y variación)
4. Gráfico de barras SVG inline mostrando variación 24h
5. Lectura por activo (2-3 frases cada uno)
6. Contexto geopolítico (2 callouts cortos)
7. Calendario macro (tabla con eventos próximos)
8. Análisis de riesgos (grid 2x2: visibles/ocultos/alternativos/señales)
9. Lectura crítica de la narrativa dominante
10. Footer con disclaimer

ESTILO CSS OBLIGATORIO (dark mode Bloomberg):
- Fondo: #0d1117, texto: #c9d1d9
- Bordes: #30363d, acentos: #58a6ff
- Subidas: #00d4aa, bajadas: #ff4757
- Fuente: system-ui, -apple-system, sans-serif
- Tablas con fondo #161b22, cabecera #21262d
- Diseño responsive, max-width 1180px, centrado

REGLAS ESTRICTAS:
- NO uses markdown (```html). Empieza DIRECTAMENTE con <!DOCTYPE html>
- NO des recomendaciones de compra/venta ni niveles operativos
- NO inventes datos. Si no sabes algo, escribe "dato no disponible"
- Usa tono profesional, probabilístico ("es probable que...", "el escenario base sugiere...")
- Separa hechos de inferencias con etiquetas "Hecho:", "Lectura:", "Riesgo:"
- Incluye un gráfico SVG de barras comparando las variaciones 24h de los 8 activos
- El HTML debe ser autocontenible (todo CSS inline en <style>)

Genera SOLO el código HTML, desde <!DOCTYPE html> hasta </html>.
"""

# ==========================================
# 4. LLAMADA A LA IA
# ==========================================
response = model.generate_content(prompt_completo)
html_informe = response.text

# Limpieza de markdown por si acaso
if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]
html_informe = html_informe.strip()

print("✅ Informe HTML generado correctamente")

# ==========================================
# 5. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("historico", exist_ok=True)

# Guardar como latest.html (siempre el más reciente)
with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print("  ✓ Guardado: latest.html")

# Guardar copia en histórico con fecha
with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"  ✓ Guardado: historico/{fecha_hoy}.html")

# ==========================================
# 6. CREAR LANDING PAGE (INDEX.HTML)
# ==========================================
print("📄 Generando landing page...")

# Leer todos los informes del histórico y ordenarlos (nuevo -> viejo)
archivos_hist = sorted(glob.glob("historico/*.html"), reverse=True)

lista_enlaces = ""
for ruta in archivos_hist:
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
        .btn-secondary {{
            display: block;
            background: #161b22;
            color: #c9d1d9;
            text-align: center;
            padding: 12px 20px;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s ease;
            border: 1px solid #30363d;
            margin-bottom: 40px;
        }}
        .btn-secondary:hover {{
            border-color: #58a6ff;
            color: #58a6ff;
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
        @media (max-width: 600px) {{
            h1 {{ font-size: 28px; }}
            .btn-main {{ font-size: 16px; padding: 14px 20px; }}
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
            <p>Información general · No es asesoramiento financiero · <a href="https://github.com">Ver en GitHub</a></p>
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

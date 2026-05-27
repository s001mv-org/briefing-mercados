import yfinance as yf
from google import genai
import os
import glob
from datetime import datetime
from curl_cffi import requests

# ==========================================
# 1. CONEXIÓN A GEMINI
# ==========================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def get_madrid_time():
    now = datetime.now()
    is_summer = (now.month > 3 and now.month < 10) or (now.month == 3 and now.day >= 30) or (now.month == 10 and now.day <= 26)
    offset = 2 if is_summer else 1
    hora = (now.hour + offset) % 24
    tz = "CEST" if is_summer else "CET"
    return f"{hora:02d}:{now.minute:02d} {tz}"

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")
hora_madrid = get_madrid_time()

# ==========================================
# 2. DESCARGAR PRECIOS
# ==========================================
activos = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "DAX": "^GDAXI",
    "EUR/USD": "EURUSD=X",
    "DXY": "DX-Y.NYB",
    "Oro (futuro)": "GC=F",
    "Petróleo WTI": "CL=F",
    "Bitcoin": "BTC-USD"
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

precios = {}
variaciones = {}

print("📡 Descargando precios en tiempo real...")
for nombre, ticker in activos.items():
    try:
        ticker_obj = yf.Ticker(ticker, session=session)
        hist = ticker_obj.history(period="2d")
        if len(hist) >= 2:
            c_hoy = hist['Close'].iloc[-1]
            c_ayer = hist['Close'].iloc[-2]
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            precios[nombre] = c_hoy
            variaciones[nombre] = var_pct
            print(f"  ✓ {nombre}: {c_hoy:.2f} ({var_pct:+.2f}%)")
        else:
            precios[nombre] = 0
            variaciones[nombre] = 0
    except Exception as e:
        precios[nombre] = 0
        variaciones[nombre] = 0
        print(f"  ❌ {nombre}: Error")

datos_mercado = "DATOS DE MERCADO ACTUALES:\n"
for nombre in activos.keys():
    if precios[nombre] != 0:
        signo = "+" if variaciones[nombre] >= 0 else ""
        datos_mercado += f"- {nombre}: {precios[nombre]:.2f} (Var 24h: {signo}{variaciones[nombre]:.2f}%)\n"
    else:
        datos_mercado += f"- {nombre}: dato no disponible\n"

# ==========================================
# 3. PROMPT COMPLETO (versión simplificada pero completa)
# ==========================================
prompt_completo = f"""
{datos_mercado}

FECHA ACTUAL: {fecha_legible} a las {hora_madrid}

Eres un analista senior de mercados financieros. Genera un briefing profesional en HTML estilo morning note.

ESTRUCTURA OBLIGATORIA DEL HTML:
1. Header con título, fecha, hora CET y banner de perfil
2. Resumen ejecutivo (4-5 bullets con "Hecho:", "Lectura:", "Riesgo:")
3. Snapshot: KPI grid + tabla de 8 activos
4. Gráfico SVG de barras 24h (verde/rojo)
5. Lectura por activo (2-3 frases cada uno)
6. Contexto geopolítico (callouts)
7. Calendario macro (tabla con badges)
8. Análisis de riesgos (grid 2x2)
9. Lectura crítica narrativa dominante
10. Checklist + footer

ESTILO VISUAL: dark mode Bloomberg (fondo #0d1117, texto #c9d1d9, acentos #58a6ff, subidas #00d4aa, bajadas #ff4757)

BANNER DE PERFIL:
<div class="banner-perfil"><strong>Perfil estándar usado.</strong> 8 activos: S&P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin.</div>

DISCLAIMER EN FOOTER:
<footer><p><strong>Aviso.</strong> Este briefing es información general de mercado, no asesoramiento financiero.</p></footer>

REGLAS:
- NO inventes precios. Usa los datos reales que te he proporcionado.
- NO des recomendaciones de compra/venta.
- Empieza DIRECTAMENTE con <!DOCTYPE html>
- HTML autocontenible (CSS inline)
"""

print("\n🧠 Generando briefing con Gemini...")

# 🔥 CORRECCIÓN AQUÍ - Modelos que SÍ funcionan en mayo 2026
try:
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt_completo
    )
    print("✅ Usando modelo: gemini-2.0-flash")
except Exception as e:
    print(f"⚠️ Error con gemini-2.0-flash: {e}")
    print("🔄 Intentando con gemini-1.5-pro...")
    try:
        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=prompt_completo
        )
        print("✅ Usando modelo: gemini-1.5-pro")
    except Exception as e2:
        print(f"⚠️ Error con gemini-1.5-pro: {e2}")
        print("🔄 Último intento con gemini-2.0-flash-lite...")
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt_completo
        )
        print("✅ Usando modelo: gemini-2.0-flash-lite")

html_informe = response.text

# Limpieza de markdown
if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]
html_informe = html_informe.strip()

print("✅ Briefing HTML generado correctamente")

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
# 5. LANDING PAGE
# ==========================================
archivos_hist = sorted(glob.glob("historico/*.html"), reverse=True)
lista_enlaces = ""
for ruta in archivos_hist[:30]:
    nombre = os.path.basename(ruta).replace(".html", "").replace("-", "/")
    lista_enlaces += f'<li><a href="{ruta}">📊 Briefing del {nombre}</a></li>\n'

landing = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Morning Note</title>
<style>
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;text-align:center;padding:50px 20px;}}
.btn{{background:#1f6feb;color:#fff;padding:16px 32px;text-decoration:none;border-radius:8px;display:inline-block;margin-bottom:40px;font-weight:600;}}
.btn:hover{{background:#388bfd;}}
.caja{{background:#161b22;border:1px solid #30363d;border-radius:12px;max-width:500px;margin:0 auto;padding:20px;text-align:left;}}
.caja h2{{color:#f0f6fc;margin-top:0;padding-bottom:10px;border-bottom:1px solid #30363d;}}
ul{{list-style:none;padding:0;}}
li a{{display:block;padding:12px 0;color:#58a6ff;text-decoration:none;border-bottom:1px solid #21262d;}}
li:last-child a{{border-bottom:none;}}
li a:hover{{color:#79c0ff;}}
</style>
</head>
<body>
<h1>Morning Note Institucional</h1>
<a href="latest.html" class="btn">📈 Leer briefing de hoy ({fecha_legible})</a>
<div class="caja"><h2>📚 Hemeroteca</h2><ul>{lista_enlaces}</ul></div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing)

print("✅ Landing page guardada: index.html")
print("=" * 50)
print("🎉 ¡BRIEFING COMPLETO GENERADO CON ÉXITO!")
print("=" * 50)

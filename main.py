import yfinance as yf
from google import genai
import os
import glob
from datetime import datetime
import time
from curl_cffi import requests

# ==========================================
# 1. CONEXIÓN A GEMINI
# ==========================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Obtener hora exacta en Madrid (CET/CEST)
def get_madrid_time():
    # Por simplicidad usamos UTC+1 o UTC+2 según fecha
    # En producción usar pytz, pero para GitHub Actions esto basta
    now = datetime.now()
    # Domingo 30 marzo a domingo 26 octubre -> CEST (UTC+2)
    is_summer = (now.month > 3 and now.month < 10) or (now.month == 3 and now.day >= 30) or (now.month == 10 and now.day <= 26)
    offset = 2 if is_summer else 1
    hora = (now.hour + offset) % 24
    tz = "CEST" if is_summer else "CET"
    return f"{hora:02d}:{now.minute:02d} {tz}"

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
fecha_legible = datetime.now().strftime("%d/%m/%Y")
hora_madrid = get_madrid_time()

# ==========================================
# 2. DESCARGAR PRECIOS REALES
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

# Construir string de datos para la IA
datos_mercado = "DATOS DE MERCADO ACTUALES:\n"
for nombre in activos.keys():
    if precios[nombre] != 0:
        signo = "+" if variaciones[nombre] >= 0 else ""
        datos_mercado += f"- {nombre}: {precios[nombre]:.2f} (Var 24h: {signo}{variaciones[nombre]:.2f}%)\n"
    else:
        datos_mercado += f"- {nombre}: dato no disponible\n"

# ==========================================
# 3. PROMPT COMPLETO (literal del original)
# ==========================================
prompt_completo = f"""
{datos_mercado}

FECHA ACTUAL: {fecha_legible} a las {hora_madrid}

Eres un analista senior de mercados financieros del estilo de las morning notes de Goldman Sachs / JPMorgan: conciso, denso, profesional. Tu único output será un bloque de HTML autocontenible (de <!DOCTYPE html> a </html>) que el usuario verá renderizado. Nada de chat. Nada de explicaciones previas. Nada de preguntas. El HTML ES el entregable.

================================================================
VARIABLES DE PERFIL
================================================================
ACTIVOS (8 estándar): S&P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin
PROFUNDIDAD: estándar consultora
HORIZONTE OPERATIVO: swing/multitemporal
ZONA HORARIA: Europa/Madrid
MONEDA BASE: EUR
IDIOMA: Español

================================================================
RIGOR PROFESIONAL OBLIGATORIO
================================================================
1. Separa hechos de inferencias. Usa "Hecho:", "Lectura:", "Riesgo:".
2. Verifica tesis dominantes contra el dato real.
3. Nada de "máximos históricos" absolutos. Usa "zona de máximos cíclicos".
4. Mentalidad probabilística: "es probable que...", "el escenario base sugiere..."
5. Tono profesional, sobrio, sin sensacionalismo.
6. Incluye análisis crítico de la narrativa dominante.
7. SIN niveles operativos, SIN recomendaciones de compra/venta.
8. Cita fuentes en cada dato.

================================================================
ESTRUCTURA OBLIGATORIA DEL HTML
================================================================
El HTML debe contener, en este orden:

1. HEADER con título "Morning Note Institucional", fecha del día, hora de generación (CET/CEST) y banner de perfil.
2. RESUMEN EJECUTIVO (4-5 bullets, una frase cada uno).
3. SNAPSHOT: KPI grid (4 tarjetas) + tabla compacta de los 8 activos.
4. GRÁFICO SVG de barras comparando variación 24h de los 8 activos. Verde si positiva, rojo si negativa. Eje horizontal en y=130 (cero). Escala vertical: 1% = 35 píxeles. Viewbox 800x260.
5. LECTURA POR ACTIVO (subapartados con h3, 2-3 frases por activo).
6. CONTEXTO GEOPOLÍTICO (2-3 callouts cortos).
7. CALENDARIO MACRO (tabla con badges de relevancia alta/media/baja).
8. ANÁLISIS DE RIESGOS (grid 2x2: visibles / no descontados / escenarios alternativos / señales a vigilar).
9. LECTURA CRÍTICA de la narrativa dominante (callout danger + 2 párrafos).
10. CHECKLIST de verificación.
11. FOOTER con disclaimer.

================================================================
ESTILO VISUAL OBLIGATORIO (dark Bloomberg-like)
================================================================
Usa EXACTAMENTE este CSS. NO añadas librerías externas, NO CDN, NO fuentes web.

* {{ box-sizing: border-box; }}
body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif; font-size: 16px; line-height: 1.6; margin: 0; padding: 0; }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 64px; }}
header {{ border-bottom: 2px solid #30363d; padding-bottom: 18px; margin-bottom: 28px; }}
.tag {{ display: inline-block; background: #1f6feb; color: #fff; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; }}
h1 {{ color: #f0f6fc; font-size: 30px; margin: 12px 0 4px; font-weight: 700; }}
h2 {{ color: #f0f6fc; font-size: 22px; margin: 40px 0 12px; padding-bottom: 8px; border-bottom: 1px solid #30363d; }}
h3 {{ color: #58a6ff; font-size: 17px; margin: 18px 0 8px; }}
p, li {{ font-size: 15.5px; }}
.meta {{ color: #8b949e; font-size: 13px; margin-top: 6px; }}
.section {{ margin-bottom: 22px; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 14px 0 10px; }}
.kpi {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 12px 14px; }}
.kpi .name {{ font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
.kpi .price {{ font-size: 20px; font-weight: 700; color: #f0f6fc; font-family: "SF Mono", Menlo, monospace; }}
.kpi .delta {{ font-size: 13px; margin-top: 4px; font-family: "SF Mono", Menlo, monospace; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0 18px; font-size: 14px; background: #161b22; border: 1px solid #30363d; border-radius: 4px; overflow: hidden; }}
th, td {{ padding: 9px 12px; text-align: left; border-bottom: 1px solid #21262d; }}
th {{ background: #21262d; color: #f0f6fc; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; font-family: "SF Mono", Menlo, monospace; }}
td.asset {{ font-weight: 600; color: #f0f6fc; }}
.up {{ color: #00d4aa; }}
.down {{ color: #ff4757; }}
.flat {{ color: #8b949e; }}
.b-high {{ background: #ff4757; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.b-med {{ background: #f0883e; color: #fff; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.b-low {{ background: #30363d; color: #c9d1d9; padding: 2px 8px; border-radius: 3px; font-size: 11px; }}
.badge-bull {{ background: #00d4aa20; color: #00d4aa; border: 1px solid #00d4aa55; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.badge-bear {{ background: #ff475720; color: #ff4757; border: 1px solid #ff475755; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.badge-range {{ background: #8b949e20; color: #c9d1d9; border: 1px solid #8b949e55; padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }}
.callout {{ background: #161b22; border-left: 4px solid #1f6feb; padding: 12px 16px; margin: 16px 0; border-radius: 0 4px 4px 0; font-size: 15px; }}
.callout.warn {{ border-left-color: #f0883e; }}
.callout.danger {{ border-left-color: #ff4757; }}
.callout strong {{ color: #f0f6fc; }}
.banner-perfil {{ background: #1f6feb15; border: 1px solid #1f6feb55; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #c9d1d9; margin-bottom: 18px; }}
ul.check {{ list-style: none; padding-left: 0; margin: 8px 0; }}
ul.check li {{ padding: 5px 0; border-bottom: 1px dashed #21262d; font-size: 14px; }}
.risk-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 12px 0; }}
.risk-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 14px 16px; }}
.risk-card h4 {{ margin: 0 0 8px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; color: #8b949e; font-weight: 600; }}
.risk-card.visible h4 {{ color: #f0883e; }}
.risk-card.hidden h4 {{ color: #ff4757; }}
.risk-card.scenario h4 {{ color: #58a6ff; }}
.risk-card.signal h4 {{ color: #00d4aa; }}
.risk-card p {{ margin: 0 0 6px; font-size: 14px; line-height: 1.55; }}
footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #30363d; color: #8b949e; font-size: 12px; }}
footer p {{ font-size: 12px; margin: 6px 0; }}
@media (max-width: 720px) {{ .risk-grid {{ grid-template-columns: 1fr; }} h1 {{ font-size: 24px; }} h2 {{ font-size: 19px; }} }}

================================================================
BANNER DE PERFIL OBLIGATORIO
================================================================
<div class="banner-perfil">
  <strong>Perfil estándar usado.</strong> 8 activos: S&amp;P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin. Profundidad: estándar consultora. Horizonte: swing/multitemporal. Zona horaria: Europa/Madrid. Para personalizar, edita las variables del prompt antes de ejecutarlo.
</div>

================================================================
DISCLAIMER OBLIGATORIO EN FOOTER
================================================================
<footer>
  <p><strong>Aviso.</strong> Este briefing es información general de mercado, no asesoramiento financiero ni recomendación de inversión personalizada. No tiene en cuenta tu situación, objetivos ni tolerancia al riesgo. Las decisiones de inversión son tuyas y conllevan riesgo de pérdida. Para asesoramiento adaptado a tu perfil, acude a una entidad autorizada en tu país (CNMV en España, o equivalente).</p>
  <p>Generado por IA con búsqueda web. Fuentes citadas en cada sección. Educación, no asesoramiento. Análisis probabilístico, no determinista.</p>
</footer>

================================================================
GRÁFICO SVG OBLIGATORIO
================================================================
Incluye un gráfico de barras SVG inline en la sección 4. Escala: 1% = 35px, eje Y en 130. Verde (#00d4aa) si positiva, rojo (#ff4757) si negativa.

================================================================
LO QUE NUNCA DEBES HACER
================================================================
- No pedir información al usuario.
- No inventar precios. Usa "dato no disponible" si falta.
- No dar niveles operativos ni recomendaciones.
- No tono sensacionalista.
- No romper el CSS dado.

================================================================
EMPIEZA AHORA
================================================================
Genera el HTML completo con los precios que te he proporcionado al inicio. Usa esos datos reales. No inventes nada. Sigue la estructura al pie de la letra.
"""

print("\n🧠 Generando briefing con Gemini (100% fiel al prompt original)...")

# Llamada a Gemini
response = client.models.generate_content(
    model="gemini-2.0-flash-exp",
    contents=prompt_completo
)

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
# 5. LANDING PAGE (simplificada pero funcional)
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

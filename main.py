import yfinance as yf
import os
import glob
from datetime import datetime
from curl_cffi import requests
from openai import OpenAI
from google import genai

# ==========================================
# CONFIGURACIÓN - ELIGE TU MOTOR
# ==========================================
# Opciones: "deepseek", "gemini", "auto"
MOTOR_IA = "gemini"  # Cambia a "gemini" si quieres volver

# API Keys (desde GitHub Secrets)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ==========================================
# 1. FUNCIONES COMUNES
# ==========================================
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
        print(f"  ❌ {nombre}: {str(e)[:50]}")

datos_mercado = "DATOS DE MERCADO ACTUALES:\n"
for nombre in activos.keys():
    if precios[nombre] != 0:
        signo = "+" if variaciones[nombre] >= 0 else ""
        datos_mercado += f"- {nombre}: {precios[nombre]:.2f} (Var 24h: {signo}{variaciones[nombre]:.2f}%)\n"
    else:
        datos_mercado += f"- {nombre}: dato no disponible\n"

# ==========================================
# 3. PROMPT COMPLETO
# ==========================================
prompt_completo = f"""
{datos_mercado}

FECHA: {fecha_legible} | HORA: {hora_madrid}

Eres un analista senior de mercados financieros del estilo Goldman Sachs/JPMorgan. Genera un briefing profesional en HTML.

ESTRUCTURA OBLIGATORIA (11 secciones):
1. Header con título, fecha, hora CET y banner de perfil
2. Resumen ejecutivo (4-5 bullets con "Hecho:", "Lectura:", "Riesgo:")
3. Snapshot: KPI grid (4 tarjetas) + tabla de 8 activos
4. Gráfico SVG de barras 24h (verde/rojo, escala: 1% = 35px, eje Y=130)
5. Lectura por activo (subapartados h3, 2-3 frases por activo con etiquetas)
6. Contexto geopolítico (2-3 callouts)
7. Calendario macro (tabla con badges alta/media/baja)
8. Análisis de riesgos (grid 2x2: visibles/no descontados/escenarios alternativos/señales)
9. Lectura crítica de la narrativa dominante (callout danger + 2 párrafos)
10. Checklist de verificación
11. Footer con disclaimer

ESTILO VISUAL OBLIGATORIO (dark Bloomberg-like):
- Fondo: #0d1117, texto: #c9d1d9
- Bordes: #30363d, acentos: #58a6ff
- Subidas: #00d4aa, bajadas: #ff4757
- Tablas fondo #161b22, cabecera #21262d

BANNER DE PERFIL (obligatorio, justo debajo del header):
<div class="banner-perfil">
  <strong>Perfil estándar usado.</strong> 8 activos: S&amp;P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin.
</div>

DISCLAIMER EN FOOTER (literal):
<footer>
  <p><strong>Aviso.</strong> Este briefing es información general de mercado, no asesoramiento financiero ni recomendación de inversión personalizada.</p>
  <p>Generado por IA con búsqueda web. Educación, no asesoramiento. Análisis probabilístico, no determinista.</p>
</footer>

REGLAS ESTRICTAS:
- NO inventes precios. Usa los datos reales que te he proporcionado.
- NO des recomendaciones de compra/venta ni niveles operativos.
- Tono profesional, probabilístico, sin sensacionalismo.
- Empieza DIRECTAMENTE con <!DOCTYPE html>
- HTML autocontenible (CSS inline en <style>)
"""

# ==========================================
# 4. FUNCIONES DE GENERACIÓN POR MOTOR
# ==========================================
def generar_con_deepseek():
    """Genera briefing usando DeepSeek API"""
    print("🚀 Generando con DeepSeek...")
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1"
    )
    
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt_completo}],
        temperature=0.2,
        max_tokens=8192
    )
    
    return response.choices[0].message.content

def generar_con_gemini():
    """Genera briefing usando Gemini API"""
    print("🚀 Generando con Gemini...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Probar varios modelos
    modelos = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-2.0-flash-lite"]
    for modelo in modelos:
        try:
            print(f"  Intentando con {modelo}...")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt_completo
            )
            return response.text
        except Exception as e:
            print(f"  ❌ {modelo}: {str(e)[:50]}")
            continue
    raise Exception("Todos los modelos de Gemini fallaron")

# ==========================================
# 5. GENERAR BRIEFING SEGÚN MOTOR ELEGIDO
# ==========================================
print(f"\n🧠 Motor seleccionado: {MOTOR_IA.upper()}")

html_informe = None

if MOTOR_IA == "deepseek":
    try:
        html_informe = generar_con_deepseek()
        print(f"✅ Generado con DeepSeek, longitud: {len(html_informe)} caracteres")
    except Exception as e:
        print(f"❌ Error con DeepSeek: {e}")
        if GEMINI_API_KEY:
            print("🔄 Fallback a Gemini...")
            try:
                html_informe = generar_con_gemini()
                print(f"✅ Generado con Gemini (fallback)")
            except Exception as e2:
                print(f"❌ También falló Gemini: {e2}")

elif MOTOR_IA == "gemini":
    try:
        html_informe = generar_con_gemini()
        print(f"✅ Generado con Gemini, longitud: {len(html_informe)} caracteres")
    except Exception as e:
        print(f"❌ Error con Gemini: {e}")
        if DEEPSEEK_API_KEY:
            print("🔄 Fallback a DeepSeek...")
            try:
                html_informe = generar_con_deepseek()
                print(f"✅ Generado con DeepSeek (fallback)")
            except Exception as e2:
                print(f"❌ También falló DeepSeek: {e2}")

else:  # auto
    print("🔄 Modo automático: probando DeepSeek primero...")
    if DEEPSEEK_API_KEY:
        try:
            html_informe = generar_con_deepseek()
            print(f"✅ Generado con DeepSeek")
        except:
            pass
    if not html_informe and GEMINI_API_KEY:
        try:
            html_informe = generar_con_gemini()
            print(f"✅ Generado con Gemini")
        except:
            pass

# ==========================================
# 6. EMERGENCIA (si todo falla)
# ==========================================
if not html_informe or len(html_informe.strip()) < 100:
    print("⚠️ Generando HTML de emergencia con los precios descargados...")
    
    tabla_precios = ""
    for nombre in activos.keys():
        if precios[nombre] != 0:
            signo = "+" if variaciones[nombre] >= 0 else ""
            color_cls = "up" if variaciones[nombre] >= 0 else "down"
            tabla_precios += f"""
            <tr>
                <td class="asset">{nombre}</td>
                <td class="num">{precios[nombre]:.2f}</td>
                <td class="num {color_cls}">{signo}{variaciones[nombre]:.2f}%</td>
            </tr>"""
    
    html_informe = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Briefing de Mercados - {fecha_legible}</title>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, sans-serif; margin: 0; padding: 40px; }}
        .wrap {{ max-width: 1180px; margin: 0 auto; }}
        h1, h2 {{ color: #f0f6fc; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; background: #161b22; border: 1px solid #30363d; border-radius: 4px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ background: #21262d; color: #f0f6fc; }}
        .asset {{ font-weight: 600; color: #f0f6fc; }}
        .num {{ text-align: right; font-family: monospace; }}
        .up {{ color: #00d4aa; }}
        .down {{ color: #ff4757; }}
        .banner-perfil {{ background: #1f6feb15; border: 1px solid #1f6feb55; padding: 10px 14px; border-radius: 4px; margin-bottom: 20px; }}
        footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #30363d; color: #8b949e; font-size: 12px; }}
    </style>
</head>
<body>
<div class="wrap">
    <h1>📊 Morning Note Institucional</h1>
    <div class="banner-perfil">
        <strong>Perfil estándar usado.</strong> 8 activos: S&amp;P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin.
    </div>
    <p><strong>Fecha:</strong> {fecha_legible} | <strong>Hora:</strong> {hora_madrid}</p>
    
    <h2>📈 Cotizaciones</h2>
    <table>
        <thead><tr><th>Activo</th><th>Precio</th><th>Variación 24h</th></tr></thead>
        <tbody>{tabla_precios}</tbody>
    </table>
    
    <footer>
        <p><strong>Aviso.</strong> Información general de mercado, no asesoramiento financiero.</p>
        <p>Generado automáticamente.</p>
    </footer>
</div>
</body>
</html>"""

# Limpiar markdown
if html_informe.startswith("```html"):
    html_informe = html_informe[7:-3]
elif html_informe.startswith("```"):
    html_informe = html_informe[3:-3]
html_informe = html_informe.strip()

print(f"✅ Briefing final, longitud: {len(html_informe)} caracteres")

# ==========================================
# 7. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("historico", exist_ok=True)

with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print("  ✓ Guardado: latest.html")

with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"  ✓ Guardado: historico/{fecha_hoy}.html")

# ==========================================
# 8. LANDING PAGE
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

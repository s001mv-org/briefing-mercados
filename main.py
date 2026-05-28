import yfinance as yf
import os
import re
import glob
from datetime import datetime
from curl_cffi import requests
from openai import OpenAI

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    print("❌ ERROR: No se encontró DEEPSEEK_API_KEY")
    exit(1)

def get_madrid_time():
    now = datetime.utcnow()
    is_summer = (now.month > 3 and now.month < 10) or \
                (now.month == 3 and now.day >= 28) or \
                (now.month == 10 and now.day <= 25)
    offset = 2 if is_summer else 1
    hora = (now.hour + offset) % 24
    tz = "CEST" if is_summer else "CET"
    return f"{hora:02d}:{now.minute:02d} {tz}"

fecha_hoy     = datetime.utcnow().strftime("%Y-%m-%d")
fecha_legible = datetime.utcnow().strftime("%d/%m/%Y")
hora_madrid   = get_madrid_time()

# ==========================================
# 2. DESCARGAR PRECIOS (Yahoo Finance)
# ==========================================
activos = {
    "S&P 500":      "^GSPC",
    "Nasdaq 100":   "^NDX",
    "DAX":          "^GDAXI",
    "EUR/USD":      "EURUSD=X",
    "DXY":          "DX-Y.NYB",
    "Oro (futuro)": "GC=F",
    "Petróleo WTI": "CL=F",
    "Bitcoin":      "BTC-USD",
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
})

precios     = {}
variaciones = {}

print("📡 Descargando precios...")
for nombre, ticker in activos.items():
    try:
        t    = yf.Ticker(ticker, session=session)
        hist = t.history(period="5d")       # 5d cubre festivos
        hist = hist[hist["Close"].notna()]   # filtra NaN
        if len(hist) >= 2:
            c_hoy   = float(hist["Close"].iloc[-1])
            c_ayer  = float(hist["Close"].iloc[-2])
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            precios[nombre]     = c_hoy
            variaciones[nombre] = var_pct
            signo = "+" if var_pct >= 0 else ""
            print(f"  ✓ {nombre}: {c_hoy:.2f} ({signo}{var_pct:.2f}%)")
        else:
            raise ValueError("Historial insuficiente")
    except Exception as e:
        precios[nombre]     = 0
        variaciones[nombre] = 0
        print(f"  ❌ {nombre}: {e}")

datos_mercado = "DATOS DE MERCADO ACTUALES (Yahoo Finance):\n"
for nombre in activos:
    if precios[nombre] != 0:
        signo = "+" if variaciones[nombre] >= 0 else ""
        datos_mercado += (
            f"- {nombre}: {precios[nombre]:.2f} "
            f"(Var 24h: {signo}{variaciones[nombre]:.2f}%)\n"
        )

# ==========================================
# 3. PROMPT
# ==========================================
prompt = f"""{datos_mercado}
FECHA: {fecha_legible}  |  HORA: {hora_madrid}

---

Eres un analista senior de mercados financieros estilo morning notes Goldman Sachs / JPMorgan.
Tu ÚNICO output es un archivo HTML autocontenible, desde <!DOCTYPE html> hasta </html>.
Sin texto previo. Sin explicaciones. Sin markdown. Solo el HTML.

ACTIVOS: S&P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro (futuro), Petróleo WTI, Bitcoin
IDIOMA: Español | ZONA HORARIA: Europa/Madrid | HORIZONTE: swing/multitemporal

=== REGLAS DE RIGOR ===
1. Usa los datos de mercado exactos proporcionados arriba. No los alteres ni inventes otros.
2. Separa hechos de inferencias: etiqueta con "Hecho:", "Lectura:", "Riesgo:".
3. Nunca afirmes "máximos históricos" sin referenciar el periodo exacto.
4. Lenguaje probabilístico: "es probable que...", "el escenario base sugiere...".
5. Sin niveles operativos (R1/S1/stops/objetivos). Sin "compra" ni "vende".
6. Incluye sección de lectura crítica que cuestione la narrativa dominante del día.

=== ESTRUCTURA (11 secciones en orden) ===
1. Header: título, fecha {fecha_legible}, hora {hora_madrid}, banner perfil estándar
2. Resumen ejecutivo: 4-5 bullets con Hecho/Lectura/Riesgo
3. Snapshot: KPI grid (8 cards) + tabla de los 8 activos con precio y variación
4. Gráfico SVG barras 24h: verde=#00d4aa positivo, rojo=#ff4757 negativo, escala 1%=35px, eje cero en y=130, viewBox="0 0 820 260", fondo #161b22
5. Lectura por activo: h3 por activo, 2-3 frases máximo
6. Contexto geopolítico: 2-3 callouts con temas relevantes del día
7. Calendario macro: tabla con eventos próximos 7-10 días, badges alta/media/baja
8. Análisis de riesgos: grid 2x2 (visibles / no descontados / escenarios alternativos / señales a vigilar)
9. Lectura crítica: callout danger + 2 párrafos cortos
10. Checklist de verificación de rigor
11. Footer con disclaimer legal

=== CSS OBLIGATORIO (cópialo literalmente dentro de <style>) ===
*{{box-sizing:border-box;}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.6;margin:0;padding:0;}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 22px 64px;}}
header{{border-bottom:2px solid #30363d;padding-bottom:18px;margin-bottom:28px;}}
.tag{{display:inline-block;background:#1f6feb;color:#fff;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}}
h1{{color:#f0f6fc;font-size:30px;margin:12px 0 4px;font-weight:700;}}
h2{{color:#f0f6fc;font-size:22px;margin:40px 0 12px;padding-bottom:8px;border-bottom:1px solid #30363d;}}
h3{{color:#58a6ff;font-size:17px;margin:18px 0 8px;}}
p,li{{font-size:15.5px;}}
.meta{{color:#8b949e;font-size:13px;margin-top:6px;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0 10px;}}
.kpi{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px 14px;}}
.kpi .name{{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;}}
.kpi .price{{font-size:20px;font-weight:700;color:#f0f6fc;font-family:"SF Mono",Menlo,monospace;}}
.kpi .delta{{font-size:13px;margin-top:4px;font-family:"SF Mono",Menlo,monospace;}}
table{{width:100%;border-collapse:collapse;margin:10px 0 18px;font-size:14px;background:#161b22;border:1px solid #30363d;border-radius:4px;overflow:hidden;}}
th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid #21262d;}}
th{{background:#21262d;color:#f0f6fc;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em;}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:"SF Mono",Menlo,monospace;}}
td.asset{{font-weight:600;color:#f0f6fc;}}
.up{{color:#00d4aa;}}.down{{color:#ff4757;}}.flat{{color:#8b949e;}}
.b-high{{background:#ff4757;color:#fff;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;}}
.b-med{{background:#f0883e;color:#fff;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;}}
.b-low{{background:#30363d;color:#c9d1d9;padding:2px 8px;border-radius:3px;font-size:11px;}}
.badge-bull{{background:#00d4aa20;color:#00d4aa;border:1px solid #00d4aa55;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;}}
.badge-bear{{background:#ff475720;color:#ff4757;border:1px solid #ff475755;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;}}
.badge-range{{background:#8b949e20;color:#c9d1d9;border:1px solid #8b949e55;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;}}
.callout{{background:#161b22;border-left:4px solid #1f6feb;padding:12px 16px;margin:16px 0;border-radius:0 4px 4px 0;font-size:15px;}}
.callout.warn{{border-left-color:#f0883e;}}.callout.danger{{border-left-color:#ff4757;}}
.callout strong{{color:#f0f6fc;}}
.banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;color:#c9d1d9;margin-bottom:18px;}}
ul.check{{list-style:none;padding-left:0;margin:8px 0;}}
ul.check li{{padding:5px 0;border-bottom:1px dashed #21262d;font-size:14px;}}
.risk-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;}}
.risk-card{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 16px;}}
.risk-card h4{{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#8b949e;font-weight:600;}}
.risk-card.visible h4{{color:#f0883e;}}.risk-card.hidden h4{{color:#ff4757;}}
.risk-card.scenario h4{{color:#58a6ff;}}.risk-card.signal h4{{color:#00d4aa;}}
.risk-card p{{margin:0 0 6px;font-size:14px;line-height:1.55;}}
footer{{margin-top:40px;padding-top:16px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
footer p{{font-size:12px;margin:6px 0;}}
@media(max-width:720px){{.risk-grid{{grid-template-columns:1fr;}}h1{{font-size:24px;}}h2{{font-size:19px;}}}}

=== FOOTER OBLIGATORIO ===
<footer>
  <p><strong>Aviso.</strong> Este briefing es información general de mercado, no asesoramiento financiero ni recomendación de inversión personalizada. Las decisiones de inversión son tuyas y conllevan riesgo de pérdida. Para asesoramiento personalizado acude a una entidad autorizada (CNMV en España o equivalente).</p>
  <p>Generado automáticamente con IA. Datos: Yahoo Finance. Análisis probabilístico, no determinista.</p>
</footer>

Genera el HTML COMPLETO ahora. Empieza directamente con <!DOCTYPE html> sin ningún texto previo."""

print(f"\n📝 Prompt: {len(prompt):,} caracteres")
print("🧠 Generando briefing con DeepSeek (deepseek-reasoner)...")

# ==========================================
# 4. LLAMADA A DEEPSEEK
#    FIX 1: timeout=300 (el reasoner tarda 3-5 min con prompts largos)
#    FIX 2: se elimina el bloque <think>...</think> antes de procesar
#    FIX 3: se lee reasoning_content si content viene vacío
# ==========================================
html_informe = None

try:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        timeout=300.0,          # FIX 1: era 120s, ahora 300s
    )

    response = client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=32768,
    )

    raw = response.choices[0].message.content or ""

    # FIX 3: si content viene vacío, algunos builds del SDK meten
    # el HTML en reasoning_content por error de parsing
    if not raw.strip():
        rc = getattr(response.choices[0].message, "reasoning_content", "") or ""
        if rc.strip():
            print("⚠️  content vacío, usando reasoning_content como fallback")
            raw = rc

    print(f"✅ Respuesta recibida: {len(raw):,} caracteres")

    # FIX 2: elimina el bloque de razonamiento <think>...</think>
    # El reasoner antepone su cadena de pensamiento antes del HTML
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    print(f"   Tras eliminar <think>: {len(raw):,} caracteres")

    # Limpia posibles bloques markdown
    if "```html" in raw:
        raw = raw.split("```html", 1)[1]
        raw = raw.rsplit("```", 1)[0]
    elif raw.strip().startswith("```"):
        raw = raw.strip()[3:]
        if raw.endswith("```"):
            raw = raw[:-3]

    raw = raw.strip()

    # Busca el DOCTYPE aunque haya texto sobrante antes
    if not raw.lower().startswith("<!doctype"):
        idx = raw.lower().find("<!doctype")
        if idx != -1:
            print(f"⚠️  Texto basura antes del HTML ({idx} chars), recortando...")
            raw = raw[idx:]
        else:
            print("❌ No se encontró <!DOCTYPE> en la respuesta")
            raw = None

    html_informe = raw

except Exception as e:
    print(f"❌ Error con DeepSeek API: {e}")
    html_informe = None

# ==========================================
# 5. FALLBACK DE EMERGENCIA
# ==========================================
if not html_informe or len(html_informe) < 1000:
    print("⚠️  Usando HTML de emergencia (tabla básica)...")

    filas = ""
    for nombre in activos:
        if precios[nombre] != 0:
            signo = "+" if variaciones[nombre] >= 0 else ""
            cls   = "up" if variaciones[nombre] >= 0 else "down"
            filas += (
                f"<tr><td class='asset'>{nombre}</td>"
                f"<td class='num'>{precios[nombre]:.2f}</td>"
                f"<td class='num {cls}'>{signo}{variaciones[nombre]:.2f}%</td></tr>"
            )

    html_informe = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Morning Note — {fecha_legible}</title>
<style>
*{{box-sizing:border-box;}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;margin:0;padding:40px;}}
.wrap{{max-width:1180px;margin:0 auto;}}
header{{border-bottom:2px solid #30363d;padding-bottom:18px;margin-bottom:28px;}}
h1{{color:#f0f6fc;font-size:28px;margin:12px 0 4px;}}
.meta{{color:#8b949e;font-size:13px;}}
.banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:4px;overflow:hidden;}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #21262d;}}
th{{background:#21262d;color:#f0f6fc;font-size:12px;text-transform:uppercase;}}
td.asset{{font-weight:600;color:#f0f6fc;}}
td.num{{text-align:right;font-family:monospace;}}
.up{{color:#00d4aa;}}.down{{color:#ff4757;}}
footer{{margin-top:40px;padding-top:16px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>📊 Morning Note Institucional</h1>
  <div class="meta">{fecha_legible} — {hora_madrid} — Modo emergencia (IA no disponible)</div>
</header>
<div class="banner-perfil"><strong>Perfil estándar.</strong> 8 activos: S&amp;P 500, Nasdaq 100, DAX, EUR/USD, DXY, Oro, Petróleo WTI, Bitcoin.</div>
<h2>Cotizaciones</h2>
<table>
  <thead><tr><th>Activo</th><th>Precio</th><th>Variación 24h</th></tr></thead>
  <tbody>{filas}</tbody>
</table>
<footer>
  <p><strong>Aviso.</strong> Información general de mercado. No asesoramiento financiero.</p>
  <p>Datos: Yahoo Finance. {fecha_legible} {hora_madrid}</p>
</footer>
</div>
</body>
</html>"""

# ==========================================
# 6. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("historico", exist_ok=True)

with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"\n✅ latest.html guardado ({len(html_informe):,} caracteres)")

with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"✅ historico/{fecha_hoy}.html guardado")

# ==========================================
# 7. LANDING PAGE (index.html)
# ==========================================
archivos = sorted(glob.glob("historico/*.html"), reverse=True)[:30]
enlaces  = "".join([
    f'<li><a href="{a}">📊 '
    f'{a.replace("historico/","").replace(".html","")}'
    f'</a></li>'
    for a in archivos
])

landing = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Morning Note Institucional</title>
<style>
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;text-align:center;padding:50px 20px;}}
h1{{color:#f0f6fc;font-size:28px;margin-bottom:8px;}}
.sub{{color:#8b949e;font-size:14px;margin-bottom:32px;}}
.btn{{background:#1f6feb;color:#fff;padding:16px 32px;text-decoration:none;border-radius:8px;display:inline-block;margin-bottom:40px;font-weight:600;font-size:16px;}}
.btn:hover{{background:#388bfd;}}
.caja{{background:#161b22;border:1px solid #30363d;border-radius:12px;max-width:520px;margin:0 auto;padding:24px;text-align:left;}}
.caja h2{{color:#f0f6fc;margin:0 0 16px;padding-bottom:10px;border-bottom:1px solid #30363d;font-size:17px;}}
ul{{list-style:none;padding:0;margin:0;}}
li a{{display:block;padding:10px 0;color:#58a6ff;text-decoration:none;border-bottom:1px solid #21262d;font-size:14px;}}
li a:hover{{color:#79c0ff;}}
</style>
</head>
<body>
<h1>📊 Morning Note Institucional</h1>
<p class="sub">Briefing diario de mercados — actualización automática L-V</p>
<a href="latest.html" class="btn">📈 Leer briefing de hoy ({fecha_legible})</a>
<div class="caja">
  <h2>📚 Hemeroteca (últimos 30 días)</h2>
  <ul>{enlaces}</ul>
</div>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing)
print("✅ index.html guardado")
print("\n🎉 PROCESO COMPLETADO")

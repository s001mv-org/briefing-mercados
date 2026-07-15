import yfinance as yf
import os
import re
import glob
from datetime import datetime
from curl_cffi import requests
from google import genai

# ==========================================
# 1. CONFIGURACIÓN - GEMINI
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️  WARNING: No se encontró GEMINI_API_KEY. Generando briefing en modo offline.")
    MODO_IA = False
else:
    MODO_IA = True
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Error al inicializar el cliente de Gemini: {e}")
        MODO_IA = False

def get_madrid_time():
    """Calcula la hora actual en Madrid (CET o CEST según fecha)"""
    now = datetime.utcnow()
    is_summer = (now.month > 3 and now.month < 10) or \
                (now.month == 3 and now.day >= 28) or \
                (now.month == 10 and now.day <= 25)
    offset = 2 if is_summer else 1
    hora = (now.hour + offset) % 24
    tz = "CEST" if is_summer else "CET"
    return f"{hora:02d}:{now.minute:02d} {tz}"

fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")
fecha_legible = datetime.utcnow().strftime("%d/%m/%Y")
hora_madrid = get_madrid_time()

# ==========================================
# 2. DESCARGAR PRECIOS (Yahoo Finance)
# ==========================================
activos = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "DAX": "^GDAXI",
    "EUR/USD": "EURUSD=X",
    "DXY": "DX-Y.NYB",
    "Oro (futuro)": "GC=F",
    "Petróleo WTI": "CL=F",
    "Bitcoin": "BTC-USD",
}

# Sesión con User-Agent personalizado para evitar bloqueos
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
})

precios = {}
variaciones = {}

print("📡 Descargando precios...")
for nombre, ticker in activos.items():
    try:
        t = yf.Ticker(ticker, session=session)
        hist = t.history(period="5d")
        hist = hist[hist["Close"].notna()]
        if len(hist) >= 2:
            c_hoy = float(hist["Close"].iloc[-1])
            c_ayer = float(hist["Close"].iloc[-2])
            var_pct = ((c_hoy - c_ayer) / c_ayer) * 100
            precios[nombre] = c_hoy
            variaciones[nombre] = var_pct
            signo = "+" if var_pct >= 0 else ""
            print(f"  ✓ {nombre}: {c_hoy:.2f} ({signo}{var_pct:.2f}%)")
        else:
            precios[nombre] = 0
            variaciones[nombre] = 0
    except Exception as e:
        precios[nombre] = 0
        variaciones[nombre] = 0
        print(f"  ❌ {nombre}: {e}")

datos_mercado = "DATOS DE MERCADO ACTUALES (Yahoo Finance):\n"
for nombre in activos:
    if precios[nombre] != 0:
        signo = "+" if variaciones[nombre] >= 0 else ""
        datos_mercado += f"- {nombre}: {precios[nombre]:.2f} (Var 24h: {signo}{variaciones[nombre]:.2f}%)\n"

# ==========================================
# 3. PROMPT COMPLETO (52k caracteres)
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
print("🧠 Generando briefing con Gemini...")

# ==========================================
# 4. LLAMADA A GEMINI (con reintentos)
# ==========================================
html_informe = None

if MODO_IA:
    modelos_gemini = [
        "gemini-2.0-flash",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-pro",
    ]

    for modelo in modelos_gemini:
        try:
            print(f"  Intentando con {modelo}...")
            model = client.models.generate_content(
                model=modelo,
                contents=prompt
            )
            raw = model.text
            
            if raw and len(raw) > 100:
                print(f"  ✅ Éxito con {modelo} ({len(raw):,} caracteres)")
                
                if "```html" in raw:
                    raw = raw.split("```html", 1)[1]
                    raw = raw.rsplit("```", 1)[0]
                elif raw.strip().startswith("```"):
                    raw = raw.strip()[3:]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                
                raw = raw.strip()
                
                if not raw.lower().startswith("<!doctype"):
                    idx = raw.lower().find("<!doctype")
                    if idx != -1:
                        print(f"  ⚠️ Recortando texto basura ({idx} caracteres)")
                        raw = raw[idx:]
                
                html_informe = raw
                break
            else:
                print(f"  ❌ {modelo}: respuesta demasiado corta")
                
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"  ❌ {modelo}: CUOTA EXCEDIDA")
            elif "404" in error_msg:
                print(f"  ❌ {modelo}: modelo no encontrado")
            else:
                print(f"  ❌ {modelo}: {error_msg[:100]}")
            continue

# ==========================================
# 5. FALLBACK DE EMERGENCIA
# ==========================================
if not html_informe or len(html_informe) < 500:
    print("⚠️ Usando HTML de emergencia (tabla básica)...")

    filas = ""
    for nombre in activos:
        if precios[nombre] != 0:
            signo = "+" if variaciones[nombre] >= 0 else ""
            cls = "up" if variaciones[nombre] >= 0 else "down"
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
  <div class="meta">{fecha_legible} — {hora_madrid} — Modo emergencia</div>
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
# 6. GUARDAR ARCHIVOS (Morning Note)
# ==========================================
os.makedirs("historico", exist_ok=True)

with open("latest.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"\n✅ latest.html guardado ({len(html_informe):,} caracteres)")

with open(f"historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_informe)
print(f"✅ historico/{fecha_hoy}.html guardado")

# ==========================================
# 7. LANDING PAGE (index.html) - TREE MENÚ
# ==========================================
def generar_tree_html():
    """Genera el HTML del árbol con los enlaces actuales y contadores"""
    
    # Contar archivos históricos
    mn_files = sorted(glob.glob("historico/*.html"), reverse=True)
    db_files = sorted(glob.glob("dashboard-historico/*.html"), reverse=True)
    mn_count = len(mn_files)
    db_count = len(db_files)
    
    # Obtener fecha de hoy para el badge
    hoy = datetime.utcnow().strftime("%d/%m/%Y")
    
    # Generar listas de históricos (top 5 para mostrar en tooltip)
    mn_list = "".join([
        f'<li><a href="{f}">📊 {f.replace("historico/","").replace(".html","")}</a></li>'
        for f in mn_files[:5]
    ])
    db_list = "".join([
        f'<li><a href="{f}">🎯 {f.replace("dashboard-historico/","").replace(".html","")}</a></li>'
        for f in db_files[:5]
    ])
    
    return f'''
    <ul class="tree" id="treeMenu">
      
      <!-- ===== NODO 1: MORNING NOTES ===== -->
      <li class="node">
        <div class="label" onclick="toggleNode(this)">
          <span class="icon">📈</span>
          Morning Notes
          <span class="badge-count">{mn_count}</span>
          <span class="arrow">▶</span>
        </div>
        <ul class="children open">
          <li class="leaf">
            <div class="label">
              <a href="latest.html" class="link">
                📄 Lectura de Hoy
                <span class="today-badge">{hoy}</span>
              </a>
            </div>
          </li>
          <li class="leaf">
            <div class="label">
              <a href="historico/" class="link">
                📚 Hemeroteca
                <span class="badge-small">{mn_count} archivos</span>
              </a>
            </div>
          </li>
          {f'<li class="leaf"><div class="label" style="padding:4px 14px 4px 44px;font-size:12px;color:#8b949e;cursor:default;">📋 Últimos: {mn_list}</div></li>' if mn_count > 0 else ''}
        </ul>
      </li>

      <!-- ===== NODO 2: OPORTUNIDADES ===== -->
      <li class="node">
        <div class="label" onclick="toggleNode(this)">
          <span class="icon">🎯</span>
          Oportunidades
          <span class="badge-count">{db_count}</span>
          <span class="arrow">▶</span>
        </div>
        <ul class="children open">
          <li class="leaf">
            <div class="label">
              <a href="dashboard-latest.html" class="link">
                📊 Dashboard de Hoy
                <span class="today-badge">{hoy}</span>
              </a>
            </div>
          </li>
          <li class="leaf">
            <div class="label">
              <a href="dashboard-historico/" class="link">
                📚 Histórico
                <span class="badge-small">{db_count} archivos</span>
              </a>
            </div>
          </li>
          {f'<li class="leaf"><div class="label" style="padding:4px 14px 4px 44px;font-size:12px;color:#8b949e;cursor:default;">📋 Últimos: {db_list}</div></li>' if db_count > 0 else ''}
        </ul>
      </li>

      <!-- ===== NODO 3: FUTURO MÓDULO 1 ===== -->
      <li class="node">
        <div class="label" onclick="toggleNode(this)" style="color:#8b949e;">
          <span class="icon">🔮</span>
          Futuro Módulo 1
          <span class="arrow">▶</span>
        </div>
        <ul class="children">
          <li class="leaf">
            <div class="label" style="color:#8b949e;cursor:default;">
              <span class="link" style="color:#8b949e;cursor:default;">🚧 En desarrollo</span>
            </div>
          </li>
        </ul>
      </li>

      <!-- ===== NODO 4: FUTURO MÓDULO 2 ===== -->
      <li class="node">
        <div class="label" onclick="toggleNode(this)" style="color:#8b949e;">
          <span class="icon">⚙️</span>
          Futuro Módulo 2
          <span class="arrow">▶</span>
        </div>
        <ul class="children">
          <li class="leaf">
            <div class="label" style="color:#8b949e;cursor:default;">
              <span class="link" style="color:#8b949e;cursor:default;">📋 En planificación</span>
            </div>
          </li>
        </ul>
      </li>

    </ul>
    '''

# Generar el HTML completo de la landing page
landing = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
<title>Finance Dashboard</title>
<style>
/* ========================================
   RESET Y BASE
   ======================================== */
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.6;padding:20px 16px;min-height:100vh;}}
.wrap{{max-width:1200px;margin:0 auto;}}

/* ========================================
   HEADER
   ======================================== */
header{{border-bottom:2px solid #30363d;padding-bottom:16px;margin-bottom:24px;}}
.logo{{font-size:24px;font-weight:700;color:#f0f6fc;display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
.logo .badge{{background:#1f6feb;font-size:10px;padding:2px 12px;border-radius:12px;font-weight:600;color:#fff;letter-spacing:0.3px;}}
.subtitle{{color:#8b949e;font-size:13px;margin-top:4px;}}

/* ========================================
   TREE MENÚ
   ======================================== */
.tree{{list-style:none;padding:0;margin:0 0 30px;}}
.tree li{{list-style:none;padding:0;}}
.tree .node{{margin:0;}}
.tree .node > .label{{display:flex;align-items:center;gap:8px;padding:12px 16px;cursor:pointer;border-radius:8px;transition:background 0.2s;color:#c9d1d9;font-size:15px;font-weight:500;user-select:none;-webkit-tap-highlight-color:transparent;}}
.tree .node > .label:hover{{background:#21262d;}}
.tree .node > .label:active{{background:#30363d;}}
.tree .node > .label .icon{{font-size:18px;width:28px;text-align:center;flex-shrink:0;}}
.tree .node > .label .arrow{{font-size:11px;color:#8b949e;transition:transform 0.3s ease;margin-left:auto;flex-shrink:0;}}
.tree .node > .label .arrow.open{{transform:rotate(90deg);}}
.tree .node > .label .badge-count{{background:#21262d;color:#8b949e;font-size:11px;padding:1px 10px;border-radius:12px;font-weight:400;margin-left:auto;}}
.tree .node > .children{{list-style:none;padding:0;margin:0 0 0 16px;overflow:hidden;max-height:0;opacity:0;transition:max-height 0.35s ease, opacity 0.3s ease, padding 0.3s ease;}}
.tree .node > .children.open{{max-height:2000px;opacity:1;padding:4px 0;}}

/* ========================================
   NODOS HOJA
   ======================================== */
.tree .leaf .label{{padding:10px 16px 10px 44px;font-weight:400;font-size:14px;cursor:pointer;border-radius:6px;transition:background 0.15s;color:#8b949e;min-height:44px;display:flex;align-items:center;}}
.tree .leaf .label:hover{{background:#1c2333;color:#f0f6fc;}}
.tree .leaf .label:active{{background:#21262d;}}
.tree .leaf .label .link{{color:#58a6ff;text-decoration:none;display:flex;align-items:center;gap:8px;flex-wrap:wrap;width:100%;}}
.tree .leaf .label .link:hover{{color:#79c0ff;}}
.tree .leaf .label .today-badge{{background:#1f6feb20;color:#58a6ff;font-size:10px;padding:2px 10px;border-radius:12px;border:1px solid #1f6feb55;margin-left:auto;white-space:nowrap;}}
.tree .leaf .label .badge-small{{background:#21262d;padding:1px 10px;border-radius:12px;font-size:10px;color:#8b949e;margin-left:auto;white-space:nowrap;}}

/* ========================================
   FOOTER
   ======================================== */
footer{{margin-top:40px;padding-top:16px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;text-align:center;}}
footer p{{margin:4px 0;}}
footer .version{{color:#30363d;font-size:10px;}}

/* ========================================
   RESPONSIVE - MÓVIL
   ======================================== */
@media(max-width:640px){{
  body{{padding:12px 10px;}}
  .logo{{font-size:20px;}}
  .subtitle{{font-size:12px;}}
  .tree .node > .label{{padding:14px 12px;font-size:14px;min-height:52px;}}
  .tree .node > .children{{margin-left:8px;}}
  .tree .leaf .label{{padding:12px 12px 12px 36px;font-size:13px;min-height:48px;}}
  .tree .node > .label .icon{{font-size:16px;width:24px;}}
  .tree .leaf .label .today-badge{{font-size:9px;padding:1px 8px;}}
  .tree .leaf .label .badge-small{{font-size:9px;padding:1px 8px;}}
}}

@media(max-width:480px){{
  body{{padding:8px 6px;}}
  .tree .node > .label{{font-size:13px;padding:14px 10px;min-height:48px;}}
  .tree .leaf .label{{padding:12px 10px 12px 30px;font-size:12px;min-height:44px;}}
  .tree .node > .children{{margin-left:4px;}}
  .tree .node > .label .icon{{font-size:14px;width:20px;}}
}}

/* ========================================
   SCROLLBAR PERSONALIZADA (opcional)
   ======================================== */
::-webkit-scrollbar{{width:6px;height:6px;}}
::-webkit-scrollbar-track{{background:#0d1117;}}
::-webkit-scrollbar-thumb{{background:#30363d;border-radius:4px;}}
::-webkit-scrollbar-thumb:hover{{background:#484f58;}}
</style>
</head>
<body>
<div class="wrap">

<!-- ===== HEADER ===== -->
<header>
  <div class="logo">
    📊 Finance Dashboard
    <span class="badge">v2.0</span>
  </div>
  <div class="subtitle">Actualización automática diaria (L-V) · Datos en tiempo real</div>
</header>

<!-- ===== TREE MENÚ (generado dinámicamente) ===== -->
{generar_tree_html()}

<!-- ===== FOOTER ===== -->
<footer>
  <p>Datos: Yahoo Finance · Análisis con IA · No asesoramiento financiero</p>
  <p class="version">v2.0 · Generado automáticamente · {datetime.utcnow().strftime("%d/%m/%Y %H:%M")} UTC</p>
</footer>

</div>

<!-- ========================================
   JAVASCRIPT
   ======================================== -->
<script>
// ========================================
// 1. FUNCIÓN TOGGLE PARA NODOS DEL ÁRBOL
// ========================================
function toggleNode(labelElement) {{
    const node = labelElement.closest('.node');
    if (!node) return;
    
    const children = node.querySelector('.children');
    if (!children) return;
    
    children.classList.toggle('open');
    
    const arrow = labelElement.querySelector('.arrow');
    if (arrow) {{
        arrow.classList.toggle('open');
    }}
}}

// ========================================
// 2. SOPORTE PARA TECLADO (accesibilidad)
// ========================================
document.querySelectorAll('.node > .label').forEach(label => {{
    label.setAttribute('role', 'button');
    label.setAttribute('tabindex', '0');
    label.setAttribute('aria-expanded', label.closest('.node').querySelector('.children').classList.contains('open') ? 'true' : 'false');
    
    label.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' || e.key === ' ') {{
            e.preventDefault();
            toggleNode(this);
            const isOpen = this.closest('.node').querySelector('.children').classList.contains('open');
            this.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }}
    }});
    
    label.addEventListener('click', function() {{
        setTimeout(() => {{
            const isOpen = this.closest('.node').querySelector('.children').classList.contains('open');
            this.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        }}, 50);
    }});
}});

// ========================================
// 3. LOG PARA DEPURACIÓN
// ========================================
console.log('🌳 Tree Menu cargado correctamente');
console.log('📊 Morning Notes:', document.querySelectorAll('.node:first-child .leaf').length, 'elementos');
console.log('🎯 Oportunidades:', document.querySelectorAll('.node:nth-child(2) .leaf').length, 'elementos');
</script>
</body>
</html>"""

# Guardar la landing page
with open("index.html", "w", encoding="utf-8") as f:
    f.write(landing)
print("✅ index.html guardado (con Tree Menú)")

print("\n🎉 PROCESO COMPLETADO")

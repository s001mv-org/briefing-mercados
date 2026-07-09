import yfinance as yf
import os
import re
import glob
import json
import math
from datetime import datetime
from curl_cffi import requests
import google.generativeai as genai

# ==========================================
# 1. CONFIGURACIÓN - GEMINI
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ ERROR: No se encontró GEMINI_API_KEY")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def get_madrid_time():
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
# 2. UNIVERSO DE ACCIONES
# ==========================================
acciones = {
    "NVDA": "Nvidia",
    "META": "Meta Platforms", 
    "MSFT": "Microsoft",
    "AVGO": "Broadcom",
    "AMD": "Advanced Micro Devices",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    "AMZN": "Amazon",
    "AAPL": "Apple",
    "GOOGL": "Alphabet (Google)",
    "V": "Visa",
    "COST": "Costco",
    "JPM": "JPMorgan Chase",
    "LLY": "Eli Lilly",
    "TSLA": "Tesla",
    "NFLX": "Netflix",
    "KO": "Coca-Cola",
    "PG": "Procter & Gamble",
}

sector_colores = {
    "Technology": "#58a6ff",
    "Communication Services": "#f0883e",
    "Consumer Cyclical": "#00d4aa",
    "Financial Services": "#ff4757",
    "Healthcare": "#d2a8ff",
    "Consumer Defensive": "#ffd93d",
    "Energy": "#ff6b6b",
    "Industrials": "#4ecdc4",
    "Real Estate": "#a8e6cf",
    "Utilities": "#95e1d3",
    "N/A": "#8b949e",
}

# ==========================================
# 3. DESCARGAR DATOS
# ==========================================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
})

def get_stock_data(ticker):
    try:
        t = yf.Ticker(ticker, session=session)
        hist = t.history(period="2y")
        info = t.info
        
        if len(hist) < 2:
            return None
            
        precio_actual = float(hist["Close"].iloc[-1])
        max_52s = float(hist["High"].max())
        caida_max = ((max_52s - precio_actual) / max_52s) * 100 if max_52s > 0 else 0
        
        if len(hist) >= 252:
            precio_anio = float(hist["Close"].iloc[-252])
            retorno_anual = ((precio_actual - precio_anio) / precio_anio) * 100
        else:
            retorno_anual = 0
        
        if len(hist) >= 1260:
            precio_5y = float(hist["Close"].iloc[-1260])
            crecimiento_5y = ((precio_actual - precio_5y) / precio_5y) * 100
        else:
            crecimiento_5y = 0
        
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        market_cap = info.get("marketCap", 0)
        
        forward_pe = info.get("forwardPE", 0)
        trailing_pe = info.get("trailingPE", 0)
        peg = info.get("pegRatio", 0)
        ev_ebitda = info.get("enterpriseToEbitda", 0)
        fcf_yield = info.get("freeCashflowYield", 0) * 100 if info.get("freeCashflowYield") else 0
        
        revenue_growth = info.get("revenueGrowth", 0) * 100
        earnings_growth = info.get("earningsGrowth", 0) * 100
        gross_margins = info.get("grossMargins", 0) * 100
        operating_margins = info.get("operatingMargins", 0) * 100
        net_margins = info.get("profitMargins", 0) * 100
        
        roe = info.get("returnOnEquity", 0) * 100
        roic = info.get("returnOnAssets", 0) * 100
        debt_to_equity = info.get("debtToEquity", 0)
        current_ratio = info.get("currentRatio", 0)
        quick_ratio = info.get("quickRatio", 0)
        
        recommendation = info.get("recommendationKey", "N/A")
        target_mean = info.get("targetMeanPrice", 0)
        target_high = info.get("targetHighPrice", 0)
        target_low = info.get("targetLowPrice", 0)
        number_of_analysts = info.get("numberOfAnalystOpinions", 0)
        
        dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
        volume = info.get("volume", 0)
        avg_volume = info.get("averageVolume", 0)
        
        return {
            "ticker": ticker,
            "nombre": acciones.get(ticker, ticker),
            "precio": round(precio_actual, 2),
            "max_52s": round(max_52s, 2),
            "caida_max": round(caida_max, 2),
            "retorno_anual": round(retorno_anual, 2),
            "crecimiento_5y": round(crecimiento_5y, 2),
            "sector": sector,
            "industria": industry,
            "market_cap": market_cap,
            "market_cap_b": round(market_cap / 1e9, 2) if market_cap else 0,
            "forward_pe": round(forward_pe, 2) if forward_pe else 0,
            "trailing_pe": round(trailing_pe, 2) if trailing_pe else 0,
            "peg": round(peg, 2) if peg else 0,
            "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda else 0,
            "fcf_yield": round(fcf_yield, 2),
            "revenue_growth": round(revenue_growth, 2),
            "earnings_growth": round(earnings_growth, 2),
            "gross_margins": round(gross_margins, 2),
            "operating_margins": round(operating_margins, 2),
            "net_margins": round(net_margins, 2),
            "roe": round(roe, 2),
            "roic": round(roic, 2),
            "debt_to_equity": round(debt_to_equity, 2),
            "current_ratio": round(current_ratio, 2),
            "quick_ratio": round(quick_ratio, 2),
            "recommendation": recommendation,
            "target_mean": round(target_mean, 2) if target_mean else 0,
            "target_high": round(target_high, 2) if target_high else 0,
            "target_low": round(target_low, 2) if target_low else 0,
            "number_analysts": number_of_analysts,
            "dividend_yield": round(dividend_yield, 2),
            "volume": volume,
            "avg_volume": avg_volume,
        }
    except Exception as e:
        print(f"  ❌ {ticker}: {str(e)[:80]}")
        return None

print("📡 Descargando datos de acciones...")
datos_acciones = []
for ticker in acciones:
    print(f"  Procesando {ticker}...")
    data = get_stock_data(ticker)
    if data:
        datos_acciones.append(data)
        print(f"    ✓ {ticker}: ${data['precio']:.2f} | Caída: {data['caida_max']:.1f}% | ROE: {data['roe']:.1f}%")

print(f"\n✅ {len(datos_acciones)} acciones descargadas correctamente")

# ==========================================
# 4. CALCULAR SCORES
# ==========================================
def calcular_scores(data):
    scores = {}
    
    # VALUE (0-25)
    value = 0
    if data['forward_pe'] > 0:
        if data['forward_pe'] < 10:
            value += 8
        elif data['forward_pe'] < 15:
            value += 6
        elif data['forward_pe'] < 20:
            value += 4
        elif data['forward_pe'] < 25:
            value += 2
    if data['peg'] > 0:
        if data['peg'] < 0.5:
            value += 7
        elif data['peg'] < 1:
            value += 5
        elif data['peg'] < 1.5:
            value += 3
        elif data['peg'] < 2:
            value += 1
    if data['ev_ebitda'] > 0:
        if data['ev_ebitda'] < 8:
            value += 5
        elif data['ev_ebitda'] < 12:
            value += 4
        elif data['ev_ebitda'] < 15:
            value += 3
        elif data['ev_ebitda'] < 20:
            value += 1
    if data['fcf_yield'] > 0:
        if data['fcf_yield'] > 10:
            value += 5
        elif data['fcf_yield'] > 5:
            value += 4
        elif data['fcf_yield'] > 3:
            value += 2
        elif data['fcf_yield'] > 1:
            value += 1
    scores['value'] = min(value, 25)
    
    # GROWTH (0-25)
    growth = 0
    if data['revenue_growth'] > 0:
        if data['revenue_growth'] > 50:
            growth += 9
        elif data['revenue_growth'] > 30:
            growth += 7
        elif data['revenue_growth'] > 20:
            growth += 5
        elif data['revenue_growth'] > 10:
            growth += 3
        elif data['revenue_growth'] > 5:
            growth += 1
    if data['earnings_growth'] > 0:
        if data['earnings_growth'] > 50:
            growth += 8
        elif data['earnings_growth'] > 30:
            growth += 6
        elif data['earnings_growth'] > 20:
            growth += 4
        elif data['earnings_growth'] > 10:
            growth += 2
        elif data['earnings_growth'] > 5:
            growth += 1
    if data['gross_margins'] > 40:
        growth += 3
    if data['operating_margins'] > 20:
        growth += 3
    if data['net_margins'] > 15:
        growth += 2
    scores['growth'] = min(growth, 25)
    
    # QUALITY (0-25)
    quality = 0
    if data['roe'] > 0:
        if data['roe'] > 50:
            quality += 7
        elif data['roe'] > 30:
            quality += 5
        elif data['roe'] > 20:
            quality += 4
        elif data['roe'] > 15:
            quality += 2
        elif data['roe'] > 10:
            quality += 1
    if data['roic'] > 0:
        if data['roic'] > 30:
            quality += 6
        elif data['roic'] > 20:
            quality += 5
        elif data['roic'] > 15:
            quality += 3
        elif data['roic'] > 10:
            quality += 1
    if data['debt_to_equity'] > 0:
        if data['debt_to_equity'] < 0.3:
            quality += 6
        elif data['debt_to_equity'] < 0.6:
            quality += 5
        elif data['debt_to_equity'] < 1:
            quality += 4
        elif data['debt_to_equity'] < 1.5:
            quality += 2
        elif data['debt_to_equity'] < 2:
            quality += 1
    else:
        quality += 3
    if data['net_margins'] > 20:
        quality += 6
    elif data['net_margins'] > 15:
        quality += 4
    elif data['net_margins'] > 10:
        quality += 2
    elif data['net_margins'] > 5:
        quality += 1
    scores['quality'] = min(quality, 25)
    
    # MOMENTUM (0-25)
    momentum = 0
    if data['caida_max'] > 0:
        if data['caida_max'] > 30:
            momentum += 10
        elif data['caida_max'] > 20:
            momentum += 8
        elif data['caida_max'] > 15:
            momentum += 6
        elif data['caida_max'] > 10:
            momentum += 4
        elif data['caida_max'] > 5:
            momentum += 2
    if data['retorno_anual'] < 0:
        if data['roe'] > 20 and data['revenue_growth'] > 15:
            momentum += 8
        elif data['roe'] > 15 and data['revenue_growth'] > 10:
            momentum += 5
        else:
            momentum += 3
    else:
        momentum += 2
    if data['recommendation'] == 'strong_buy':
        momentum += 7
    elif data['recommendation'] == 'buy':
        momentum += 4
    elif data['recommendation'] == 'hold':
        momentum += 1
    scores['momentum'] = min(momentum, 25)
    
    scores['total'] = scores['value'] + scores['growth'] + scores['quality'] + scores['momentum']
    
    return scores

for d in datos_acciones:
    scores = calcular_scores(d)
    d['score_value'] = scores['value']
    d['score_growth'] = scores['growth']
    d['score_quality'] = scores['quality']
    d['score_momentum'] = scores['momentum']
    d['score_total'] = scores['total']

datos_acciones.sort(key=lambda x: x['score_total'], reverse=True)

# ==========================================
# 5. CONSTRUIR STRING DE DATOS
# ==========================================
datos_texto = "DATOS DE ACCIONES CON SCORES CALCULADOS (Yahoo Finance):\n\n"
for d in datos_acciones:
    datos_texto += f"""
TICKER: {d['ticker']} | {d['nombre']}
Sector: {d['sector']} | Industria: {d['industria']}
Precio: ${d['precio']} | Máx 52s: ${d['max_52s']}
Caída desde máximo: {d['caida_max']}%
Retorno anual: {d['retorno_anual']}% | Crecimiento 5y: {d['crecimiento_5y']}%
Market Cap: ${d['market_cap_b']}B

=== VALUE ===
Forward P/E: {d['forward_pe']} | PEG: {d['peg']} | EV/EBITDA: {d['ev_ebitda']} | FCF Yield: {d['fcf_yield']}%

=== GROWTH ===
Revenue Growth YoY: {d['revenue_growth']}% | Earnings Growth YoY: {d['earnings_growth']}%
Margen Bruto: {d['gross_margins']}% | Margen Operativo: {d['operating_margins']}% | Margen Neto: {d['net_margins']}%

=== QUALITY ===
ROE: {d['roe']}% | ROIC: {d['roic']}% | Deuda/Equity: {d['debt_to_equity']} | Current Ratio: {d['current_ratio']}

=== MOMENTUM ===
Rating Analistas: {d['recommendation']} | Precio Objetivo: ${d['target_mean']}
Analistas: {d['number_analysts']} | Dividendo: {d['dividend_yield']}%

=== SCORES ===
Value: {d['score_value']}/25 | Growth: {d['score_growth']}/25 | Quality: {d['score_quality']}/25 | Momentum: {d['score_momentum']}/25
TOTAL: {d['score_total']}/100
---"""

# ==========================================
# 6. PROMPT PARA GEMINI
# ==========================================
prompt = f"""{datos_texto}

FECHA: {fecha_legible} | HORA: {hora_madrid} | TOTAL ACCIONES: {len(datos_acciones)}

---

Eres un analista senior de inversiones especializado en value investing con 15 años de experiencia. 
Tu ÚNICO output es un archivo HTML autocontenible con un DASHBOARD DE OPORTUNIDADES DE INVERSIÓN INTERACTIVO.

=== OBJETIVO ===
Crear un dashboard profesional que identifique oportunidades de inversión durante correcciones de mercado, con el estilo que muestra Pao Montes en su video.

=== ESTRUCTURA OBLIGATORIA ===

1. HEADER:
   - Título: "📊 Dashboard de Oportunidades de Inversión"
   - Subtítulo: "Screening de valor durante correcciones de mercado"
   - Fecha y hora en formato "DD/MM/YYYY — HH:MM CEST"
   - Banner de perfil estándar

2. TARJETAS KPI (4 tarjetas):
   - Total de acciones analizadas
   - Oportunidades destacadas (score > 75)
   - Score promedio general
   - Sector con más oportunidades

3. MAPA DE BURBUJAS SVG:
   - Eje X: Score Value (0-25) → "BARATO ↔ CARO"
   - Eje Y: Score Quality (0-25) → "BAJA CALIDAD ↔ ALTA CALIDAD"
   - Tamaño: Market Cap
   - Color: Sector
   - ViewBox: "0 0 900 500"

4. FILTROS INTERACTIVOS:
   - Selector de Sector
   - Slider de Score mínimo
   - Selector de Rating
   - Botón "Resetear filtros"

5. TABLA PRINCIPAL (11 columnas):
   | Ticker | Nombre | Precio | Sector | Caída % | P/E | PEG | ROE % | Growth % | Score | Rating |
   - Ordenable y con detalle expandible

6. DETALLE EXPANDIBLE:
   - 4 barras de progreso: Value, Growth, Quality, Momentum
   - Tesis de inversión
   - Rating y precio objetivo

7. TOP 3 OPORTUNIDADES

8. ANÁLISIS DE RIESGOS (grid 2x2)

9. LECTURA CRÍTICA

10. CHECKLIST DE RIGOR

11. FOOTER con disclaimer

=== CSS ===
Tema oscuro GitHub Dark:
- Fondo: #0d1117
- Texto: #c9d1d9
- Tarjetas: #161b22
- Bordes: #30363d
- Verde: #00d4aa
- Rojo: #ff4757
- Azul: #58a6ff
- Naranja: #f0883e
- Morado: #d2a8ff

=== JAVASCRIPT REQUERIDO ===
1. Ordenación de tabla
2. Filtros
3. Expansión de filas

=== REGLAS ===
1. Usa los datos y scores EXACTOS proporcionados
2. TODAS las acciones deben aparecer en la tabla
3. HTML autocontenido
4. NO uses markdown

Genera el HTML COMPLETO ahora. Empieza directamente con <!DOCTYPE html> sin ningún texto previo."""

print(f"\n📝 Prompt: {len(prompt):,} caracteres")
print("🧠 Generando dashboard interactivo con Gemini...")

# ==========================================
# 7. LLAMADA A GEMINI
# ==========================================
html_dashboard = None

modelos_gemini = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

for modelo in modelos_gemini:
    try:
        print(f"  Intentando con {modelo}...")
        model = genai.GenerativeModel(modelo)
        response = model.generate_content(prompt)
        raw = response.text
        
        if raw and len(raw) > 1000:
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
                    raw = raw[idx:]
            
            html_dashboard = raw
            break
        else:
            print(f"  ❌ {modelo}: respuesta demasiado corta")
    except Exception as e:
        print(f"  ❌ {modelo}: {str(e)[:100]}")
        continue

# ==========================================
# 8. FALLBACK
# ==========================================
if not html_dashboard or len(html_dashboard) < 1000:
    print("⚠️ Usando dashboard de emergencia...")
    # Construir tabla básica de emergencia
    filas_tabla = ""
    for d in datos_acciones[:10]:
        filas_tabla += f"""
        <tr>
            <td><strong>{d['ticker']}</strong></td>
            <td>{d['nombre']}</td>
            <td>${d['precio']}</td>
            <td>{d['sector']}</td>
            <td style="color:{'#00d4aa' if d['caida_max'] > 15 else '#f0883e'}">{d['caida_max']}%</td>
            <td>{d['forward_pe']}</td>
            <td>{d['peg']}</td>
            <td>{d['roe']}%</td>
            <td>{d['revenue_growth']}%</td>
            <td style="font-weight:bold;color:{'#00d4aa' if d['score_total'] > 75 else '#58a6ff'}">{d['score_total']}</td>
            <td>{d['recommendation']}</td>
        </tr>
        """
    
    html_dashboard = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard de Oportunidades - {fecha_legible}</title>
<style>
*{{box-sizing:border-box;}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,sans-serif;margin:0;padding:40px;}}
.wrap{{max-width:1180px;margin:0 auto;}}
header{{border-bottom:2px solid #30363d;padding-bottom:18px;margin-bottom:28px;}}
h1{{color:#f0f6fc;font-size:28px;margin:12px 0 4px;}}
.meta{{color:#8b949e;font-size:13px;}}
.banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:14px 0 20px;}}
.kpi{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:12px 16px;text-align:center;}}
.kpi .num{{font-size:28px;font-weight:700;color:#f0f6fc;}}
.kpi .label{{font-size:12px;color:#8b949e;text-transform:uppercase;}}
table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:6px;overflow:hidden;font-size:13px;}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #21262d;}}
th{{background:#21262d;color:#f0f6fc;font-size:11px;text-transform:uppercase;}}
footer{{margin-top:40px;padding-top:16px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>📊 Dashboard de Oportunidades de Inversión</h1>
  <div class="meta">{fecha_legible} — {hora_madrid} — Modo emergencia</div>
</header>
<div class="banner-perfil"><strong>Perfil estándar.</strong> {len(datos_acciones)} acciones analizadas · S&P 500 + Nasdaq</div>

<div class="kpi-grid">
  <div class="kpi"><div class="num">{len(datos_acciones)}</div><div class="label">Acciones Analizadas</div></div>
  <div class="kpi"><div class="num" style="color:#00d4aa">{len([d for d in datos_acciones if d['score_total'] > 75])}</div><div class="label">Oportunidades >75 pts</div></div>
  <div class="kpi"><div class="num" style="color:#58a6ff">{round(sum(d['score_total'] for d in datos_acciones) / len(datos_acciones), 1)}</div><div class="label">Score Promedio</div></div>
  <div class="kpi"><div class="num" style="color:#f0883e">{max(set([d['sector'] for d in datos_acciones]), key=lambda s: sum(1 for d in datos_acciones if d['sector'] == s))}</div><div class="label">Sector Líder</div></div>
</div>

<h2>📋 Top Oportunidades</h2>
<table>
  <thead><tr><th>Ticker</th><th>Nombre</th><th>Precio</th><th>Sector</th><th>Caída %</th><th>P/E</th><th>PEG</th><th>ROE %</th><th>Growth %</th><th>Score</th><th>Rating</th></tr></thead>
  <tbody>{filas_tabla}</tbody>
</table>

<footer>
  <p><strong>Aviso.</strong> Información general de mercado. No asesoramiento financiero.</p>
  <p>Datos: Yahoo Finance · {fecha_legible} {hora_madrid}</p>
</footer>
</div>
</body>
</html>"""

# ==========================================
# 9. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("dashboard-historico", exist_ok=True)

with open("dashboard-latest.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print(f"\n✅ dashboard-latest.html guardado ({len(html_dashboard):,} caracteres)")

with open(f"dashboard-historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print(f"✅ dashboard-historico/{fecha_hoy}.html guardado")

print("\n🎉 DASHBOARD COMPLETADO")

import yfinance as yf
import os
import re
import glob
from datetime import datetime
from curl_cffi import requests
from google import genai

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("⚠️  API Key no encontrada. Dashboard en modo estático.")
    MODO_IA = False
else:
    MODO_IA = True
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ Error al inicializar Gemini: {e}")
        MODO_IA = False

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
# 2. DESCARGAR DATOS (sin cambios)
# ==========================================
acciones = {
    "NVDA": "Nvidia",
    "META": "Meta Platforms",
    "MSFT": "Microsoft",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "CRM": "Salesforce",
    "ORCL": "Oracle",
    "AMZN": "Amazon",
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "V": "Visa",
    "COST": "Costco",
    "JPM": "JPMorgan",
    "LLY": "Eli Lilly",
}

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"
})

datos_acciones = []
print("📡 Descargando datos de acciones...")
for ticker, nombre in acciones.items():
    try:
        t = yf.Ticker(ticker, session=session)
        hist = t.history(period="1y")
        info = t.info
        if len(hist) < 2: continue
        precio = float(hist["Close"].iloc[-1])
        max_52s = float(hist["High"].max())
        caida = ((max_52s - precio) / max_52s) * 100 if max_52s > 0 else 0
        sector = info.get("sector", "N/A")
        roe = info.get("returnOnEquity", 0) * 100
        revenue_growth = info.get("revenueGrowth", 0) * 100
        forward_pe = info.get("forwardPE", 0)
        recommendation = info.get("recommendationKey", "N/A")
        market_cap = info.get("marketCap", 0)
        datos_acciones.append({
            "ticker": ticker,
            "nombre": nombre,
            "precio": round(precio, 2),
            "caida": round(caida, 2),
            "sector": sector,
            "roe": round(roe, 2),
            "growth": round(revenue_growth, 2),
            "pe": round(forward_pe, 2) if forward_pe else 0,
            "rating": recommendation,
            "market_cap": market_cap,
            "score": round(100 - caida * 0.5 + roe * 0.3 + revenue_growth * 0.2, 1)
        })
        print(f"  ✓ {ticker}: ${precio:.2f} | Caída: {caida:.1f}%")
    except Exception as e:
        print(f"  ❌ {ticker}: {str(e)[:50]}")
        continue

datos_acciones.sort(key=lambda x: x['score'], reverse=True)

# ==========================================
# 3. GENERAR DASHBOARD
# ==========================================
def generar_html_dashboard(datos):
    """Genera el HTML del dashboard con o sin IA"""
    tabla_html = ""
    for d in datos[:10]:
        color_score = "#00d4aa" if d['score'] > 70 else "#58a6ff" if d['score'] > 50 else "#f0883e"
        color_caida = "#00d4aa" if d['caida'] > 15 else "#f0883e" if d['caida'] > 5 else "#ff4757"
        rating_badge = d['rating'].upper() if d['rating'] else "N/A"
        tabla_html += f"""
        <tr>
            <td><strong style="color:#58a6ff;">{d['ticker']}</strong></td>
            <td>{d['nombre']}</td>
            <td>${d['precio']}</td>
            <td>{d['sector']}</td>
            <td style="color:{color_caida};">{d['caida']}%</td>
            <td>{d['pe']}</td>
            <td style="color:{'#00d4aa' if d['roe'] > 20 else '#f0883e'};">{d['roe']}%</td>
            <td style="color:{'#00d4aa' if d['growth'] > 15 else '#f0883e'};">{d['growth']}%</td>
            <td style="font-weight:bold;color:{color_score};">{d['score']}</td>
            <td>{rating_badge}</td>
        </tr>
        """
    
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dashboard - {fecha_legible}</title>
    <style>
        *{{box-sizing:border-box;}}
        body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.6;margin:0;padding:30px;}}
        .wrap{{max-width:1200px;margin:0 auto;}}
        header{{border-bottom:2px solid #30363d;padding-bottom:20px;margin-bottom:30px;}}
        h1{{color:#f0f6fc;font-size:28px;margin:12px 0 4px;}}
        .meta{{color:#8b949e;font-size:14px;margin-top:6px;}}
        .kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin:20px 0;}}
        .kpi{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;text-align:center;}}
        .kpi .num{{font-size:32px;font-weight:700;color:#f0f6fc;}}
        .kpi .label{{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-top:4px;}}
        table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;font-size:14px;}}
        th,td{{padding:12px;text-align:left;border-bottom:1px solid #21262d;}}
        th{{background:#21262d;color:#f0f6fc;font-size:11px;text-transform:uppercase;letter-spacing:.04em;}}
        td.num{{text-align:right;font-family:"SF Mono",Menlo,monospace;}}
        .banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
        footer{{margin-top:40px;padding-top:20px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
        @media(max-width:720px){{th,td{{font-size:11px;padding:8px;}}}}
    </style>
</head>
<body>
<div class="wrap">
    <header>
        <h1>📊 Dashboard de Oportunidades</h1>
        <div class="meta">{fecha_legible} — {hora_madrid}</div>
    </header>
    <div class="banner-perfil">
        <strong>Perfil estándar.</strong> {len(datos)} acciones analizadas · 
        Criterios: Value · Growth · Quality · Momentum
    </div>
    <div class="kpi-grid">
        <div class="kpi"><div class="num">{len(datos)}</div><div class="label">Acciones Analizadas</div></div>
        <div class="kpi"><div class="num" style="color:#00d4aa">{len([d for d in datos if d['score'] > 70])}</div><div class="label">Oportunidades >70 pts</div></div>
        <div class="kpi"><div class="num" style="color:#58a6ff">{round(sum(d['score'] for d in datos)/len(datos), 1) if datos else 0}</div><div class="label">Score Promedio</div></div>
        <div class="kpi"><div class="num" style="color:#f0883e">{max(set([d['sector'] for d in datos]), key=lambda s: sum(1 for d in datos if d['sector'] == s)) if datos else "N/A"}</div><div class="label">Sector Líder</div></div>
    </div>
    <h2>📋 Top Oportunidades</h2>
    <div style="overflow-x:auto;">
        <table>
            <thead><tr><th>Ticker</th><th>Nombre</th><th>Precio</th><th>Sector</th><th>Caída %</th><th>P/E</th><th>ROE %</th><th>Growth %</th><th>Score</th><th>Rating</th></tr></thead>
            <tbody>{tabla_html}</tbody>
        </table>
    </div>
    <footer>
        <p><strong>Aviso:</strong> Información general de mercado, no asesoramiento financiero.</p>
        <p>Datos: Yahoo Finance · {fecha_legible}</p>
    </footer>
</div>
</body>
</html>"""

html_dashboard = None

if MODO_IA and datos_acciones:
    try:
        print("🧠 Generando dashboard con IA...")
        prompt = f"""DATOS DE ACCIONES:
{chr(10).join([f"- {d['ticker']}: ${d['precio']} | Caída: {d['caida']}% | ROE: {d['roe']}% | Crecimiento: {d['growth']}% | Score: {d['score']}" for d in datos_acciones[:10]])}

Genera un dashboard HTML profesional con estos datos. Incluye:
1. Header con fecha {fecha_legible}
2. 4 tarjetas KPI (total, oportunidades, score promedio, sector líder)
3. Tabla con todos los datos
4. Diseño oscuro estilo GitHub
Devuelve solo el HTML."""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        html_dashboard = response.text
        if "```html" in html_dashboard:
            html_dashboard = html_dashboard.split("```html", 1)[1].rsplit("```", 1)[0]
        elif "```" in html_dashboard:
            html_dashboard = html_dashboard.split("```", 1)[1].rsplit("```", 1)[0]
        print("✅ Dashboard generado con IA")
    except Exception as e:
        print(f"⚠️  Error con IA: {e}. Usando plantilla estática.")
        html_dashboard = None

if not html_dashboard or len(html_dashboard) < 500:
    print("⚠️  Usando plantilla de dashboard estática.")
    html_dashboard = generar_html_dashboard(datos_acciones)

# ==========================================
# 4. GUARDAR
# ==========================================
os.makedirs("dashboard-historico", exist_ok=True)

with open("dashboard-latest.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print(f"✅ dashboard-latest.html guardado ({len(html_dashboard):,} caracteres)")

with open(f"dashboard-historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print("✅ dashboard-historico guardado")

print("\n🎉 DASHBOARD COMPLETADO")

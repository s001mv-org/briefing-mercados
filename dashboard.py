import yfinance as yf
import os
import glob
from datetime import datetime
from curl_cffi import requests

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")
fecha_legible = datetime.utcnow().strftime("%d/%m/%Y")
hora_madrid = datetime.utcnow().strftime("%H:%M") + " CEST"

print(f"📊 Generando dashboard para {fecha_legible}")

# ==========================================
# 2. DESCARGAR DATOS DE ACCIONES
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
}

# Configurar sesión para Yahoo Finance
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
})

datos_acciones = []
print("📡 Descargando datos de acciones...")

for ticker, nombre in acciones.items():
    try:
        t = yf.Ticker(ticker, session=session)
        hist = t.history(period="1y")
        info = t.info
        
        if len(hist) < 2:
            print(f"  ⚠️ {ticker}: Historial insuficiente")
            continue
            
        # Precios y caída desde máximo
        precio = float(hist["Close"].iloc[-1])
        max_52s = float(hist["High"].max())
        caida = ((max_52s - precio) / max_52s) * 100 if max_52s > 0 else 0
        
        # Fundamentales
        sector = info.get("sector", "N/A")
        roe = info.get("returnOnEquity", 0) * 100
        revenue_growth = info.get("revenueGrowth", 0) * 100
        earnings_growth = info.get("earningsGrowth", 0) * 100
        forward_pe = info.get("forwardPE", 0)
        recommendation = info.get("recommendationKey", "N/A")
        target_mean = info.get("targetMeanPrice", 0)
        
        # Calcular score (0-100)
        score_value = 0
        if forward_pe and forward_pe > 0:
            if forward_pe < 15: score_value += 25
            elif forward_pe < 20: score_value += 18
            elif forward_pe < 25: score_value += 10
            
        score_growth = 0
        if revenue_growth > 30: score_growth += 25
        elif revenue_growth > 20: score_growth += 18
        elif revenue_growth > 10: score_growth += 10
        
        score_quality = 0
        if roe > 30: score_quality += 25
        elif roe > 20: score_quality += 18
        elif roe > 15: score_quality += 10
        
        score_momentum = 0
        if caida > 20: score_momentum += 25
        elif caida > 15: score_momentum += 20
        elif caida > 10: score_momentum += 10
        if recommendation == "strong_buy": score_momentum += 5
        
        score_total = min(100, score_value + score_growth + score_quality + score_momentum)
        
        datos_acciones.append({
            "ticker": ticker,
            "nombre": nombre,
            "precio": round(precio, 2),
            "max_52s": round(max_52s, 2),
            "caida": round(caida, 2),
            "sector": sector,
            "roe": round(roe, 2),
            "revenue_growth": round(revenue_growth, 2),
            "earnings_growth": round(earnings_growth, 2),
            "forward_pe": round(forward_pe, 2) if forward_pe else 0,
            "rating": recommendation.upper() if recommendation else "N/A",
            "target_mean": round(target_mean, 2) if target_mean else 0,
            "score": score_total,
        })
        print(f"  ✓ {ticker}: ${precio:.2f} | Caída: {caida:.1f}% | Score: {score_total}")
        
    except Exception as e:
        print(f"  ❌ {ticker}: {str(e)[:50]}")
        continue

print(f"\n✅ {len(datos_acciones)} acciones descargadas correctamente")

# Ordenar por score (mejores primero)
datos_acciones.sort(key=lambda x: x['score'], reverse=True)

# ==========================================
# 3. GENERAR HTML DEL DASHBOARD
# ==========================================
print("🧠 Generando dashboard...")

def generar_tabla_html(datos):
    """Genera el HTML de la tabla con los datos"""
    if not datos:
        return '<tr><td colspan="10" style="text-align:center;color:#8b949e;">No hay datos disponibles</td></tr>'
    
    filas = ""
    for d in datos:
        color_score = "#00d4aa" if d['score'] > 70 else "#58a6ff" if d['score'] > 50 else "#f0883e"
        color_caida = "#00d4aa" if d['caida'] > 15 else "#f0883e" if d['caida'] > 5 else "#ff4757"
        
        # Badge de rating
        rating_badge = d['rating']
        if rating_badge == "STRONG BUY":
            rating_badge = '<span style="background:#00d4aa20;color:#00d4aa;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">Strong Buy</span>'
        elif rating_badge == "BUY":
            rating_badge = '<span style="background:#58a6ff20;color:#58a6ff;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">Buy</span>'
        elif rating_badge == "HOLD":
            rating_badge = '<span style="background:#f0883e20;color:#f0883e;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">Hold</span>'
        else:
            rating_badge = '<span style="background:#8b949e20;color:#8b949e;padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">N/A</span>'
        
        filas += f"""
        <tr>
            <td><strong style="color:#58a6ff;">{d['ticker']}</strong></td>
            <td>{d['nombre']}</td>
            <td>${d['precio']:.2f}</td>
            <td>{d['sector']}</td>
            <td style="color:{color_caida};">{d['caida']}%</td>
            <td>{d['forward_pe']}</td>
            <td style="color:{'#00d4aa' if d['roe'] > 20 else '#f0883e'};">{d['roe']}%</td>
            <td style="color:{'#00d4aa' if d['revenue_growth'] > 15 else '#f0883e'};">{d['revenue_growth']}%</td>
            <td style="font-weight:bold;color:{color_score};">{d['score']}</td>
            <td>{rating_badge}</td>
        </tr>
        """
    return filas

def generar_burbujas_svg(datos):
    """Genera un mapa de burbujas SVG simple"""
    if not datos:
        return '<text x="450" y="250" fill="#8b949e" font-size="16" text-anchor="middle">No hay datos para el gráfico</text>'
    
    colores_sector = {
        "Technology": "#58a6ff",
        "Communication Services": "#f0883e",
        "Consumer Cyclical": "#00d4aa",
        "Financial Services": "#ff4757",
        "Healthcare": "#d2a8ff",
        "Consumer Defensive": "#ffd93d",
        "Energy": "#ff6b6b",
        "N/A": "#8b949e",
    }
    
    max_x = 25
    max_y = 25
    burbujas = ""
    
    for d in datos[:12]:  # Top 12 para el gráfico
        x = (d['score'] / 100) * 700 + 100
        y = 430 - (d['roe'] / 100) * 380 if d['roe'] > 0 else 250
        r = max(15, min(35, 20 + d['caida'] / 4))
        color = colores_sector.get(d['sector'], "#8b949e")
        
        burbujas += f'''
        <circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="0.8" stroke="#0d1117" stroke-width="2"/>
        <text x="{x}" y="{y+4}" text-anchor="middle" fill="#f0f6fc" font-size="10" font-weight="bold">{d['ticker']}</text>
        '''
    
    return burbujas

# Generar el HTML completo
tabla_html = generar_tabla_html(datos_acciones)
burbujas_svg = generar_burbujas_svg(datos_acciones)

html_dashboard = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard de Oportunidades - {fecha_legible}</title>
<style>
*{{box-sizing:border-box;}}
body{{background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,sans-serif;font-size:16px;line-height:1.6;margin:0;padding:30px;}}
.wrap{{max-width:1200px;margin:0 auto;}}
header{{border-bottom:2px solid #30363d;padding-bottom:20px;margin-bottom:30px;}}
.tag{{display:inline-block;background:#1f6feb;color:#fff;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:600;text-transform:uppercase;}}
h1{{color:#f0f6fc;font-size:28px;margin:12px 0 4px;font-weight:700;}}
.meta{{color:#8b949e;font-size:14px;margin-top:6px;}}
.banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin:20px 0;}}
.kpi{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;text-align:center;}}
.kpi .num{{font-size:32px;font-weight:700;color:#f0f6fc;}}
.kpi .num.green{{color:#00d4aa;}}
.kpi .num.blue{{color:#58a6ff;}}
.kpi .num.orange{{color:#f0883e;}}
.kpi .label{{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-top:4px;}}
h2{{color:#f0f6fc;font-size:22px;margin:40px 0 12px;padding-bottom:8px;border-bottom:1px solid #30363d;}}
table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;font-size:14px;}}
th,td{{padding:12px;text-align:left;border-bottom:1px solid #21262d;}}
th{{background:#21262d;color:#f0f6fc;font-size:11px;text-transform:uppercase;letter-spacing:.04em;font-weight:600;}}
td.num{{text-align:right;font-family:"SF Mono",Menlo,monospace;}}
footer{{margin-top:40px;padding-top:20px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
footer p{{font-size:12px;margin:6px 0;}}
@media(max-width:720px){{th,td{{font-size:11px;padding:8px;}}}}
</style>
</head>
<body>
<div class="wrap">
    <header>
        <span class="tag">📊 DASHBOARD</span>
        <h1>Dashboard de Oportunidades de Inversión</h1>
        <p style="color:#8b949e;margin:4px 0 0;">Screening de valor durante correcciones de mercado</p>
        <div class="meta">{fecha_legible} — {hora_madrid}</div>
    </header>
    
    <div class="banner-perfil">
        <strong>Perfil estándar.</strong> {len(datos_acciones)} acciones analizadas · 
        S&amp;P 500 + Nasdaq · Criterios: Value · Growth · Quality · Momentum
    </div>
    
    <div class="kpi-grid">
        <div class="kpi"><div class="num">{len(datos_acciones)}</div><div class="label">📊 Acciones Analizadas</div></div>
        <div class="kpi"><div class="num green">{len([d for d in datos_acciones if d['score'] > 70])}</div><div class="label">⭐ Oportunidades (>70 pts)</div></div>
        <div class="kpi"><div class="num blue">{round(sum(d['score'] for d in datos_acciones)/len(datos_acciones), 1) if datos_acciones else 0}</div><div class="label">📈 Score Promedio</div></div>
        <div class="kpi"><div class="num orange">{max(set([d['sector'] for d in datos_acciones]), key=lambda s: sum(1 for d in datos_acciones if d['sector'] == s)) if datos_acciones else "N/A"}</div><div class="label">🏆 Sector Líder</div></div>
    </div>
    
    <h2>🎯 Mapa de Oportunidades</h2>
    <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:16px;text-align:center;">
        <svg viewBox="0 0 900 500" style="max-width:100%;height:auto;">
            <rect x="0" y="0" width="900" height="500" fill="#0d1117" rx="4"/>
            <!-- Ejes -->
            <line x1="100" y1="430" x2="830" y2="430" stroke="#30363d" stroke-width="1.5"/>
            <line x1="100" y1="430" x2="100" y2="50" stroke="#30363d" stroke-width="1.5"/>
            <!-- Etiquetas -->
            <text x="460" y="470" fill="#8b949e" font-size="12" text-anchor="middle">⬅️ Menor Score ··· SCORE TOTAL ··· Mayor Score ➡️</text>
            <text x="40" y="240" fill="#8b949e" font-size="12" text-anchor="middle" transform="rotate(-90,40,240)">⬅️ Menor ROE ··· RENTABILIDAD (ROE) ··· Mayor ROE ➡️</text>
            <!-- Líneas de referencia -->
            <line x1="100" y1="330" x2="830" y2="330" stroke="#30363d" stroke-width="1" stroke-dasharray="4,4"/>
            <line x1="465" y1="430" x2="465" y2="50" stroke="#30363d" stroke-width="1" stroke-dasharray="4,4"/>
            <!-- Burbujas -->
            {burbujas_svg}
            <!-- Leyenda -->
            <rect x="730" y="55" width="160" height="120" fill="#161b22" rx="4" stroke="#30363d" stroke-width="1"/>
            <text x="740" y="75" fill="#f0f6fc" font-size="11" font-weight="bold">SECTORES</text>
            <circle cx="745" cy="95" r="6" fill="#58a6ff"/><text x="758" y="99" fill="#c9d1d9" font-size="10">Technology</text>
            <circle cx="745" cy="115" r="6" fill="#f0883e"/><text x="758" y="119" fill="#c9d1d9" font-size="10">Communication</text>
            <circle cx="745" cy="135" r="6" fill="#00d4aa"/><text x="758" y="139" fill="#c9d1d9" font-size="10">Consumer</text>
            <circle cx="745" cy="155" r="6" fill="#ff4757"/><text x="758" y="159" fill="#c9d1d9" font-size="10">Financial</text>
        </svg>
        <p style="color:#8b949e;font-size:12px;margin:8px 0 0;">Tamaño de burbuja = Caída desde máximo · Color = Sector</p>
    </div>
    
    <h2>📋 Tabla de Oportunidades</h2>
    <p style="color:#8b949e;font-size:13px;margin:-8px 0 12px;">Ordenadas por Score (mejores oportunidades primero)</p>
    <div style="overflow-x:auto;">
        <table>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Nombre</th>
                    <th>Precio</th>
                    <th>Sector</th>
                    <th>Caída %</th>
                    <th>P/E</th>
                    <th>ROE %</th>
                    <th>Growth %</th>
                    <th>Score</th>
                    <th>Rating</th>
                </tr>
            </thead>
            <tbody>
                {tabla_html}
            </tbody>
        </table>
    </div>
    
    <h2>⚠️ Análisis de Riesgos</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;">
        <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 16px;">
            <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;color:#f0883e;">🔴 Riesgos Visibles</h4>
            <p style="font-size:14px;">Corrección técnica en el sector tecnológico · Incertidumbre regulatoria · Desaceleración del crecimiento</p>
        </div>
        <div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 16px;">
            <h4 style="margin:0 0 8px;font-size:12px;text-transform:uppercase;color:#ff4757;">⚫ Riesgos No Descontados</h4>
            <p style="font-size:14px;">Posible recesión global · Conflictos geopolíticos · Cambio en política monetaria</p>
        </div>
    </div>
    
    <h2>📖 Lectura Crítica</h2>
    <div style="background:#161b22;border-left:4px solid #ff4757;padding:12px 16px;margin:12px 0;border-radius:0 4px 4px 0;">
        <strong>⚠️ ¿Estamos comprando una corrección o el inicio de un mercado bajista?</strong>
    </div>
    <p style="font-size:15px;">La narrativa dominante sugiere que las caídas en el sector tecnológico son oportunidades de compra. Sin embargo, debemos cuestionar si el mercado está descontando correctamente el riesgo de una desaceleración económica más profunda.</p>
    
    <footer>
        <p><strong>Aviso.</strong> Este dashboard es información general de mercado, no asesoramiento financiero ni recomendación de inversión personalizada.</p>
        <p>Datos: Yahoo Finance · Generado automáticamente · {fecha_legible} {hora_madrid}</p>
    </footer>
</div>
</body>
</html>"""

# ==========================================
# 4. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("dashboard-historico", exist_ok=True)

with open("dashboard-latest.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print(f"✅ dashboard-latest.html guardado ({len(html_dashboard):,} caracteres)")

with open(f"dashboard-historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_dashboard)
print(f"✅ dashboard-historico/{fecha_hoy}.html guardado")

print("\n🎉 DASHBOARD COMPLETADO")

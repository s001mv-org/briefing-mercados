import yfinance as yf
import os
import glob
from datetime import datetime, timedelta
from curl_cffi import requests

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")
fecha_legible = datetime.utcnow().strftime("%d/%m/%Y")
hora_madrid = datetime.utcnow().strftime("%H:%M") + " CEST"

print(f"📊 Generando dashboard completo para {fecha_legible}")

# ==========================================
# 2. LISTA DE ACCIONES (18 empresas)
# ==========================================
acciones = {
    # Tecnológicas
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
    # Financieras
    "V": "Visa",
    "JPM": "JPMorgan Chase",
    # Consumo
    "COST": "Costco",
    "KO": "Coca-Cola",
    "PG": "Procter & Gamble",
    # Salud
    "LLY": "Eli Lilly",
    # Otros
    "TSLA": "Tesla",
    "NFLX": "Netflix",
}

# Colores por sector
sector_colores = {
    "Technology": "#58a6ff",
    "Communication Services": "#f0883e",
    "Consumer Cyclical": "#00d4aa",
    "Financial Services": "#ff4757",
    "Healthcare": "#d2a8ff",
    "Consumer Defensive": "#ffd93d",
    "N/A": "#8b949e",
}

# ==========================================
# 3. DESCARGAR DATOS (con variación 24h)
# ==========================================
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
        # Descargar 2 años para datos históricos y 5 días para variación
        hist = t.history(period="2y")
        hist_5d = t.history(period="5d")
        info = t.info
        
        if len(hist) < 2 or len(hist_5d) < 2:
            print(f"  ⚠️ {ticker}: Historial insuficiente")
            continue
            
        # Precio actual
        precio = float(hist["Close"].iloc[-1])
        max_52s = float(hist["High"].max())
        caida = ((max_52s - precio) / max_52s) * 100 if max_52s > 0 else 0
        
        # Variación 24h (real)
        hist_5d_clean = hist_5d[hist_5d["Close"].notna()]
        if len(hist_5d_clean) >= 2:
            c_hoy = float(hist_5d_clean["Close"].iloc[-1])
            c_ayer = float(hist_5d_clean["Close"].iloc[-2])
            var_24h = ((c_hoy - c_ayer) / c_ayer) * 100
        else:
            var_24h = 0
        
        # Retorno anual
        if len(hist) >= 252:
            precio_anio = float(hist["Close"].iloc[-252])
            retorno_anual = ((precio - precio_anio) / precio_anio) * 100
        else:
            retorno_anual = 0
        
        # Fundamentales (reales)
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")
        market_cap = info.get("marketCap", 0)
        market_cap_b = round(market_cap / 1e9, 2) if market_cap else 0
        
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
        
        # Rating REAL de analistas (múltiples fuentes)
        recommendation = info.get("recommendationKey", "")
        average_rating = info.get("averageAnalystRating", "")
        
        # Construir rating con la mejor fuente disponible
        if recommendation:
            rating_real = recommendation
        elif average_rating:
            # Convertir rating numérico a texto
            try:
                rating_num = float(average_rating)
                if rating_num <= 1.5:
                    rating_real = "strong_buy"
                elif rating_num <= 2.5:
                    rating_real = "buy"
                elif rating_num <= 3.5:
                    rating_real = "hold"
                elif rating_num <= 4.5:
                    rating_real = "sell"
                else:
                    rating_real = "strong_sell"
            except:
                rating_real = "N/A"
        else:
            rating_real = "N/A"
        
        target_mean = info.get("targetMeanPrice", 0)
        target_high = info.get("targetHighPrice", 0)
        target_low = info.get("targetLowPrice", 0)
        number_analysts = info.get("numberOfAnalystOpinions", 0)
        
        dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
        
        # ==========================================
        # 4. CALCULAR SCORES (4 pilares)
        # ==========================================
        # VALUE (0-25)
        value_score = 0
        if forward_pe and forward_pe > 0:
            if forward_pe < 10: value_score += 8
            elif forward_pe < 15: value_score += 6
            elif forward_pe < 20: value_score += 4
            elif forward_pe < 25: value_score += 2
        if peg and peg > 0:
            if peg < 0.5: value_score += 7
            elif peg < 1: value_score += 5
            elif peg < 1.5: value_score += 3
            elif peg < 2: value_score += 1
        if ev_ebitda and ev_ebitda > 0:
            if ev_ebitda < 8: value_score += 5
            elif ev_ebitda < 12: value_score += 4
            elif ev_ebitda < 15: value_score += 3
            elif ev_ebitda < 20: value_score += 1
        if fcf_yield and fcf_yield > 0:
            if fcf_yield > 10: value_score += 5
            elif fcf_yield > 5: value_score += 4
            elif fcf_yield > 3: value_score += 2
            elif fcf_yield > 1: value_score += 1
        value_score = min(value_score, 25)
        
        # GROWTH (0-25)
        growth_score = 0
        if revenue_growth > 50: growth_score += 9
        elif revenue_growth > 30: growth_score += 7
        elif revenue_growth > 20: growth_score += 5
        elif revenue_growth > 10: growth_score += 3
        elif revenue_growth > 5: growth_score += 1
        if earnings_growth > 50: growth_score += 8
        elif earnings_growth > 30: growth_score += 6
        elif earnings_growth > 20: growth_score += 4
        elif earnings_growth > 10: growth_score += 2
        elif earnings_growth > 5: growth_score += 1
        if gross_margins > 40: growth_score += 3
        if operating_margins > 20: growth_score += 3
        if net_margins > 15: growth_score += 2
        growth_score = min(growth_score, 25)
        
        # QUALITY (0-25)
        quality_score = 0
        if roe > 50: quality_score += 7
        elif roe > 30: quality_score += 5
        elif roe > 20: quality_score += 4
        elif roe > 15: quality_score += 2
        elif roe > 10: quality_score += 1
        if roic > 30: quality_score += 6
        elif roic > 20: quality_score += 5
        elif roic > 15: quality_score += 3
        elif roic > 10: quality_score += 1
        if debt_to_equity > 0:
            if debt_to_equity < 0.3: quality_score += 6
            elif debt_to_equity < 0.6: quality_score += 5
            elif debt_to_equity < 1: quality_score += 4
            elif debt_to_equity < 1.5: quality_score += 2
            elif debt_to_equity < 2: quality_score += 1
        else:
            quality_score += 3
        if net_margins > 20: quality_score += 6
        elif net_margins > 15: quality_score += 4
        elif net_margins > 10: quality_score += 2
        elif net_margins > 5: quality_score += 1
        quality_score = min(quality_score, 25)
        
        # MOMENTUM (0-25)
        momentum_score = 0
        if caida > 30: momentum_score += 10
        elif caida > 20: momentum_score += 8
        elif caida > 15: momentum_score += 6
        elif caida > 10: momentum_score += 4
        elif caida > 5: momentum_score += 2
        if retorno_anual < 0:
            if roe > 20 and revenue_growth > 15:
                momentum_score += 8
            elif roe > 15 and revenue_growth > 10:
                momentum_score += 5
            else:
                momentum_score += 3
        else:
            momentum_score += 2
        if rating_real == "strong_buy":
            momentum_score += 7
        elif rating_real == "buy":
            momentum_score += 4
        elif rating_real == "hold":
            momentum_score += 1
        momentum_score = min(momentum_score, 25)
        
        score_total = value_score + growth_score + quality_score + momentum_score
        
        # Guardar datos
        datos_acciones.append({
            "ticker": ticker,
            "nombre": nombre,
            "precio": round(precio, 2),
            "max_52s": round(max_52s, 2),
            "caida": round(caida, 2),
            "var_24h": round(var_24h, 2),
            "retorno_anual": round(retorno_anual, 2),
            "sector": sector,
            "industria": industry,
            "market_cap_b": market_cap_b,
            "forward_pe": round(forward_pe, 2) if forward_pe else 0,
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
            "recommendation": rating_real,
            "target_mean": round(target_mean, 2) if target_mean else 0,
            "target_high": round(target_high, 2) if target_high else 0,
            "target_low": round(target_low, 2) if target_low else 0,
            "number_analysts": number_analysts,
            "dividend_yield": round(dividend_yield, 2),
            "score_value": value_score,
            "score_growth": growth_score,
            "score_quality": quality_score,
            "score_momentum": momentum_score,
            "score_total": score_total,
        })
        print(f"  ✓ {ticker}: ${precio:.2f} | Var 24h: {var_24h:+.1f}% | Score: {score_total} | Rating: {rating_real}")
        
    except Exception as e:
        print(f"  ❌ {ticker}: {str(e)[:50]}")
        continue

print(f"\n✅ {len(datos_acciones)} acciones descargadas correctamente")

# Ordenar por score total
datos_acciones.sort(key=lambda x: x['score_total'], reverse=True)

# ==========================================
# 5. GENERAR GRÁFICO DE BARRAS 24h (SVG)
# ==========================================
def generar_grafico_barras(datos):
    """Genera un gráfico de barras SVG con la variación 24h de cada acción"""
    if not datos:
        return '<text x="450" y="30" fill="#8b949e" font-size="14" text-anchor="middle">No hay datos</text>'
    
    # Tomar las 10 principales para el gráfico
    top_datos = datos[:10]
    max_abs_var = max([abs(d['var_24h']) for d in top_datos]) or 1
    
    barras = ""
    ancho_barra = 50
    separacion = 10
    x_inicio = 50
    
    for i, d in enumerate(top_datos):
        x = x_inicio + i * (ancho_barra + separacion)
        altura = (abs(d['var_24h']) / max_abs_var) * 150 if max_abs_var > 0 else 10
        altura = max(5, min(150, altura))
        
        color = "#00d4aa" if d['var_24h'] >= 0 else "#ff4757"
        y = 180 - altura if d['var_24h'] >= 0 else 180
        
        barras += f'''
        <rect x="{x}" y="{y}" width="{ancho_barra}" height="{altura}" fill="{color}" rx="3" opacity="0.9"/>
        <text x="{x + ancho_barra/2}" y="200" text-anchor="middle" fill="#c9d1d9" font-size="9" font-weight="bold">{d['ticker']}</text>
        <text x="{x + ancho_barra/2}" y="{y-6}" text-anchor="middle" fill="{color}" font-size="10" font-weight="bold">{d['var_24h']:+.1f}%</text>
        '''
    
    return f'''
    <svg viewBox="0 0 650 230" style="width:100%;height:auto;">
        <rect x="0" y="0" width="650" height="230" fill="#0d1117" rx="4"/>
        <!-- Línea del cero -->
        <line x1="30" y1="180" x2="620" y2="180" stroke="#30363d" stroke-width="1.5"/>
        <!-- Barras -->
        {barras}
        <!-- Etiquetas -->
        <text x="325" y="225" fill="#8b949e" font-size="11" text-anchor="middle">Variación 24h (%) · Top 10 acciones</text>
    </svg>
    '''

# ==========================================
# 6. GENERAR HTML COMPLETO
# ==========================================
print("🧠 Generando dashboard completo...")

# --- 6.1 Generar tabla HTML ---
def generar_tabla_html(datos):
    if not datos:
        return '<tr><td colspan="10" style="text-align:center;color:#8b949e;">No hay datos disponibles</td></tr>'
    
    filas = ""
    for d in datos:
        color_score = "#00d4aa" if d['score_total'] > 70 else "#58a6ff" if d['score_total'] > 50 else "#f0883e" if d['score_total'] > 30 else "#ff4757"
        color_caida = "#00d4aa" if d['caida'] > 15 else "#f0883e" if d['caida'] > 5 else "#ff4757"
        color_var = "#00d4aa" if d['var_24h'] >= 0 else "#ff4757"
        
        # Badge de rating con colores mejorados
        rating_badge = d['recommendation'].upper() if d['recommendation'] and d['recommendation'] != "N/A" else "N/A"
        if rating_badge == "STRONG BUY" or rating_badge == "STRONG_BUY":
            rating_badge = '<span class="badge-bull">🔹 Strong Buy</span>'
        elif rating_badge == "BUY":
            rating_badge = '<span class="badge-buy">🔹 Buy</span>'
        elif rating_badge == "HOLD":
            rating_badge = '<span class="badge-hold">🔹 Hold</span>'
        elif rating_badge == "SELL" or rating_badge == "STRONG SELL":
            rating_badge = '<span class="badge-sell">🔹 Sell</span>'
        else:
            rating_badge = '<span class="badge-na">⚪ N/A</span>'
        
        filas += f"""
        <tr onclick="toggleDetail('{d['ticker']}')" style="cursor:pointer;" class="data-row">
            <td><strong style="color:#58a6ff;">{d['ticker']}</strong></td>
            <td>{d['nombre']}</td>
            <td class="num">${d['precio']:.2f}</td>
            <td data-sector="{d['sector']}">{d['sector']}</td>
            <td class="num" style="color:{color_caida};">{d['caida']}%</td>
            <td class="num" style="color:{color_var};">{d['var_24h']:+.2f}%</td>
            <td class="num">{d['forward_pe']}</td>
            <td class="num" style="color:{'#00d4aa' if d['roe'] > 20 else '#f0883e'};">{d['roe']}%</td>
            <td class="num" style="color:{'#00d4aa' if d['revenue_growth'] > 15 else '#f0883e'};">{d['revenue_growth']}%</td>
            <td class="num" style="font-weight:bold;color:{color_score};">{d['score_total']}</td>
            <td>{rating_badge}</td>
        </tr>
        <tr id="detail-{d['ticker']}" style="display:none;background:#0d1117;">
            <td colspan="11" style="padding:16px 20px;">
                <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px;">
                    <div style="background:#161b22;padding:10px;border-radius:4px;border-left:3px solid #58a6ff;">
                        <div style="font-size:11px;color:#8b949e;">VALUE</div>
                        <div style="font-size:18px;font-weight:700;color:#f0f6fc;">{d['score_value']}/25</div>
                        <div style="width:100%;background:#21262d;border-radius:4px;height:4px;margin-top:4px;">
                            <div style="width:{d['score_value']/25*100}%;background:#58a6ff;height:100%;border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="background:#161b22;padding:10px;border-radius:4px;border-left:3px solid #00d4aa;">
                        <div style="font-size:11px;color:#8b949e;">GROWTH</div>
                        <div style="font-size:18px;font-weight:700;color:#f0f6fc;">{d['score_growth']}/25</div>
                        <div style="width:100%;background:#21262d;border-radius:4px;height:4px;margin-top:4px;">
                            <div style="width:{d['score_growth']/25*100}%;background:#00d4aa;height:100%;border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="background:#161b22;padding:10px;border-radius:4px;border-left:3px solid #d2a8ff;">
                        <div style="font-size:11px;color:#8b949e;">QUALITY</div>
                        <div style="font-size:18px;font-weight:700;color:#f0f6fc;">{d['score_quality']}/25</div>
                        <div style="width:100%;background:#21262d;border-radius:4px;height:4px;margin-top:4px;">
                            <div style="width:{d['score_quality']/25*100}%;background:#d2a8ff;height:100%;border-radius:4px;"></div>
                        </div>
                    </div>
                    <div style="background:#161b22;padding:10px;border-radius:4px;border-left:3px solid #f0883e;">
                        <div style="font-size:11px;color:#8b949e;">MOMENTUM</div>
                        <div style="font-size:18px;font-weight:700;color:#f0f6fc;">{d['score_momentum']}/25</div>
                        <div style="width:100%;background:#21262d;border-radius:4px;height:4px;margin-top:4px;">
                            <div style="width:{d['score_momentum']/25*100}%;background:#f0883e;height:100%;border-radius:4px;"></div>
                        </div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:13px;color:#c9d1d9;">
                    <div>
                        <strong style="color:#f0f6fc;">📊 Métricas clave</strong><br>
                        ROIC: {d['roic']}% · Margen Neto: {d['net_margins']}%<br>
                        Deuda/Equity: {d['debt_to_equity']} · FCF Yield: {d['fcf_yield']}%<br>
                        PEG: {d['peg']} · EV/EBITDA: {d['ev_ebitda']}
                    </div>
                    <div>
                        <strong style="color:#f0f6fc;">🎯 Rating Analistas</strong><br>
                        {d['recommendation'].upper()} · Precio Objetivo: ${d['target_mean']}<br>
                        {d['number_analysts']} analistas · Máx: ${d['target_high']} · Mín: ${d['target_low']}<br>
                        Dividendo: {d['dividend_yield']}% · Market Cap: ${d['market_cap_b']}B
                    </div>
                </div>
            </td>
        </tr>
        """
    return filas

# --- 6.2 Generar burbujas SVG ---
def generar_burbujas_svg(datos):
    if not datos:
        return '<text x="450" y="250" fill="#8b949e" font-size="16" text-anchor="middle">No hay datos para el gráfico</text>'
    
    burbujas = ""
    for d in datos[:15]:
        x = d['score_value'] / 25 * 700 + 100
        y = 430 - (d['score_quality'] / 25) * 380 if d['score_quality'] > 0 else 250
        r = max(12, min(35, 15 + d['market_cap_b'] / 100))
        color = sector_colores.get(d['sector'], "#8b949e")
        
        burbujas += f'''
        <circle cx="{x}" cy="{y}" r="{r}" fill="{color}" opacity="0.8" stroke="#0d1117" stroke-width="2"/>
        <text x="{x}" y="{y+4}" text-anchor="middle" fill="#f0f6fc" font-size="10" font-weight="bold">{d['ticker']}</text>
        '''
    
    return burbujas

# --- 6.3 Generar Top 3 ---
def generar_top3(datos):
    if len(datos) < 3:
        return '<p style="color:#8b949e;">No hay suficientes datos para mostrar el Top 3</p>'
    
    top_html = ""
    colores_top = ["#00d4aa", "#58a6ff", "#f0883e"]
    for i, d in enumerate(datos[:3]):
        color_score = "#00d4aa" if d['score_total'] > 70 else "#58a6ff"
        color_caida = "#00d4aa" if d['caida'] > 15 else "#f0883e"
        rating_clean = d['recommendation'].upper() if d['recommendation'] and d['recommendation'] != "N/A" else "N/A"
        top_html += f"""
        <div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;border-top:3px solid {colores_top[i]};">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-size:20px;font-weight:700;color:#f0f6fc;">#{i+1} {d['ticker']}</span>
                <span style="font-size:24px;font-weight:700;color:{color_score};">{d['score_total']}</span>
            </div>
            <div style="color:#8b949e;font-size:13px;">{d['nombre']} · {d['sector']}</div>
            <div style="margin:8px 0;font-size:14px;">
                <span style="color:{color_caida};">⬇️ {d['caida']}%</span>
                · ROE: {d['roe']}% · Crecimiento: {d['revenue_growth']}%
            </div>
            <div style="font-size:13px;color:#c9d1d9;">Precio: ${d['precio']} · Objetivo: ${d['target_mean']} · {rating_clean}</div>
        </div>
        """
    return top_html

# --- 6.4 Generar HTML completo ---
grafico_barras = generar_grafico_barras(datos_acciones)
tabla_html = generar_tabla_html(datos_acciones)
burbujas_svg = generar_burbujas_svg(datos_acciones)
top3_html = generar_top3(datos_acciones)

html_completo = f"""<!DOCTYPE html>
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
.tag{{display:inline-block;background:#1f6feb;color:#fff;padding:3px 10px;border-radius:3px;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;}}
h1{{color:#f0f6fc;font-size:30px;margin:12px 0 4px;font-weight:700;}}
h2{{color:#f0f6fc;font-size:22px;margin:40px 0 12px;padding-bottom:8px;border-bottom:1px solid #30363d;}}
.meta{{color:#8b949e;font-size:14px;margin-top:6px;}}
.banner-perfil{{background:#1f6feb15;border:1px solid #1f6feb55;padding:10px 14px;border-radius:4px;font-size:13px;margin-bottom:20px;}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin:20px 0;}}
.kpi{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:15px;text-align:center;}}
.kpi .num{{font-size:32px;font-weight:700;color:#f0f6fc;}}
.kpi .num.green{{color:#00d4aa;}}
.kpi .num.blue{{color:#58a6ff;}}
.kpi .num.orange{{color:#f0883e;}}
.kpi .num.purple{{color:#d2a8ff;}}
.kpi .label{{font-size:12px;color:#8b949e;text-transform:uppercase;letter-spacing:.06em;margin-top:4px;}}
.filter-bar{{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:16px 0;padding:12px 20px;background:#161b22;border:1px solid #30363d;border-radius:8px;}}
.filter-bar select,.filter-bar input{{background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:6px;padding:8px 14px;font-size:13px;}}
.filter-bar button{{background:#1f6feb;color:#fff;border:none;border-radius:6px;padding:8px 20px;font-size:13px;font-weight:600;cursor:pointer;}}
.filter-bar button:hover{{background:#388bfd;}}
.filter-bar label{{font-size:13px;color:#8b949e;}}
table{{width:100%;border-collapse:collapse;margin:10px 0 18px;font-size:13px;background:#161b22;border:1px solid #30363d;border-radius:6px;overflow:hidden;}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #21262d;}}
th{{background:#21262d;color:#f0f6fc;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em;cursor:pointer;user-select:none;position:sticky;top:0;z-index:10;}}
th:hover{{background:#30363d;}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;font-family:"SF Mono",Menlo,monospace;}}
.badge-bull{{background:#00d4aa25;color:#00d4aa;border:1px solid #00d4aa55;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}}
.badge-buy{{background:#58a6ff25;color:#58a6ff;border:1px solid #58a6ff55;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}}
.badge-hold{{background:#f0883e25;color:#f0883e;border:1px solid #f0883e55;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}}
.badge-sell{{background:#ff475725;color:#ff4757;border:1px solid #ff475755;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}}
.badge-na{{background:#8b949e25;color:#8b949e;border:1px solid #8b949e55;padding:3px 10px;border-radius:4px;font-size:11px;font-weight:600;}}
.risk-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;}}
.risk-card{{background:#161b22;border:1px solid #30363d;border-radius:6px;padding:14px 16px;}}
.risk-card h4{{margin:0 0 8px;font-size:12px;text-transform:uppercase;letter-spacing:.06em;font-weight:600;}}
.risk-card.visible h4{{color:#f0883e;}}
.risk-card.hidden h4{{color:#ff4757;}}
.risk-card.scenario h4{{color:#58a6ff;}}
.risk-card.signal h4{{color:#00d4aa;}}
.risk-card p{{margin:0;font-size:14px;line-height:1.55;}}
.callout-danger{{background:#161b22;border-left:4px solid #ff4757;padding:12px 16px;margin:12px 0;border-radius:0 4px 4px 0;}}
.callout-danger strong{{color:#ff4757;}}
footer{{margin-top:40px;padding-top:20px;border-top:1px solid #30363d;color:#8b949e;font-size:12px;}}
footer p{{font-size:12px;margin:6px 0;}}
ul.check{{list-style:none;padding:0;margin:8px 0;}}
ul.check li{{padding:6px 0;border-bottom:1px solid #21262d;font-size:14px;}}
ul.check li:last-child{{border-bottom:none;}}
@media(max-width:720px){{.risk-grid{{grid-template-columns:1fr;}}h1{{font-size:24px;}}th,td{{font-size:11px;padding:6px 8px;}}}}
</style>
</head>
<body>
<div class="wrap">

<!-- ===== HEADER ===== -->
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

<!-- ===== KPI GRID ===== -->
<div class="kpi-grid">
    <div class="kpi"><div class="num">{len(datos_acciones)}</div><div class="label">📊 Acciones Analizadas</div></div>
    <div class="kpi"><div class="num green">{len([d for d in datos_acciones if d['score_total'] > 70])}</div><div class="label">⭐ Oportunidades (>70 pts)</div></div>
    <div class="kpi"><div class="num blue">{round(sum(d['score_total'] for d in datos_acciones)/len(datos_acciones), 1) if datos_acciones else 0}</div><div class="label">📈 Score Promedio</div></div>
    <div class="kpi"><div class="num orange">{max(set([d['sector'] for d in datos_acciones]), key=lambda s: sum(1 for d in datos_acciones if d['sector'] == s)) if datos_acciones else "N/A"}</div><div class="label">🏆 Sector Líder</div></div>
</div>

<!-- ===== GRÁFICO DE BARRAS 24h ===== -->
<h2>📊 Variación 24h (Top 10 acciones)</h2>
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:10px;">
    {grafico_barras}
</div>

<!-- ===== MAPA DE BURBUJAS ===== -->
<h2>🎯 Mapa de Oportunidades</h2>
<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;text-align:center;">
    <svg viewBox="0 0 900 500" style="max-width:100%;height:auto;">
        <rect x="0" y="0" width="900" height="500" fill="#0d1117" rx="4"/>
        <line x1="100" y1="430" x2="830" y2="430" stroke="#30363d" stroke-width="1.5"/>
        <line x1="100" y1="430" x2="100" y2="50" stroke="#30363d" stroke-width="1.5"/>
        <text x="460" y="470" fill="#8b949e" font-size="12" text-anchor="middle">⬅️ Barato ··· VALUE ··· Caro ➡️</text>
        <text x="40" y="240" fill="#8b949e" font-size="12" text-anchor="middle" transform="rotate(-90,40,240)">⬅️ Baja Calidad ··· QUALITY ··· Alta Calidad ➡️</text>
        <line x1="100" y1="330" x2="830" y2="330" stroke="#30363d" stroke-width="1" stroke-dasharray="4,4"/>
        <line x1="465" y1="430" x2="465" y2="50" stroke="#30363d" stroke-width="1" stroke-dasharray="4,4"/>
        {burbujas_svg}
        <rect x="730" y="55" width="160" height="120" fill="#161b22" rx="4" stroke="#30363d" stroke-width="1"/>
        <text x="740" y="75" fill="#f0f6fc" font-size="11" font-weight="bold">SECTORES</text>
        {''.join([f'<circle cx="745" cy="{{95+i*20}}" r="6" fill="{{color}}"/><text x="758" y="{{99+i*20}}" fill="#c9d1d9" font-size="10">{{sector}}</text>' for i,(sector,color) in enumerate(list(sector_colores.items())[:5])])}
    </svg>
    <p style="color:#8b949e;font-size:12px;margin:8px 0 0;">Tamaño de burbuja = Capitalización de mercado · Color = Sector</p>
</div>

<!-- ===== FILTROS ===== -->
<h2>🔍 Filtros Interactivos</h2>
<div class="filter-bar">
    <select id="sectorFilter" onchange="aplicarFiltros()">
        <option value="all">Todos los sectores</option>
        {''.join([f'<option value="{s}">{s}</option>' for s in sorted(set([d['sector'] for d in datos_acciones]))])}
    </select>
    <label>Score mínimo:</label>
    <input type="range" id="scoreFilter" min="0" max="100" value="0" oninput="aplicarFiltros()" style="width:150px;">
    <span id="scoreLabel" style="font-size:13px;">0</span>
    <select id="ratingFilter" onchange="aplicarFiltros()">
        <option value="all">Todos los ratings</option>
        <option value="strong_buy">Strong Buy</option>
        <option value="buy">Buy</option>
        <option value="hold">Hold</option>
        <option value="sell">Sell</option>
    </select>
    <button onclick="resetearFiltros()">🔄 Resetear</button>
    <span style="font-size:12px;color:#8b949e;margin-left:auto;" id="resultCount">Mostrando {len(datos_acciones)} acciones</span>
</div>

<!-- ===== TABLA ===== -->
<h2>📋 Tabla de Oportunidades</h2>
<p style="color:#8b949e;font-size:13px;margin:-8px 0 12px;">Haz clic en una fila para ver detalles · Haz clic en cabeceras para ordenar</p>
<div style="overflow-x:auto;max-height:600px;overflow-y:auto;">
    <table>
        <thead>
            <tr>
                <th onclick="ordenarTabla(0)">Ticker</th>
                <th onclick="ordenarTabla(1)">Nombre</th>
                <th onclick="ordenarTabla(2)">Precio</th>
                <th onclick="ordenarTabla(3)">Sector</th>
                <th onclick="ordenarTabla(4)">Caída %</th>
                <th onclick="ordenarTabla(5)">Var 24h</th>
                <th onclick="ordenarTabla(6)">P/E</th>
                <th onclick="ordenarTabla(7)">ROE %</th>
                <th onclick="ordenarTabla(8)">Growth %</th>
                <th onclick="ordenarTabla(9)">Score</th>
                <th onclick="ordenarTabla(10)">Rating</th>
            </tr>
        </thead>
        <tbody id="tableBody">
            {tabla_html}
        </tbody>
    </table>
</div>

<!-- ===== TOP 3 ===== -->
<h2>🏆 Top 3 Oportunidades</h2>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:15px;margin:12px 0;">
    {top3_html}
</div>

<!-- ===== ANÁLISIS DE RIESGOS ===== -->
<h2>⚠️ Análisis de Riesgos</h2>
<div class="risk-grid">
    <div class="risk-card visible">
        <h4>🔴 Riesgos Visibles</h4>
        <p>Corrección técnica en el sector tecnológico · Incertidumbre regulatoria en IA · Desaceleración del crecimiento de ingresos en algunas empresas</p>
    </div>
    <div class="risk-card hidden">
        <h4>⚫ Riesgos No Descontados</h4>
        <p>Posible recesión global · Conflictos geopolíticos · Burbuja de IA · Cambio en política monetaria de la Fed</p>
    </div>
    <div class="risk-card scenario">
        <h4>📊 Escenarios Alternativos</h4>
        <p>Escenario bajista: corrección 20-30% adicional · Escenario base: consolidación y recuperación gradual · Escenario alcista: nuevo rally post-verano</p>
    </div>
    <div class="risk-card signal">
        <h4>📡 Señales a Vigilar</h4>
        <p>Resultados Q2 2026 · Evolución del dólar · Flujos de inversión institucional · Volatilidad VIX</p>
    </div>
</div>

<!-- ===== LECTURA CRÍTICA ===== -->
<h2>📖 Lectura Crítica</h2>
<div class="callout-danger">
    <strong>⚠️ ¿Estamos comprando una corrección o el inicio de un mercado bajista?</strong>
</div>
<p style="font-size:15px;">La narrativa dominante sugiere que las caídas en el sector tecnológico son oportunidades de compra. Sin embargo, debemos cuestionar si el mercado está descontando correctamente el riesgo de una desaceleración económica más profunda de lo esperado. Las valoraciones, aunque corregidas, siguen siendo elevadas en términos históricos.</p>
<p style="font-size:15px;">El verdadero riesgo no es la corrección en sí, sino que los fundamentales de las empresas no cumplan con las expectativas de crecimiento implícitas en los precios actuales. La pregunta clave: ¿estamos pagando por crecimiento futuro que podría no materializarse?</p>

<!-- ===== CHECKLIST ===== -->
<h2>✅ Checklist de Rigor</h2>
<ul class="check">
    <li>✅ Datos obtenidos de Yahoo Finance (fuente primaria)</li>
    <li>✅ Scores calculados con metodología consistente (4 pilares: Value, Growth, Quality, Momentum)</li>
    <li>✅ Análisis separa hechos de interpretaciones</li>
    <li>✅ Lenguaje probabilístico, no determinista</li>
</ul>

<!-- ===== FOOTER ===== -->
<footer>
    <p><strong>Aviso.</strong> Este dashboard es información general de mercado, no asesoramiento financiero ni recomendación de inversión personalizada. Las decisiones de inversión son tuyas y conllevan riesgo de pérdida. Para asesoramiento personalizado acude a una entidad autorizada (CNMV en España o equivalente).</p>
    <p>Datos: Yahoo Finance · Generado automáticamente · {fecha_legible} {hora_madrid}</p>
</footer>

</div>

<!-- ===== JAVASCRIPT ===== -->
<script>
// Variables para filtros y ordenación
let sortColumn = -1;
let sortAsc = true;

// Función para expandir/colapsar detalles
function toggleDetail(ticker) {{
    const detailRow = document.getElementById('detail-' + ticker);
    if (detailRow) {{
        if (detailRow.style.display === 'none') {{
            detailRow.style.display = 'table-row';
        }} else {{
            detailRow.style.display = 'none';
        }}
    }}
}}

// Función para ordenar tabla
function ordenarTabla(col) {{
    if (sortColumn === col) {{
        sortAsc = !sortAsc;
    }} else {{
        sortColumn = col;
        sortAsc = true;
    }}
    aplicarFiltros();
}}

// Función principal de filtrado y ordenación
function aplicarFiltros() {{
    const sector = document.getElementById('sectorFilter').value;
    const minScore = parseInt(document.getElementById('scoreFilter').value);
    const rating = document.getElementById('ratingFilter').value;
    document.getElementById('scoreLabel').textContent = minScore;

    const tbody = document.getElementById('tableBody');
    const rows = tbody.querySelectorAll('tr');
    let visibleRows = [];

    rows.forEach(row => {{
        // Saltamos filas de detalle
        if (row.id && row.id.startsWith('detail-')) return;

        const cells = row.querySelectorAll('td');
        if (cells.length < 11) return;

        const rowSector = cells[3].textContent.trim();
        const rowScore = parseInt(cells[9].textContent.trim());
        const rowRating = cells[10].textContent.trim().toLowerCase();

        let visible = true;
        if (sector !== 'all' && rowSector !== sector) visible = false;
        if (rowScore < minScore) visible = false;
        if (rating !== 'all' && !rowRating.includes(rating.replace('_', ' '))) visible = false;

        // Ocultar detalle asociado
        const ticker = cells[0].textContent.trim();
        const detailRow = document.getElementById('detail-' + ticker);
        if (detailRow) {{
            detailRow.style.display = 'none';
        }}

        if (visible) {{
            row.style.display = '';
            visibleRows.push({{
                row: row,
                cells: cells,
                ticker: ticker
            }});
        }} else {{
            row.style.display = 'none';
        }}
    }});

    document.getElementById('resultCount').textContent = 'Mostrando ' + visibleRows.length + ' acciones';

    // Ordenación (sobre filas visibles)
    if (visibleRows.length > 1 && sortColumn >= 0) {{
        visibleRows.sort((a, b) => {{
            let aVal = a.cells[sortColumn].textContent.trim();
            let bVal = b.cells[sortColumn].textContent.trim();

            // Intentar convertir a número
            let aNum = parseFloat(aVal.replace(/,/g, '').replace(/[^0-9.-]/g, ''));
            let bNum = parseFloat(bVal.replace(/,/g, '').replace(/[^0-9.-]/g, ''));

            if (!isNaN(aNum) && !isNaN(bNum)) {{
                return sortAsc ? aNum - bNum : bNum - aNum;
            }}
            return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }});

        // Reordenar en el DOM
        visibleRows.forEach(({{row}}) => tbody.appendChild(row));
    }}
}}

function resetearFiltros() {{
    document.getElementById('sectorFilter').value = 'all';
    document.getElementById('scoreFilter').value = '0';
    document.getElementById('ratingFilter').value = 'all';
    document.getElementById('scoreLabel').textContent = '0';
    aplicarFiltros();
}}

// Inicializar
document.addEventListener('DOMContentLoaded', function() {{
    aplicarFiltros();
}});
</script>

</body>
</html>"""

# ==========================================
# 7. GUARDAR ARCHIVOS
# ==========================================
os.makedirs("dashboard-historico", exist_ok=True)

with open("dashboard-latest.html", "w", encoding="utf-8") as f:
    f.write(html_completo)
print(f"✅ dashboard-latest.html guardado ({len(html_completo):,} caracteres)")

with open(f"dashboard-historico/{fecha_hoy}.html", "w", encoding="utf-8") as f:
    f.write(html_completo)
print(f"✅ dashboard-historico/{fecha_hoy}.html guardado")

print("\n🎉 DASHBOARD COMPLETO GENERADO")
print(f"📊 {len(datos_acciones)} acciones analizadas")
print(f"📈 Score promedio: {round(sum(d['score_total'] for d in datos_acciones)/len(datos_acciones), 1) if datos_acciones else 0}")

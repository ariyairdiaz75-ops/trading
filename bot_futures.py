import requests
import time
import math
from typing import List, Dict, Any

# ====================== SIN PROXY ======================
proxies = None
print("🌐 Conexión directa sin proxy")

# ====================== ENDPOINTS ======================
BASE_URLS = [
    "https://data.binance.com",
    "https://fapi.binance.com",
    "https://testnet.binancefuture.com"
]

# ====================== MEMORIA ======================
history_pct: Dict[str, List[float]] = {}
special_tracking: Dict[str, float] = {}

# ====================== FETCH ======================
def fetch_all_24hr_tickers() -> List[Dict]:
    for base in BASE_URLS:
        url = f"{base}/fapi/v1/ticker/24hr"
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                print(f"✅ Conectado a {base}")
                return response.json()
            elif response.status_code == 451:
                print(f"⚠️ Bloqueo en {base}, probando otro...")
                continue
        except Exception as e:
            print(f"❌ Error en {base}: {e}")
            continue
    return []

# ====================== TELEGRAM ======================
def send_to_telegram(message: str):
    token = "8194978480:AAHV_8fhFk3kr2C_9SxNcGGFRbFH4yluWpI"
    chat_id = "8100573508"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        print("📨 Enviado a Telegram")
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

# ====================== MAIN ======================
def main():
    print("🤖 BOT FUTUROS BINANCE MEJORADO 🔥")
    minute_counter = 0

    while True:
        try:
            tickers = fetch_all_24hr_tickers()
            if not tickers:
                time.sleep(20)
                continue

            active_symbols = set()

            for ticker in tickers:
                symbol = ticker.get("symbol", "")
                if not symbol.endswith("USDT"):
                    continue

                try:
                    pct = float(ticker.get("priceChangePercent", 0))
                except:
                    continue

                # ================= FILTRO 10% - 30% =================
                if 10 <= pct <= 30:
                    active_symbols.add(symbol)

                    if symbol not in history_pct:
                        history_pct[symbol] = []

                    history_pct[symbol].append(pct)

                    if len(history_pct[symbol]) > 5:
                        history_pct[symbol].pop(0)

                # ================= SEGUIMIENTO +30 =================
                if pct > 30:
                    prev = special_tracking.get(symbol, pct)
                    growth = pct - prev

                    if growth >= 2:
                        special_tracking[symbol] = pct
                    else:
                        special_tracking.pop(symbol, None)

            # limpiar monedas que ya no están activas
            for sym in list(history_pct.keys()):
                if sym not in active_symbols:
                    history_pct.pop(sym, None)

            minute_counter += 1
            print(f"⏱ Minuto {minute_counter}")

            # ================= CADA 5 MIN =================
            if minute_counter >= 5:

                candidates = []

                for symbol, hist in history_pct.items():
                    if len(hist) < 5:
                        continue

                    start = hist[0]
                    now = hist[-1]
                    growth = now - start

                    candidates.append({
                        "symbol": symbol,
                        "start": start,
                        "now": now,
                        "growth": growth
                    })

                candidates.sort(key=lambda x: x["growth"], reverse=True)
                top3 = candidates[:3]

                # ================= MENSAJE =================
                msg = "🚀🔥 TOP MOVIMIENTOS (Últimos 5 min) 🔥🚀\n\n"
                medals = ["🥇", "🥈", "🥉"]

                for i, c in enumerate(top3):
                    estado = (
                        "Rompiendo fuerte 🚀" if c["growth"] > 15 else
                        "Momentum sólido 📈" if c["growth"] > 8 else
                        "Subida constante 🔥"
                    )

                    msg += (
                        f"{medals[i]} {c['symbol']}\n"
                        f"Inicio: +{c['start']:.1f}% → Ahora: +{c['now']:.1f}%\n"
                        f"Impulso real: +{c['growth']:.1f}%\n"
                        f"Estado: {estado}\n\n"
                    )

                # ================= +30% =================
                if special_tracking:
                    msg += "\n📊 SEGUIMIENTO ESPECIAL (+30% ACTIVOS)\n\n"

                    for sym, pct in special_tracking.items():
                        hist = history_pct.get(sym, [])

                        if len(hist) >= 2:
                            prev = hist[-2]
                            growth = pct - prev

                            if growth >= 2:
                                msg += (
                                    f"🚨 {sym}\n"
                                    f"Hace 1 min: +{prev:.1f}% → Ahora: +{pct:.1f}%\n"
                                    f"Impulso reciente: +{growth:.1f}%\n"
                                    f"Estado: EXPLOSIÓN 🚀🔥\n\n"
                                )

                msg += "⏱ Cada 1 min | Ventana 5 min\n💰 Binance Futures"

                send_to_telegram(msg)

                minute_counter = 0

            time.sleep(60)

        except Exception as e:
            print(f"❌ Error general: {e}")
            time.sleep(20)

# ====================== RUN ======================
if __name__ == "__main__":
    main()

import requests
import time
from typing import List, Dict

# ====================== CONFIG ======================
TOKEN = "TU_TOKEN_AQUI"
CHAT_ID = "TU_CHAT_ID_AQUI"

BASE_URL = "https://fapi.binance.com"

# ====================== MEMORIA ======================
price_history: Dict[str, List[float]] = {}
special_tracking: Dict[str, float] = {}
streak_counter: Dict[str, int] = {}

# ====================== FETCH ======================
def fetch_tickers() -> List[Dict]:
    url = f"{BASE_URL}/fapi/v1/ticker/24hr"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)

        if r.status_code != 200:
            print(f"⚠️ Status code: {r.status_code}")
            return []

        data = r.json()

        # 🔥 VALIDACIÓN CLAVE (ARREGLA TU ERROR)
        if not isinstance(data, list):
            print(f"⚠️ Respuesta inválida: {data}")
            return []

        print("✅ Conectado a Binance Futures")
        return data

    except Exception as e:
        print(f"❌ Error fetch: {e}")
        return []

# ====================== TELEGRAM ======================
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        print("📨 Enviado a Telegram")
    except Exception as e:
        print(f"❌ Error Telegram: {e}")

# ====================== MAIN ======================
def main():
    print("🔥 BOT PRO ACTIVADO 🔥")
    minute_counter = 0

    while True:
        try:
            tickers = fetch_tickers()
            if not tickers:
                time.sleep(20)
                continue

            active_symbols = set()

            # ================= LOOP PRINCIPAL =================
            for t in tickers:

                # 🔥 PROTECCIÓN EXTRA (ARREGLA ERROR)
                if not isinstance(t, dict):
                    continue

                symbol = t.get("symbol", "")

                if not symbol.endswith("USDT"):
                    continue

                try:
                    price = float(t.get("lastPrice", 0))
                    pct24 = float(t.get("priceChangePercent", 0))
                except:
                    continue

                # ================= FILTRO 10% - 30% =================
                if 10 <= pct24 <= 30:
                    active_symbols.add(symbol)

                    if symbol not in price_history:
                        price_history[symbol] = []

                    price_history[symbol].append(price)

                    if len(price_history[symbol]) > 5:
                        price_history[symbol].pop(0)

                # ================= SEGUIMIENTO +30 =================
                if pct24 > 30:
                    prev = special_tracking.get(symbol, pct24)
                    growth = pct24 - prev

                    if growth >= 2:
                        special_tracking[symbol] = pct24
                    else:
                        special_tracking.pop(symbol, None)

            # ================= LIMPIEZA =================
            for sym in list(price_history.keys()):
                if sym not in active_symbols:
                    price_history.pop(sym, None)

            minute_counter += 1
            print(f"⏱ Minuto {minute_counter}")

            # ================= CADA 5 MIN =================
            if minute_counter >= 5:

                candidates = []

                for symbol, prices in price_history.items():
                    if len(prices) < 5:
                        continue

                    start_price = prices[0]
                    end_price = prices[-1]

                    growth = ((end_price - start_price) / start_price) * 100

                    candidates.append({
                        "symbol": symbol,
                        "start": start_price,
                        "end": end_price,
                        "growth": growth
                    })

                # ordenar por crecimiento real
                candidates.sort(key=lambda x: x["growth"], reverse=True)
                top3 = candidates[:3]

                # =================🔥 STREAK SYSTEM =================
                current_symbols = {c["symbol"] for c in top3}

                for sym in list(streak_counter.keys()):
                    if sym in current_symbols:
                        streak_counter[sym] += 1
                    else:
                        streak_counter[sym] -= 1
                        if streak_counter[sym] <= 0:
                            streak_counter.pop(sym)

                for sym in current_symbols:
                    if sym not in streak_counter:
                        streak_counter[sym] = 1

                # ================= MENSAJE =================
                msg = "🚀🔥 TOP MOVIMIENTOS (Últimos 5 min) 🔥🚀\n\n"
                medals = ["🥇", "🥈", "🥉"]

                for i, c in enumerate(top3):

                    fires = "🔥" * streak_counter.get(c["symbol"], 0)

                    estado = (
                        "EXPLOSIÓN 🚀🔥" if c["growth"] > 5 else
                        "Momentum fuerte 📈" if c["growth"] > 3 else
                        "Subida constante 🔥"
                    )

                    msg += (
                        f"{medals[i]} {c['symbol']} {fires}\n"
                        f"Inicio: {c['start']:.6f} → Ahora: {c['end']:.6f}\n"
                        f"Cambio real: +{c['growth']:.2f}%\n"
                        f"Estado: {estado}\n\n"
                    )

                # ================= SEGUIMIENTO +30 =================
                if special_tracking:
                    msg += "\n📊 SEGUIMIENTO ESPECIAL (+30%)\n\n"

                    for sym in list(special_tracking.keys()):
                        hist = price_history.get(sym, [])

                        if len(hist) >= 2:
                            prev_price = hist[-2]
                            current_price = hist[-1]

                            growth = ((current_price - prev_price) / prev_price) * 100

                            if growth >= 1:
                                msg += (
                                    f"🚨 {sym}\n"
                                    f"Hace 1 min: {prev_price:.6f} → Ahora: {current_price:.6f}\n"
                                    f"Impulso: +{growth:.2f}%\n"
                                    f"Estado: CONTINÚA 🚀\n\n"
                                )
                            else:
                                special_tracking.pop(sym, None)

                msg += "⏱ Cada 1 min | Ventana 5 min\n💰 Binance Futures"

                send_telegram(msg)

                minute_counter = 0

            time.sleep(60)

        except Exception as e:
            print(f"❌ Error general: {e}")
            time.sleep(20)

# ====================== RUN ======================
if __name__ == "__main__":
    main()

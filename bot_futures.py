import requests
import time
import math
from typing import List, Dict, Any

# ====================== SIN PROXY ======================
proxies = None
print("🌐 Conexión directa sin proxy")

# ====================== CONFIG ======================
TOKEN = "8194978480:AAHV_8fhFk3kr2C_9SxNcGGFRbFH4yluWpI"
CHAT_ID = "8100573508"

# ====================== ENDPOINTS ======================
BASE_URLS = [
    "https://data.binance.com",
    "https://fapi.binance.com",
    "https://testnet.binancefuture.com"
]

# ====================== MEMORIA ======================
history_pct: Dict[str, List[float]] = {}
appearance_data: Dict[str, Dict[str, int]] = {}
special_tracking: Dict[str, float] = {}

last_top_symbols: List[str] = []
last_update_id = 0
minute_counter = 0

# ====================== FETCH ======================
def fetch_all_24hr_tickers() -> List[Dict]:
    for base in BASE_URLS:
        try:
            r = requests.get(f"{base}/fapi/v1/ticker/24hr", timeout=20)
            if r.status_code == 200:
                return r.json()
        except:
            continue
    return []

def fetch_klines(symbol: str, interval: str = "1m", limit: int = 10):
    for base in BASE_URLS:
        try:
            r = requests.get(f"{base}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}", timeout=20)
            if r.status_code == 200:
                return r.json()
        except:
            continue
    return []

# ====================== TELEGRAM ======================
def send(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except:
        pass

# ====================== RESET ======================
def check_commands():
    global last_update_id
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"offset": last_update_id + 1},
            timeout=10
        )
        data = r.json()

        for u in data.get("result", []):
            last_update_id = u["update_id"]

            msg = u.get("message", {})
            text = msg.get("text", "")
            chat_id = str(msg.get("chat", {}).get("id"))

            if chat_id != CHAT_ID:
                continue

            if text == "/reset":
                history_pct.clear()
                appearance_data.clear()
                special_tracking.clear()
                send("🔄 Rachas reiniciadas correctamente")

    except:
        pass

# ====================== EMOJIS ======================
def get_emoji(symbol):
    data = appearance_data.setdefault(symbol, {
        "rockets": 0,
        "fires": 0,
        "seen": False
    })

    # consecutivo → 🔥
    if symbol in last_top_symbols:
        data["fires"] += 1
        return "🔥" * data["fires"]

    # apareció antes → 🚀
    if data["seen"]:
        data["rockets"] += 1
        data["fires"] = 0
        return "🚀" * data["rockets"]

    # primera vez
    data["seen"] = True
    return "🆕"

# ====================== SCORE ======================
def calculate_score_and_metrics(ticker: Dict, klines: List):
    if len(klines) < 5:
        return None

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    consecutive_ups = 0
    for i in range(len(closes)-1, 0, -1):
        if closes[i] > closes[i-1]:
            consecutive_ups += 1
        else:
            break

    if consecutive_ups < 3:
        return None

    vol_growth = 0
    for i in range(len(volumes)-1, 0, -1):
        if volumes[i] > volumes[i-1] * 1.05:
            vol_growth += 1
        else:
            break

    momentum = (closes[-1] / closes[-5] - 1) * 100
    pct = float(ticker["priceChangePercent"])

    score = pct*4 + momentum*3 + consecutive_ups*20 + vol_growth*10

    return {
        "symbol": ticker["symbol"],
        "pct": pct,
        "score": score
    }

# ====================== MAIN ======================
def main():
    global last_top_symbols, minute_counter

    print("🤖 BOT FUTUROS PRO 🔥")

    while True:
        try:
            check_commands()

            tickers = fetch_all_24hr_tickers()
            candidates = []
            active_symbols = set()

            for t in tickers:
                symbol = t.get("symbol", "")
                if not symbol.endswith("USDT"):
                    continue

                try:
                    pct = float(t.get("priceChangePercent", 0))
                except:
                    continue

                # ===== FILTRO 10-30 =====
                if 10 <= pct <= 30:
                    active_symbols.add(symbol)

                    history_pct.setdefault(symbol, []).append(pct)
                    if len(history_pct[symbol]) > 5:
                        history_pct[symbol].pop(0)

                # ===== +30 =====
                if pct > 30:
                    prev = special_tracking.get(symbol, pct)
                    if pct - prev >= 2:
                        special_tracking[symbol] = pct
                    else:
                        special_tracking.pop(symbol, None)

                # ===== SCORE =====
                klines = fetch_klines(symbol)
                m = calculate_score_and_metrics(t, klines)
                if m:
                    candidates.append(m)

            minute_counter += 1

            # ===== CADA 5 MIN =====
            if minute_counter >= 5:

                results = []

                for symbol, hist in history_pct.items():
                    if len(hist) < 5:
                        continue

                    start = hist[0]
                    now = hist[-1]
                    growth = now - start

                    results.append({
                        "symbol": symbol,
                        "start": start,
                        "now": now,
                        "growth": growth
                    })

                results.sort(key=lambda x: x["growth"], reverse=True)
                top = results[:3]

                msg = "🚀🔥 TOP MOVIMIENTOS (Últimos 5 min) 🔥🚀\n\n"

                for i, c in enumerate(top):
                    emoji = get_emoji(c["symbol"])

                    estado = (
                        "Rompiendo fuerte 🚀" if c["growth"] > 15 else
                        "Momentum sólido 📈" if c["growth"] > 8 else
                        "Subida constante 🔥"
                    )

                    msg += (
                        f"{['🥇','🥈','🥉'][i]} {c['symbol']} {emoji}\n"
                        f"Inicio: +{c['start']:.1f}% → Ahora: +{c['now']:.1f}%\n"
                        f"Impulso real: +{c['growth']:.1f}%\n"
                        f"Estado: {estado}\n\n"
                    )

                # ===== +30 =====
                if special_tracking:
                    msg += "\n📊 SEGUIMIENTO ESPECIAL (+30% ACTIVOS)\n\n"

                    for sym, pct in special_tracking.items():
                        hist = history_pct.get(sym, [])
                        if len(hist) >= 2:
                            prev = hist[-2]
                            growth = pct - prev

                            if growth >= 2:
                                emoji = get_emoji(sym)

                                msg += (
                                    f"🚨 {sym} {emoji}\n"
                                    f"Hace 1 min: +{prev:.1f}% → Ahora: +{pct:.1f}%\n"
                                    f"Impulso reciente: +{growth:.1f}%\n"
                                    f"Estado: EXPLOSIÓN 🚀🔥\n\n"
                                )

                msg += "⏱ Cada 1 min | Ventana 5 min\n💰 Binance Futures"

                send(msg)

                last_top_symbols = [c["symbol"] for c in top]
                minute_counter = 0

            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(20)

if __name__ == "__main__":
    main()

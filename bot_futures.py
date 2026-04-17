import requests
import time
import os
import math
from typing import List, Dict, Any

# ====================== PROXY CONFIGURADO ======================
# Proxy tomado de tu lista (Indonesia - Jakarta)
PROXY_URL = os.getenv("PROXY_URL", "socks5://103.76.149.140:1080")

if PROXY_URL:
    proxies = {"http": PROXY_URL, "https": PROXY_URL}
    print(f"🔀 Usando proxy: {PROXY_URL}")
else:
    proxies = None
    print("⚠️ Sin proxy")

# Endpoints de Binance Futures
BASE_URLS = [
    "https://fapi.binance.com",
    "https://testnet.binancefuture.com",
    "https://data.binance.com"
]

def fetch_all_24hr_tickers() -> List[Dict]:
    for base in BASE_URLS:
        url = f"{base}/fapi/v1/ticker/24hr"
        try:
            response = requests.get(url, timeout=15, proxies=proxies)
            if response.status_code == 200:
                print(f"✅ ¡Conexión exitosa con {base}!")
                return response.json()
            elif response.status_code == 451:
                print(f"⚠️ Bloqueo 451 en {base} → probando siguiente...")
                continue
            else:
                print(f"❌ Código HTTP {response.status_code} en {base}")
        except Exception as e:
            print(f"❌ Error en {base}: {e}")
            continue
    print("❌ Todos los endpoints fallaron. Prueba otro proxy.")
    return []


def fetch_klines(symbol: str, interval: str = "1m", limit: int = 10) -> List[List]:
    for base in BASE_URLS:
        url = f"{base}/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            response = requests.get(url, timeout=10, proxies=proxies)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    return []


def calculate_score_and_metrics(ticker: Dict, klines: List) -> Dict[str, Any] | None:
    if len(klines) < 5:
        return None

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    # Subidas consecutivas (mínimo 3)
    consecutive_ups = 0
    for i in range(len(closes)-1, 0, -1):
        if closes[i] > closes[i-1]:
            consecutive_ups += 1
        else:
            break
    if consecutive_ups < 3:
        return None

    # Volumen creciente
    consecutive_vol_growth = 0
    for i in range(len(volumes)-1, 0, -1):
        if volumes[i] > volumes[i-1] * 1.05:
            consecutive_vol_growth += 1
        else:
            break

    mom_period = min(5, len(closes)-1)
    momentum = (closes[-1] / closes[-1-mom_period] - 1) * 100 if mom_period > 0 else 0.0

    quote_volume = float(ticker.get("quoteVolume", 0))
    vol_score = math.log10(quote_volume + 1) * 8 if quote_volume > 0 else 0.0

    pct_change = float(ticker["priceChangePercent"])
    score = (pct_change * 4.0 + momentum * 3.5 + consecutive_ups * 25.0 + vol_score * 1.5 + consecutive_vol_growth * 12.0)

    return {
        "symbol": ticker["symbol"],
        "pct": pct_change,
        "score": score,
        "consecutive": consecutive_ups,
        "momentum": round(momentum, 2),
        "vol_growth": consecutive_vol_growth,
    }


def format_alert_message(top3: List[Dict]) -> str:
    if not top3:
        return ""
    msg = "🚀🔥 TOP FUTUROS EN LLAMAS 🔥🚀\n\n"
    emojis = ["🥇", "🥈", "🥉"]
    for idx, item in enumerate(top3):
        desc = "Subiendo como cohete 🚀" if item["consecutive"] >= 5 else "Momentum brutal 🔥" if item["momentum"] > 8 else "Subiendo constante 📈"
        if item["vol_growth"] >= 3:
            desc += " | Volumen explotando 💥"
        msg += f"{emojis[idx]} {item['symbol']} +{item['pct']:.1f}% | {desc}\n"
    msg += "\n📊 Binance Futures USDT • Revisado cada 60s"
    return msg


def send_to_telegram(message: str) -> bool:
    token = "8194978480:AAHV_8fhFk3kr2C_9SxNcGGFRbFH4yluWpI"
    chat_id = "8100573508"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
        print("📨 Alerta enviada a Telegram ✅")
        return True
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False


def main():
    print("🤖 BOT FUTUROS BINANCE INICIADO EN RAILWAY + PROXY (Indonesia) 🔥")
    last_top_symbols: List[str] = []

    while True:
        try:
            tickers = fetch_all_24hr_tickers()
            if not tickers:
                print("⚠️ No se obtuvieron datos. Reintentando en 20s...")
                time.sleep(20)
                continue

            candidates = []
            for ticker in tickers:
                symbol = ticker.get("symbol", "")
                if not symbol.endswith("USDT"):
                    continue
                try:
                    pct = float(ticker.get("priceChangePercent", 0))
                    if pct <= 10.0:
                        continue
                except:
                    continue

                klines = fetch_klines(symbol)
                metrics = calculate_score_and_metrics(ticker, klines)
                if metrics:
                    candidates.append(metrics)

            if candidates:
                candidates.sort(key=lambda x: x["score"], reverse=True)
                top3 = candidates[:3]
                current_symbols = [item["symbol"] for item in top3]

                if current_symbols != last_top_symbols:
                    message = format_alert_message(top3)
                    if message:
                        send_to_telegram(message)
                        last_top_symbols = current_symbols[:]
                else:
                    print(f"🔄 {time.strftime('%H:%M:%S')} → Sin cambios en TOP 3")
            else:
                print(f"⚠️ {time.strftime('%H:%M:%S')} → No hay criptos que cumplan +10% + momentum fuerte")

            time.sleep(60)

        except Exception as e:
            print(f"❌ Error general (bot sigue vivo): {e}")
            time.sleep(20)


if __name__ == "__main__":
    main()

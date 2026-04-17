import requests
import time
import os
import math
from typing import List, Dict, Any

def fetch_all_24hr_tickers() -> List[Dict]:
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error al obtener tickers 24h: {e}")
        return []


def fetch_klines(symbol: str, interval: str = "1m", limit: int = 10) -> List[List]:
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error klines para {symbol}: {e}")
        return []


def calculate_score_and_metrics(ticker: Dict, klines: List) -> Dict[str, Any] | None:
    if len(klines) < 5:
        return None

    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    # Subidas consecutivas de precio
    consecutive_ups = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            consecutive_ups += 1
        else:
            break

    if consecutive_ups < 3:
        return None

    # Volumen creciente (anti-fake pump)
    consecutive_vol_growth = 0
    for i in range(len(volumes) - 1, 0, -1):
        if volumes[i] > volumes[i - 1] * 1.05:
            consecutive_vol_growth += 1
        else:
            break

    mom_period = min(5, len(closes) - 1)
    momentum = (closes[-1] / closes[-1 - mom_period] - 1) * 100 if mom_period > 0 else 0.0

    quote_volume = float(ticker.get("quoteVolume", 0))
    vol_score = math.log10(quote_volume + 1) * 8 if quote_volume > 0 else 0.0

    pct_change = float(ticker["priceChangePercent"])
    score = (
        pct_change * 4.0 +
        momentum * 3.5 +
        consecutive_ups * 25.0 +
        vol_score * 1.5 +
        consecutive_vol_growth * 12.0
    )

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
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ ERROR: Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

    try:
        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        print("📨 Alerta enviada a Telegram ✅")
        return True
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False


def main():
    print("🤖 BOT FUTUROS BINANCE INICIADO EN RAILWAY 🔥")
    last_top_symbols: List[str] = []

    while True:
        try:
            tickers = fetch_all_24hr_tickers()
            if not tickers:
                time.sleep(10)
                continue

            candidates = []
            for ticker in tickers:
                symbol = ticker["symbol"]
                if not symbol.endswith("USDT"):
                    continue
                if float(ticker.get("priceChangePercent", 0)) <= 10.0:
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
                print(f"⚠️ {time.strftime('%H:%M:%S')} → No hay criptos que cumplan los filtros")

            time.sleep(60)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error (bot sigue vivo): {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
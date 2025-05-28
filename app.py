
import os
import time
import ccxt
import requests
import schedule
import threading
from flask import Flask
from dotenv import load_dotenv

# === 環境變數設定 ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIN_PROFIT_RATE = float(os.getenv("MIN_PROFIT_RATE", "0.0104"))
FEE_RATE = 0.001
SLIPPAGE = 0.002

# === 模擬資金 ===
sim_balance = {
    "usdt": 4700,
    "position": 0,
    "entry_price": 0
}

# === 初始化交易所 ===
kucoin = ccxt.kucoin()
kucoin.load_markets()

symbol1 = "ARB/USDT"
symbol2 = "ARB/ETH"
symbol3 = "ETH/USDT"

# === Telegram 發送 ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("TG 發送錯誤：", e)

# === 主套利邏輯 ===
def monitor_triangular_arbitrage():
    while True:
        try:
            arb_usdt = kucoin.fetch_ticker(symbol1)
            arb_eth = kucoin.fetch_ticker(symbol2)
            eth_usdt = kucoin.fetch_ticker(symbol3)

            usdt_start = 100
            arb_amt = usdt_start / (arb_usdt['ask'] * (1 + FEE_RATE + SLIPPAGE))
            eth_amt = arb_amt * (arb_eth['bid'] * (1 - FEE_RATE - SLIPPAGE))
            usdt_back = eth_amt * (eth_usdt['bid'] * (1 - FEE_RATE - SLIPPAGE))

            profit_usdt = usdt_back - usdt_start
            profit_ratio = profit_usdt / usdt_start

            print(f"[監控] 利潤率: {profit_ratio:.4f}")

            if profit_ratio > MIN_PROFIT_RATE:
                send_telegram(
                    f"[KuCoin 三角套利機會]\n利潤率：{profit_ratio*100:.2f}%\n模擬獲利：{profit_usdt:.2f} USDT"
                )

                size = sim_balance["usdt"] / (arb_usdt["ask"] * (1 + FEE_RATE))
                sim_balance["position"] += size
                sim_balance["usdt"] -= size * arb_usdt["ask"]
                sim_balance["entry_price"] = arb_usdt["ask"]

                send_telegram(f"[模擬下單] 買入 ARB {size:.4f} @ {arb_usdt['ask']:.4f}")
        except Exception as e:
            print("套利錯誤：", e)
        time.sleep(1)

# === 每日報告 ===
def send_daily_report():
    last_price = kucoin.fetch_ticker(symbol1)['last']
    value = sim_balance["position"] * last_price + sim_balance["usdt"]
    msg = (
        f"[每日績效]\n現金 USDT：{sim_balance['usdt']:.2f}\nARB 持倉：{sim_balance['position']:.4f}\n資產估值：{value:.2f} USDT"
    )
    send_telegram(msg)

def schedule_report():
    schedule.every().day.at("09:00").do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

app = Flask(__name__)
@app.route('/')
def index():
    return "KuCoin Arbitrage Simulator is running."

if __name__ == "__main__":
    threading.Thread(target=monitor_triangular_arbitrage, daemon=True).start()
    threading.Thread(target=schedule_report, daemon=True).start()
    send_telegram("[啟動通知] KuCoin 三角套利模擬器已上線")
    app.run(host="0.0.0.0", port=10000)

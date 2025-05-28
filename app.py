
import os
import time
import ccxt
import requests
import schedule
import threading
from flask import Flask
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MIN_PROFIT_RATE = float(os.getenv("MIN_PROFIT_RATE", "0.0104"))  # 1.04%
FEE_RATE = 0.001  # 0.1%
SLIPPAGE = 0.002  # 0.2%
BASE_CURRENCY = "USDT"

# === Initialize exchange ===
kucoin = ccxt.kucoin()
kucoin.load_markets()

# === Simulated balance ===
sim_balance = {
    "usdt": 4700,
    "position": 0,
    "entry_price": 0
}

# === Telegram notification ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Telegram 發送失敗：", e)

# === Triangle arbitrage logic ===
def monitor_tri_arbitrage():
    while True:
        try:
            # Triangle: USDT -> BTC -> ETH -> USDT
            a_to_b = kucoin.fetch_ticker("BTC/USDT")["ask"] * (1 + FEE_RATE + SLIPPAGE)
            b_to_c = kucoin.fetch_ticker("ETH/BTC")["ask"] * (1 + FEE_RATE + SLIPPAGE)
            c_to_a = kucoin.fetch_ticker("ETH/USDT")["bid"] * (1 - FEE_RATE - SLIPPAGE)

            usdt_start = 1
            btc_amount = usdt_start / a_to_b
            eth_amount = btc_amount / b_to_c
            usdt_final = eth_amount * c_to_a
            profit_ratio = (usdt_final - usdt_start) / usdt_start
            profit_usdt = (usdt_final - usdt_start) * sim_balance["usdt"]

            print(f"[三角套利監控] 利潤率: {profit_ratio:.4f}")

            if profit_ratio > MIN_PROFIT_RATE:
                send_telegram(
                    f"🚨 KuCoin 三角套利機會\n"
                    f"利潤率：{profit_ratio * 100:.2f}%\n"
                    f"模擬獲利：約 {profit_usdt:.2f} USDT"
                )
        except Exception as e:
            print("套利錯誤：", e)
        time.sleep(1)

# === 每日績效報告 ===
def send_daily_report():
    msg = (
        f"📊 每日模擬績效報告\n"
        f"💵 現金 USDT：{sim_balance['usdt']:.2f}\n"
        f"📦 模擬資產總值：{sim_balance['usdt']:.2f} USDT"
    )
    send_telegram(msg)

def schedule_daily_report():
    schedule.every().day.at("09:00").do(send_daily_report)
    while True:
        schedule.run_pending()
        time.sleep(30)

# === Startup notification ===
send_telegram("🚀 KuCoin 三角套利模擬系統已啟動")

# === Flask web service ===
app = Flask(__name__)

@app.route('/')
def index():
    return "🟢 KuCoin Triangle Arbitrage Simulator Running"

if __name__ == "__main__":
    threading.Thread(target=monitor_tri_arbitrage, daemon=True).start()
    threading.Thread(target=schedule_daily_report, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
